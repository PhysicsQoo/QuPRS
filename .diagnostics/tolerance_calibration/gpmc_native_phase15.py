#!/usr/bin/env python3
"""Research-only exact-CNF/native-GPMC semantic checks. Not a solver proof."""
from __future__ import annotations

import argparse
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
from random import Random
import re
import subprocess
import sys
import time

from exact_gpmc_cnf_oracle import count_printed_cnf_exact

OUTPUT_MARKER = "c s exact double prec-sci "
CACHE_HITS = re.compile(r"^c o Cache hit\s*=\s*(\d+)\s*$", re.M)


def fixture(name, n, clauses, positive=None, negative=None):
    positive = dict(positive or {})
    negative = dict(negative or {})
    return {"name": name, "n": n, "clauses": clauses,
            "positive": positive, "negative": negative}


def fixed_cases():
    return [
        fixture("contradictory-units", 1, [(1,), (-1,)]),
        fixture("sat-real-cancellation", 1, [], {1: (-1, 0)}),
        fixture("sat-imag-cancellation", 1, [], {1: (0, -1)}, {1: (0, 1)}),
        fixture("sat-zero-literals", 1, [], {1: (0, 0)}, {1: (0, 0)}),
        fixture("forced-zero-weight", 1, [(1,)], {1: (0, 0)}),
        fixture("equivalent-equal-weight", 2, [(-1, 2), (1, -2)],
                {1: (2, 0), 2: (3, 0)}, {1: (2, 0), 2: (5, 0)}),
        fixture("antivalent-equal-weight", 2, [(-1, -2), (1, 2)],
                {1: (2, 0), 2: (3, 0)}, {1: (2, 0), 2: (5, 0)}),
        fixture("equivalent-unequal-weight", 2, [(-1, 2), (1, -2)],
                {1: (2, 0), 2: (3, 0)}, {1: (7, 0), 2: (5, 0)}),
        fixture("xor-defined", 3, [(1, 2, -3), (-1, -2, -3),
                                    (-1, 2, 3), (1, -2, 3)],
                {1: (0, 1), 2: (1, 0), 3: (0, 1)},
                {1: (1, 0), 2: (1, 0), 3: (0, 1)}),
        fixture("disconnected-components", 4,
                [(1, 2), (-1, 2), (3, 4), (-3, 4)],
                {2: (1, 0)}, {2: (-1, 0)}),
        fixture("both-branches-unsat", 3,
                [(1, 2), (1, -2), (-1, 3), (-1, -3)]),
        fixture("cancellation-component", 4, [(-1, 2), (1, -2), (3, 4), (-3, 4)],
                {2: (-1, 0)}, {2: (1, 0)}),
    ]


def random_cases(count: int):
    rng = Random(20261030)
    w = [(-2, 0), (-1, 0), (0, 0), (0, 1), (0, -1),
         (1, 0), (1, 1), (2, 0)]
    result = []
    for i in range(count):
        n = rng.randint(2, 6)
        clauses = []
        for _ in range(rng.randint(1, 12)):
            variables = rng.sample(range(1, n + 1), rng.randint(1, min(3, n)))
            clauses.append(tuple(v if rng.getrandbits(1) else -v for v in variables))
        positive = {v: rng.choice(w) for v in range(1, n + 1)}
        negative = {v: rng.choice(w) for v in range(1, n + 1)}
        result.append(fixture(f"random-{i:04d}", n, clauses, positive, negative))
    return result


def encode(case):
    out = [f'p cnf {case["n"]} {len(case["clauses"])}', 'c t wmc']
    for v in range(1, case["n"] + 1):
        for lit, table in ((v, case["positive"]), (-v, case["negative"])):
            real, imag = table.get(v, (1, 0))
            out.append(f'c p weight {lit} {real} {imag} 0')
    for clause in case["clauses"]:
        out.append(" ".join(map(str, clause)) + " 0")
    return "\n".join(out) + "\n"


def read_solver(stdout):
    sat_lines = re.findall(r'^s (SATISFIABLE|UNSATISFIABLE)\s*$', stdout, re.M)
    result_lines = [s[len(OUTPUT_MARKER):].strip().replace(" ", "")
                    for s in stdout.splitlines() if s.startswith(OUTPUT_MARKER)]
    if len(sat_lines) != 1 or len(result_lines) != 1:
        raise ValueError("missing or duplicate native SAT/count result")
    s = result_lines[0]
    if s == "0":
        value = (Fraction(0), Fraction(0))
    else:
        if not s.endswith("i"):
            raise ValueError("missing imaginary suffix: " + s[:120])
        body = s[:-1]
        cuts = [i for i in range(1, len(body))
                if body[i] in "+-" and body[i - 1] not in "eE"]
        if len(cuts) != 1:
            raise ValueError("ambiguous complex count: " + s[:120])
        idx = cuts[0]
        value = (Fraction(Decimal(body[:idx])),
                 Fraction(Decimal(body[idx:])))
    hits = CACHE_HITS.findall(stdout)
    return value, sat_lines[0] == "SATISFIABLE", int(hits[-1]) if hits else None


def run(binary, cases, outdir: Path, timeout: int):
    outdir.mkdir(parents=True, exist_ok=True)
    results = []
    for case in cases:
        cnf = encode(case)
        oracle = count_printed_cnf_exact(cnf)
        assert oracle["status"] == "observed"
        ref = (oracle["real"], oracle["imag"])
        sat = oracle["satisfying_assignments"] > 0
        fn = outdir / (case["name"] + ".cnf")
        fn.write_text(cnf)
        for mode, switches in [("default", ["-cs=16"]),
                               ("mainloop-off", ["-cs=16", "-varlim=0"])]:
            args = [str(binary), "-mode=1", "-prec=90", *switches, str(fn)]
            t0 = time.monotonic()
            row = {"case": case["name"], "mode": mode,
                   "cnf_sha256": sha256(cnf.encode()).hexdigest(),
                   "cmd": args, "reference_sat": sat,
                   "reference_count": list(map(str, ref))}
            try:
                p = subprocess.run(args, capture_output=True, text=True,
                                   timeout=timeout)
                row["seconds"] = round(time.monotonic() - t0, 6)
                row["returncode"] = p.returncode
                (outdir / (case["name"] + "-" + mode + ".stdout")).write_text(p.stdout)
                (outdir / (case["name"] + "-" + mode + ".stderr")).write_text(p.stderr)
                if p.returncode:
                    row["status"] = "FAIL_EXIT"
                else:
                    got, has_model, hits = read_solver(p.stdout)
                    row["actual_count"] = list(map(str, got))
                    row["actual_sat"] = has_model
                    row["cache_hits"] = hits
                    row["count_pass"] = (got == ref)
                    row["sat_pass"] = (has_model == sat)
                    row["status"] = ("PASS" if row["count_pass"] and row["sat_pass"]
                                     else "FAIL_SEMANTICS")
            except subprocess.TimeoutExpired as e:
                row["status"] = "TIMEOUT"
                row["seconds"] = round(time.monotonic() - t0, 6)
                (outdir / (case["name"] + "-" + mode + ".timeout")).write_text(str(e))
            except (ValueError, ArithmeticError) as e:
                row["status"] = "FAIL_PARSE"
                row["error"] = repr(e)
            results.append(row)
            if row["status"] != "PASS":
                (outdir / "result.json").write_text(json.dumps(
                    {"status": "FAIL", "solver_sha256": sha256(binary.read_bytes()).hexdigest(),
                     "results": results}, indent=2) + "\n")
                print("NATIVE_GPMC_TARGETED_RED " + json.dumps(row), flush=True)
                return 1
    overall = {"status": "PASS", "solver_sha256": sha256(binary.read_bytes()).hexdigest(),
               "n_cases": len(cases), "n_runs": len(results),
               "actual_cache_hits": sum(r["cache_hits"] or 0 for r in results),
               "cache_hit_metrics_available": all(r["cache_hits"] is not None for r in results),
               "results": results,
               "caveat": "Native black-box counts and SAT only; does not certify cache-key uniqueness or full MPFR error"}
    (outdir / "result.json").write_text(json.dumps(overall, indent=2) + "\n")
    print("NATIVE_GPMC_TARGETED_" + overall["status"] + " "
          + json.dumps({k: v for k, v in overall.items() if k != "results"}), flush=True)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--random", type=int, default=120)
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args()
    if not args.binary.is_file():
        raise SystemExit("NATIVE_BINARY_MISSING")
    return run(args.binary.resolve(), fixed_cases() + random_cases(args.random),
               args.outdir, args.timeout)


if __name__ == "__main__":
    sys.exit(main())

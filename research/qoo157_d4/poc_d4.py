"""Read-only d4 complex WMC experiment; no QuPRS solver registration.

Oracle arithmetic uses exact fractions for decimal source weights. Native d4
output is a numerical observation, never a certified arithmetic bound.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
from fractions import Fraction
from decimal import Decimal, InvalidOperation
from itertools import product

UPSTREAM_REPO = "https://github.com/jm62300/d4"
UPSTREAM_SHA = "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690"
MAX_ORACLE_VARIABLES = 16
D4_RESULT = re.compile(
    r"^c s exact arb (float|int)\s+(.+?)\s*$", re.MULTILINE
)
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
COMPLEX = re.compile(rf"^({NUMBER})((?:\+|-)(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)i$")


def decimal_fraction(token: str) -> Fraction:
    if len(token) > 256:
        raise ValueError("oversized numeric literal")
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError(f"invalid decimal: {token!r}") from exc
    if not value.is_finite() or abs(value.adjusted()) > 1000:
        raise ValueError(f"nonfinite/out-of-range weight: {token!r}")
    return Fraction(value)


def parse_cnf(text: str):
    nvars = nclauses = None
    clauses = []
    weights = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if parts[:3] in (["c", "p", "weight"], ["c", "p", "complex"]):
            if len(parts) != 7 or parts[-1] != "0":
                raise ValueError(f"unsupported weight grammar: {raw}")
            lit = int(parts[3])
            if not lit or lit in weights:
                raise ValueError(f"invalid/duplicate weight literal: {lit}")
            weights[lit] = (decimal_fraction(parts[4]), decimal_fraction(parts[5]))
        elif parts[:2] == ["c", "p"] and parts[2:3] == ["show"]:
            raise ValueError("projected counting is outside this PoC")
        elif parts[:3] == ["c", "t", "wmc"]:
            continue
        elif parts[0] == "c":
            # Only comments outside known weight metadata are ignored.
            continue
        elif parts[:2] == ["p", "cnf"] and len(parts) == 4:
            if nvars is not None:
                raise ValueError("duplicate header")
            nvars, nclauses = int(parts[2]), int(parts[3])
        else:
            if not parts or parts[-1] != "0":
                raise ValueError(f"unterminated clause: {raw}")
            clauses.append(tuple(int(x) for x in parts[:-1]))
    if nvars is None or nclauses is None or nvars < 0 or nclauses != len(clauses):
        raise ValueError("invalid/mismatched CNF header")
    if nvars > MAX_ORACLE_VARIABLES:
        raise ValueError(f"independent oracle is bounded to {MAX_ORACLE_VARIABLES} variables")
    for clause in clauses:
        if any(lit == 0 or abs(lit) > nvars for lit in clause):
            raise ValueError("clause literal outside variable range")
    if any(abs(lit) > nvars for lit in weights):
        raise ValueError("weight literal outside variable range")
    return nvars, clauses, weights


def cmul(a, b):
    return (a[0] * b[0] - a[1] * b[1],
            a[0] * b[1] + a[1] * b[0])


def oracle_count(text: str):
    nvars, clauses, weights = parse_cnf(text)
    total = (Fraction(0), Fraction(0))
    for bits in product((False, True), repeat=nvars):
        if not all(any((bits[abs(lit) - 1] if lit > 0 else not bits[-lit - 1])
                       for lit in clause) for clause in clauses):
            continue
        value = (Fraction(1), Fraction(0))
        for idx, on in enumerate(bits, 1):
            value = cmul(value, weights.get(idx if on else -idx, (Fraction(1), Fraction(0))))
        total = (total[0] + value[0], total[1] + value[1])
    return total


def parse_d4_count(stdout: str):
    matches = D4_RESULT.findall(stdout)
    if not matches:
        raise ValueError("d4 output lacks complex weighted count")
    results = []
    for kind, raw in matches:
        token = re.sub(r"\s+", "", raw)
        if kind == "int":
            if not re.fullmatch(r"[+-]?\d+", token):
                raise ValueError(f"invalid d4 integer count: {token!r}")
            results.append((Fraction(int(token)), Fraction(0)))
        elif token.endswith("i"):
            pair = COMPLEX.fullmatch(token)
            if not pair:
                raise ValueError(f"invalid d4 complex count: {token!r}")
            results.append((decimal_fraction(pair.group(1)), decimal_fraction(pair.group(2))))
        else:
            # The upstream counter selects a real-float output for real-only weights.
            results.append((decimal_fraction(token), Fraction(0)))
    if any(x != results[0] for x in results[1:]):
        raise ValueError("conflicting d4 count lines")
    return results[0]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def native_count(binary: Path, cnf: Path, timeout: int):
    if os.name != "posix":
        raise RuntimeError("bounded native pilot currently requires POSIX process groups")
    command = [str(binary.resolve()), "-i", str(cnf.resolve())]
    proc = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise RuntimeError("D4_POC_TIMEOUT") from exc
    if proc.returncode:
        raise RuntimeError(f"D4_POC_EXIT={proc.returncode}: {stderr[:1024]}")
    return parse_d4_count(stdout), {
        "returncode": proc.returncode,
        "stdout_sha256": sha256(stdout.encode()),
        "stderr_sha256": sha256(stderr.encode()),
        "command": command,
    }


# Hand-computable controls, not a replacement for real QuPRS-emitted CNF.
FIXTURES = {
    "unsat": "p cnf 1 2\nc t wmc\n1 0\n-1 0\n",
    "zero_weight": "p cnf 1 1\nc t wmc\nc p weight 1 0 0 0\n1 0\n",
    "free_variable": (
        "p cnf 2 1\nc t wmc\n"
        "c p weight 1 1 1 0\nc p weight -1 2 -1 0\n"
        "c p weight 2 2 0 0\nc p weight -2 -1 0 0\n1 0\n"
    ),
    "negative_complex": "p cnf 1 1\nc t wmc\nc p weight 1 -3 0.5 0\n1 0\n",
    "cancellation": (
        "p cnf 1 0\nc t wmc\n"
        "c p weight 1 0 1 0\nc p weight -1 0 -1 0\n"
    ),
    "global_phase": "p cnf 1 1\nc t wmc\nc p weight 1 -1 0 0\n1 0\n",
    "nondyadic_decimal": "p cnf 1 1\nc t wmc\nc p weight 1 0.1 0.2 0\n1 0\n",
    "both_polarities": (
        "p cnf 1 0\nc t wmc\n"
        "c p weight 1 1.5 -0.25 0\nc p weight -1 -0.5 0.25 0\n"
    ),
    "unweighted_free": "p cnf 3 0\nc t wmc\n",
}


def as_pair(value):
    return [str(value[0]), str(value[1])]


def classify_pilot_delta(observed, expected):
    """Screen grammar/large count errors; never certify native arithmetic.

    Tight band is the original numerical pilot target. Exploratory band is a
    deliberately weak compatibility screen for finite-precision upstream
    arithmetic, not suitable for QuPRS EQ/NEQ decisions.
    """
    difference = tuple(abs(o - e) for o, e in zip(observed, expected))
    scale = max(Fraction(1), *(abs(x) for x in expected))
    if all(d <= scale * Fraction(1, 10**25) for d in difference):
        status = "PILOT_TIGHT"
    elif all(d <= scale * Fraction(1, 10**15) for d in difference):
        status = "PILOT_NEAR_UNCERTIFIED"
    else:
        status = "PILOT_MISMATCH"
    return status, difference, scale


def run(args):
    workdir = args.workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    cases = []
    for name, content in FIXTURES.items():
        p = workdir / f"{name}.cnf"
        p.write_text(content, encoding="utf-8")
        cases.append((name, p))
    for i, path in enumerate(args.cnf):
        cases.append((f"quprs_{i}", path.resolve()))
    binary = args.binary.resolve() if args.binary else None
    if binary and not binary.is_file():
        raise FileNotFoundError(binary)
    records = []
    for name, path in cases:
        raw = path.read_bytes()
        expected = oracle_count(raw.decode("utf-8"))
        record = {"case": name, "cnf": str(path),
                  "cnf_sha256": sha256(raw), "oracle": as_pair(expected),
                  "native_status": "NOT_RUN"}
        if binary:
            try:
                observed, meta = native_count(binary, path, args.timeout)
            except (OSError, RuntimeError, ValueError) as exc:
                # Preserve a report for every attempted case, even if d4
                # crashes or fails to parse its own input/output format.
                record.update(native_status="NATIVE_ERROR", native_error=str(exc)[:1024])
            else:
                status, difference, scale = classify_pilot_delta(observed, expected)
                record.update(
                    native_status=status, observed=as_pair(observed),
                    absolute_error=as_pair(difference), error_scale=str(scale),
                    strict_pilot_band="1e-25 * max(1, abs(oracle components))",
                    exploratory_compatibility_band="1e-15 * max(1, abs(oracle components))",
                    solver_arithmetic_certified=False, **meta,
                )
        records.append(record)
    report = {"upstream_repo": UPSTREAM_REPO, "upstream_commit": UPSTREAM_SHA,
              "upstream_binary_sha256": sha256(binary.read_bytes()) if binary else None,
              "scope": "research-only; no QuPRS adapter or release claim",
              "precision_gate": "NOT_CERTIFIED",
              "pilot_status_counts": {status: sum(c["native_status"] == status for c in records)
                  for status in sorted({c["native_status"] for c in records})},
              "cases": records}
    output = workdir / "report.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "cases": len(records),
                      "native_runs": len(records) if binary else 0}, ensure_ascii=False))
    if binary and any(r["native_status"] not in
                      ("PILOT_TIGHT", "PILOT_NEAR_UNCERTIFIED") for r in records):
        raise SystemExit(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--binary", type=Path, help="pinned d4 C++ demo counter executable")
    parser.add_argument("--cnf", type=Path, action="append", default=[],
                        help="actual QuPRS-emitted weighted CNF, n <= 16 for exhaustive oracle")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    run(args)


if __name__ == "__main__":
    main()

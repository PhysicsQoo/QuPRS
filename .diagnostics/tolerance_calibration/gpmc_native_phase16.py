#!/usr/bin/env python3
"""Native GPMC conditional-UNSAT cache and DefVE verification (research only).

Builds an instrumented throwaway copy of the pinned GPMC submodule, runs
unmodified and instrumented binaries on identical weighted CNFs, and compares
both to an independent Fraction oracle. Never changes the Git submodule.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
from random import Random
import re
import shutil
import subprocess
import tempfile

from exact_gpmc_cnf_oracle import count_printed_cnf_exact
from gpmc_native_phase15 import encode, fixed_cases, fixture, read_solver
from gpmc_cache_phase15_probe import prepare, patch, SUMMARY

DEFVE = re.compile(r"P16_DEFVE nvars=(\d+) candidates=(\d+) accepted=(\d+)")
ELIM = re.compile(r"P16_DEFVE_ELIM requested=(\d+) completed=(\d+)")
MAX_SECONDS = 15


def strengthen_preproc(src: Path):
    path = src / "preprocessor/Preprocessor.cc"
    patch(path, "if(candv.size() == 0) return;",
          'if(candv.size() == 0) { std::cerr << "P16_DEFVE nvars=" '
          '<< ins->vars << " candidates=0 accepted=0\\n"; return; }')
    end = "if(cpuTime() - stime > config.dve_timelimit) break;\n\t}\n}"
    addition = (
        'if(cpuTime() - stime > config.dve_timelimit) break;\n\t}\n'
        'std::cerr << "P16_DEFVE nvars=" << ins->vars'
        ' << " candidates=" << candv.size()'
        ' << " accepted=" << vars.size() << "\\n";\n}'
    )
    patch(path, end, addition)
    patch(path, "int lastidx = ElimVars(vars);",
          'int lastidx = ElimVars(vars);\n'
          '        if (dve) std::cerr << "P16_DEFVE_ELIM requested="'
          ' << vars.size() << " completed=" << lastidx << "\\n";')


def gated_unsat(name: str, seed: int):
    # H is the eight length-three clauses excluding every assignment of x,y,z.
    # F = AND(s OR H_j) is satisfiable iff s=true. Under s=false, H is UNSAT
    # without any root-level unit clause.
    choices = []
    for i in range(8):
        choices.append(tuple([1] + [
            v if i & (1 << (v-2)) else -v for v in (2,3,4)
        ]))
    # Unit-free equivalences give the solver additional branching/reuse paths.
    if seed & 1:
        choices += [(-5, 6), (5, -6)]
    if seed & 2:
        choices += [(5, 6), (-5, -6)]
    if seed & 4:
        choices += [(-1, 7), (1, -7)]
    rng = Random(seed)
    positive = {v: rng.choice([(-1,0), (0,0), (1,0), (2,0), (0,1)])
                for v in range(1, 8)}
    negative = {v: rng.choice([(1,0), (2,0), (0,-1), (0,0)])
                for v in range(1, 8)}
    return fixture(name, 7, choices, positive, negative)


def cycle_cases():
    cases = fixed_cases()
    # XOR graph with all four literal weights equal for defined-variable
    # selection while preventing simple equivalent-literal merging.
    for j in range(8):
        case = fixture(
            "xor-equal-%02d" % j, 3,
            [(1, 2, -3), (-1, -2, -3),
             (-1, 2, 3), (1, -2, 3)],
            {1: (j+1,0), 2: (1,0), 3: (2,0)},
            {1: (j+1,0), 2: (1,0), 3: (2,0)})
        cases.append(case)
    for j in range(24):
        cases.append(gated_unsat("gated-unsat-%02d" % j, j))
    return cases


def execute(binary: Path, cnf: Path, flags: list[str], stem: Path):
    cmd = [str(binary), "-mode=1", "-prec=90", "-cs=16", *flags, str(cnf)]
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=MAX_SECONDS)
    stem.parent.mkdir(parents=True, exist_ok=True)
    stem.with_suffix(".stdout").write_text(cp.stdout)
    stem.with_suffix(".stderr").write_text(cp.stderr)
    if cp.returncode:
        raise RuntimeError("%s exit %s: %s" %
                           (cnf.name, cp.returncode, cp.stderr[-800:]))
    count, sat, _ = read_solver(cp.stdout)
    return {"count": count, "sat": sat,
            "summary": SUMMARY.findall(cp.stderr),
            "defve": [tuple(map(int, x)) for x in DEFVE.findall(cp.stderr)],
            "eliminated": [tuple(map(int, x)) for x in ELIM.findall(cp.stderr)]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    output = a.output.resolve()
    results = []
    accepted = eliminated = store_unsat_zero = hit_zero = hit_all = 0
    with tempfile.TemporaryDirectory(prefix="p16-gpmc-") as scratch:
        root = Path(scratch)
        source = root / "src"
        prepare(a.source.resolve(), source)
        strengthen_preproc(source)
        # The baseline binary remains entirely unchanged.
        for command, label in (
            (["cmake", "-S", str(source), "-B", str(root / "build"),
              "-DCMAKE_BUILD_TYPE=Release"], "configure"),
            (["cmake", "--build", str(root / "build"), "-j", "4"], "compile"),
        ):
            cp = subprocess.run(command, text=True, capture_output=True, timeout=240)
            (output / (label + ".stdout")).write_text(cp.stdout)
            (output / (label + ".stderr")).write_text(cp.stderr)
            if cp.returncode:
                raise RuntimeError("instrumented native " + label + " failure: "
                                   + cp.stderr[-1500:])
        probe = root / "build" / "gpmc"
        (output / "binary-shas.json").write_text(json.dumps({
            "baseline": sha256(a.baseline.read_bytes()).hexdigest(),
            "instrumented": sha256(probe.read_bytes()).hexdigest()}, indent=2))
        cases = cycle_cases()
        for case in cases:
            cnf_text = encode(case)
            src_cnf = output / (case["name"] + ".cnf")
            src_cnf.write_text(cnf_text)
            oracle = count_printed_cnf_exact(cnf_text)
            if oracle["status"] != "observed":
                raise AssertionError("oracle skipped fixture")
            exact = (oracle["real"], oracle["imag"])
            exists = oracle["satisfying_assignments"] > 0
            # One run with full DefVE, another skipping preprocessing main loop
            # to isolate the effect. Backjump off for selected gated-unsat
            # experiments to increase reachability of chronological UNSAT.
            modes = [("defve", ["-no-pp_ee", "-ppreps=1"]),
                     ("no-defve", ["-varlim=0"])]
            if case["name"].startswith("gated-unsat"):
                modes.append(("chronological", ["-no-pp_ee", "-no-bj",
                                                "-ppreps=1"]))
            for mode, flags in modes:
                name = case["name"] + "-" + mode
                b = execute(a.baseline.resolve(), src_cnf, flags,
                            output / (name + "-baseline"))
                v = execute(probe, src_cnf, flags,
                            output / (name + "-probe"))
                if not (b["count"] == v["count"] == exact and
                        b["sat"] == v["sat"] == exists):
                    raise AssertionError("Native GPMC exact model mismatch: " + name
                        + " baseline=" + repr(b) + " probe=" + repr(v))
                if len(v["summary"]) != 1:
                    raise AssertionError("Missing source-level cache summary: " + name)
                cache = list(map(int, v["summary"][0]))
                accepted += sum(x[2] for x in v["defve"])
                eliminated += sum(x[1] for x in v["eliminated"])
                store_unsat_zero += cache[2]
                hit_all += cache[4]
                hit_zero += cache[5]
                result = {
                    "case": case["name"], "mode": mode,
                    "count": list(map(str, exact)), "sat": exists,
                    "cache_stores": cache[0], "cache_zero_stores": cache[1],
                    "cache_unsat_zero_stores": cache[2],
                    "cache_sat_zero_stores": cache[3],
                    "cache_hits": cache[4], "cache_zero_hits": cache[5],
                    "defve": v["defve"], "defve_eliminated": v["eliminated"],
                    "cnf_sha256": sha256(cnf_text.encode()).hexdigest()
                }
                results.append(result)
                if cache[2] or cache[5] or sum(x[2] for x in v["defve"]):
                    print("P16_INTERESTING " + json.dumps(result), flush=True)
        if accepted == 0 or eliminated == 0:
            raise AssertionError("Native DefVE path not exercised (no accepted+eliminated candidate)")
    summary = {
        "status": "NATIVE_WMC_SAT_PASS",
        "n_cases": len(cycle_cases()), "n_runs": len(results),
        "defined_candidates_accepted": accepted,
        "defined_variables_eliminated": eliminated,
        "native_cache_hits": hit_all,
        "native_cache_zero_hits": hit_zero,
        "native_cache_unsat_zero_stores": store_unsat_zero,
        "unsat_zero_cache_hit_reproduced": False,
        "notes": "Absence of an UNSAT-zero store/hit is not proof of unreachability.",
        "results": results
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("P16_SUMMARY " + json.dumps({k:v for k,v in summary.items()
                                     if k!="results"}), flush=True)


if __name__ == "__main__":
    main()

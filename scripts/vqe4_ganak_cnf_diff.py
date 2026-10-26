#!/usr/bin/env python3
"""Same-source WMC singleton phase encoding: original auxiliary vs direct weighted x.

Only research diagnostics; emitted CNFs are from exact pinned native Rust miters.
Weighted model-count equivalence is unit-tested separately, not inferred from
floating-point solver output or identical source signatures.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import statistics
import subprocess
import time

ROOT = Path("vqe4-cnf-evidence")
VARIANTS = ("base", "head")
SOLVERS = ("ganak", "gpmc")
ARGS = {"ganak": "--mode=6", "gpmc": "-mode=1"}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def profile_cnf(path):
    lines = Path(path).read_text().splitlines()
    header = [s for s in lines if s.startswith("p cnf ")]
    if len(header) != 1: raise ValueError("Unexpected DIMACS header")
    _, _, nvars, nclauses = header[0].split()
    weights = [s for s in lines if s.startswith("c p weight ")]
    clauses = [s for s in lines if s and not s.startswith(("c ", "p "))]
    if len(clauses) != int(nclauses): raise ValueError("Invalid clause count")
    widths = Counter(len(s.split()) - 1 for s in clauses)
    tokens = Counter(" ".join(s.split()[4:]) for s in weights)
    return {
        "sha256": sha(path), "vars": int(nvars), "clauses": int(nclauses),
        "weighted_entries": len(weights),
        "widths": dict(sorted(widths.items())),
        "weight_value_multiset": dict(sorted(tokens.items())),
    }

def run():
    ROOT.mkdir(exist_ok=True)
    profiles = {}
    binaries = {}
    phases = {}
    for v in VARIANTS:
        folder = ROOT / v
        phases[v] = sha(folder / "phase-signatures.tsv")
        profiles[v] = {}
        binaries[v] = {}
        for solver in SOLVERS:
            profiles[v][solver] = profile_cnf(folder / f"vqe4-{solver}.cnf")
            binaries[v][solver] = sha(folder / solver)
            (folder / f"{solver}-profile.json").write_text(
                json.dumps(profiles[v][solver], indent=2) + "\n")
    if phases["base"] != phases["head"]:
        raise ValueError("Optimization altered source-exact reduced phase polynomial")
    for solver in SOLVERS:
        if binaries["base"][solver] != binaries["head"][solver]:
            raise ValueError("Revision solver binaries differ: " + solver)
        base = profiles["base"][solver]
        head = profiles["head"][solver]
        if head["vars"] >= base["vars"] or head["clauses"] >= base["clauses"]:
            raise ValueError("No measured CNF structural reduction: " + solver)
    trials = []
    plan = ("base", "head", "head", "base")
    for round_id, variant in enumerate(plan):
        for solver in SOLVERS:
            for repetition in range(8):
                warm = repetition < 2
                path = (ROOT / variant / f"vqe4-{solver}.cnf").resolve()
                cmd = [str((ROOT / variant / solver).resolve()), ARGS[solver], str(path)]
                start = time.perf_counter_ns()
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      timeout=50, check=False)
                sec = (time.perf_counter_ns() - start) / 1e9
                if proc.returncode:
                    raise RuntimeError(f"Native solver {solver} failed on {variant}: {proc.stderr[-800:]}")
                if not any(x.startswith(("c s exact ", "s ")) for x in proc.stdout.splitlines()):
                    raise ValueError(f"Missing weighted count: {solver}/{variant}")
                record = {
                    "round": round_id, "variant": variant, "solver": solver,
                    "repeat": repetition, "warmup": warm,
                    "wall_seconds": sec, "mode": ARGS[solver],
                    "cnf_sha256": sha(path), "binary_sha256": binaries[variant][solver],
                    "stdout_tail": proc.stdout[-1200:], "stderr_tail": proc.stderr[-500:],
                }
                trials.append(record)
                print(f"VQE4_CNF_NATIVE round={round_id} variant={variant} "
                      f"solver={solver} warm={warm} sec={sec:.6f}", flush=True)
    (ROOT / "trials.json").write_text(json.dumps(trials, indent=2) + "\n")
    medians = {}
    for solver in SOLVERS:
        medians[solver] = {}
        for v in VARIANTS:
            samples = [x["wall_seconds"] for x in trials if x["solver"] == solver
                       and x["variant"] == v and not x["warmup"]]
            if len(samples) != 12: raise ValueError("Unexpected paired sample count")
            medians[solver][v] = statistics.median(samples)
        medians[solver]["ratio"] = medians[solver]["head"] / medians[solver]["base"]
    output = {
        "schema": "vqe4-source-exact-singleton-weight-optimization-v1",
        "base_phase_sha256": phases["base"], "head_phase_sha256": phases["head"],
        "solver_binaries": binaries, "cnf": profiles, "medians": medians,
        "observations": len(trials),
        "notes": [
            "Both source versions have exact same reduced Path-sum phase polynomial",
            "Distinct CNF encodings must preserve theoretical exact weighted model counts",
            "Native complex results are floating observations, not rigorous solver arithmetic certificates",
            "Same hosted runner; not a dedicated physical CPU",
            "Hash-map literal ordering can vary without affecting CNF equivalence",
        ]
    }
    (ROOT / "summary.json").write_text(json.dumps(output, indent=2) + "\n")
    print("VQE4_WMC_COMPARE " + json.dumps({
        "ratio": {k:v["ratio"] for k,v in medians.items()},
        "vars": {s:{v:profiles[v][s]["vars"] for v in VARIANTS} for s in SOLVERS},
        "clauses": {s:{v:profiles[v][s]["clauses"] for v in VARIANTS} for s in SOLVERS},
    }), flush=True)

if __name__ == "__main__":
    run()

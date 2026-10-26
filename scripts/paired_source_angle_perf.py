#!/usr/bin/env python3
"""Paired same-VM A-B-B-A source-angle performance experiment.

Uses public QuPRS calls, both installed native solvers, identical historical
positive circuit pairs and separate source-specific virtual environments.
Preserves raw timings; no hosted 10-percent correctness/performance gate.
"""
import argparse
import json
import math
from pathlib import Path
import statistics
import subprocess
import time

CASES = (
    ("grover4", "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "Proportional", True),
    ("vqe4", "vqe_nativegates_ibm_qiskit_opt0_4.qasm", "Proportional", False),
    ("qaoa7", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "Proportional", False),
    ("ghz32", "ghz_nativegates_ibm_qiskit_opt0_32.qasm", "Straightforward", True),
)
BACKENDS = ("rust", "python")
SOLVERS = ("gpmc", "ganak")


def _number(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)) else None


def run_trial(a):
    from QuPRS import check_equivalence

    root = Path(a.root).resolve()
    result_rows = []
    for case, filename, strategy, reverse in CASES:
        left = root / "benchmarks/MQTBench" / filename
        right = root / "benchmarks/MQTBench/h,ry,rz,cx" / filename
        if not left.is_file() or not right.is_file():
            raise ValueError("Benchmark QASM file not found: " + filename)
        if reverse:
            left, right = right, left
        for backend in BACKENDS:
            for solver in SOLVERS:
                for trial in range(-a.warmups, a.repeats):
                    start = time.perf_counter_ns()
                    v = check_equivalence(str(left), str(right),
                                          method="hybrid", strategy=strategy,
                                          tool_name=solver, backend=backend, timeout=60)
                    seconds = (time.perf_counter_ns() - start) / 1e9
                    if v.equivalent not in ("equivalent", "equivalent*"):
                        raise RuntimeError(f"Unexpected verdict {case}/{backend}/{solver}: {v.equivalent}")
                    if trial >= 0:
                        result_rows.append({
                            "case": case, "backend": backend, "solver": solver,
                            "iteration": trial, "status": v.equivalent,
                            "elapsed_seconds": seconds,
                            "pathsum_seconds": _number(getattr(v, "pathsum_time", None)),
                            "solver_seconds": _number(getattr(v, "tool_time", None)),
                        })
    Path(a.json_output).write_text(json.dumps({
        "schema": "source-angle-paired-trial-v1", "samples": result_rows,
    }, indent=2) + "\n")


def orchestrate(a):
    destination = Path(a.out).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    plan = (("base", a.base_python, a.base_root),
            ("head", a.head_python, a.head_root),
            ("head", a.head_python, a.head_root),
            ("base", a.base_python, a.base_root))
    samples = {}
    for run, (variant, executable, root) in enumerate(plan):
        output = destination / f"trial-{run:02d}-{variant}.json"
        cmd = [str(Path(executable).resolve()), str(Path(__file__).resolve()),
               "--mode", "trial", "--root", root, "--json-output", str(output),
               "--warmups", str(a.warmups), "--repeats", str(a.repeats)]
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                              timeout=600, check=False)
        (destination / f"trial-{run:02d}-{variant}.stdout.txt").write_text(proc.stdout)
        (destination / f"trial-{run:02d}-{variant}.stderr.txt").write_text(proc.stderr)
        if proc.returncode:
            raise RuntimeError(f"Trial {run} {variant} exited {proc.returncode}")
        data = json.loads(output.read_text())
        if data.get("schema") != "source-angle-paired-trial-v1":
            raise ValueError("Invalid trial schema")
        for row in data["samples"]:
            key = variant, row["case"], row["backend"], row["solver"]
            samples.setdefault(key, []).append(row["elapsed_seconds"])
        print(f"{run+1}/4 {variant}: {len(data['samples'])} timed observations", flush=True)

    table = []
    for case, _, _, _ in CASES:
        for backend in BACKENDS:
            for solver in SOLVERS:
                old = samples.get(("base", case, backend, solver), [])
                new = samples.get(("head", case, backend, solver), [])
                if len(old) != 2 * a.repeats or len(new) != 2 * a.repeats:
                    raise ValueError(f"Missing samples for {case}/{backend}/{solver}")
                baseline, candidate = statistics.median(old), statistics.median(new)
                table.append({
                    "case": case, "backend": backend, "solver": solver,
                    "base_count": len(old), "head_count": len(new),
                    "base_median_seconds": baseline, "head_median_seconds": candidate,
                    "head_over_base": candidate / baseline,
                })
                print(f"{case}/{backend}/{solver}: HEAD/BASE {candidate/baseline:.3f}", flush=True)
    (destination / "summary.json").write_text(json.dumps({
        "schema": "source-angle-paired-summary-v1", "order": [x[0] for x in plan],
        "warmups": a.warmups, "repeats_per_round": a.repeats,
        "scope": "Same hosted VM; two separately built source trees; not pinned physical CPU",
        "comparisons": table,
    }, indent=2) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("orchestrate", "trial"), default="orchestrate")
    p.add_argument("--base-python")
    p.add_argument("--head-python")
    p.add_argument("--base-root")
    p.add_argument("--head-root")
    p.add_argument("--root")
    p.add_argument("--json-output")
    p.add_argument("--out")
    p.add_argument("--warmups", type=int, default=1)
    p.add_argument("--repeats", type=int, default=5)
    a = p.parse_args()
    if not 0 <= a.warmups <= 3 or not 2 <= a.repeats <= 20:
        p.error("Unbounded sample plan")
    if a.mode == "trial":
        if not a.root or not a.json_output:
            p.error("Missing trial paths")
        run_trial(a)
    else:
        if not all((a.base_python, a.head_python, a.base_root, a.head_root, a.out)):
            p.error("Missing paired paths")
        orchestrate(a)


if __name__ == "__main__":
    main()

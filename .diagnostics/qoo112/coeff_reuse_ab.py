#!/usr/bin/env python3
"""Source-pinned same-host A/B for isolated phase-expansion reuse.

Genuine baseline and candidate wheels are independently installed into venvs.
All elapsed timings come from check_equivalence with the profiler disabled.
The phase-probe stage is diagnostic only and is excluded from performance ratios.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

CASES = ("qaoa7", "grover4")
VARIANTS = ("baseline", "candidate")
BLOCKS = 3
DEADLINE = 60
OUTER_TIMEOUT = 90


def digest(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def stats(samples):
    if not samples:
        return None
    m = statistics.median(samples)
    return {"n": len(samples), "median": m,
            "mad": statistics.median(abs(v - m) for v in samples),
            "values": samples}


def one_sample(root, python_binaries, case, variant, block, position, kind,
               oracle=False):
    case_script = root / ".diagnostics/qoo112/coeff_reuse_case.py"
    command = [
        str(python_binaries[variant]), "-u", str(case_script),
        "--case", case, "--variant", variant,
        "--case-root", str(root / "benchmarks/MQTBench"),
        "--timeout", str(DEADLINE),
    ]
    if kind == "probe":
        command.append("--probe")
    if oracle:
        command.append("--oracle")
    meta = {
        "case": case, "variant": variant, "block": block,
        "position": position, "kind": kind, "command": command,
        "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    started = time.perf_counter()
    try:
        run = subprocess.run(
            command, capture_output=True, text=True, timeout=OUTER_TIMEOUT,
        )
        meta["exit_code"] = run.returncode
        meta["stdout"] = run.stdout[-2500:]
        meta["stderr"] = run.stderr[-5000:]
        try:
            data = json.loads(run.stdout.strip().splitlines()[-1])
            meta["result"] = data
        except (IndexError, ValueError):
            meta["error"] = "INVALID_JSON_OUTPUT"
    except subprocess.TimeoutExpired as e:
        meta["exit_code"] = None
        meta["error"] = "PROCESS_TIMEOUT"
        meta["stderr"] = repr(e)[-2500:]
    meta["outer_elapsed_seconds"] = time.perf_counter() - started
    result = meta.get("result", {})
    print("RUN", case, variant, kind, block, position,
          result.get("status", meta.get("error", "NO_RESULT")),
          "%.3f" % meta["outer_elapsed_seconds"], flush=True)
    return meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-python", type=Path, required=True)
    parser.add_argument("--candidate-python", type=Path, required=True)
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, default=Path("qoo112-coeff-reuse-results"))
    args = parser.parse_args()
    root = Path.cwd().resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # IMPORTANT: venv/bin/python is usually a symlink to the hosted interpreter.
    # .resolve() escapes the venv and loses its site-packages.
    py = {"baseline": Path(os.path.abspath(args.baseline_python)),
          "candidate": Path(os.path.abspath(args.candidate_python))}
    for binary in py.values():
        if not binary.exists():
            raise FileNotFoundError(binary)
    files = [
        root / ".diagnostics/qoo112/coeff_reuse_case.py",
        root / ".diagnostics/qoo112/coeff_reuse_ab.py",
    ]
    for case in CASES:
        name = "qaoa_nativegates_ibm_qiskit_opt0_7.qasm" if case == "qaoa7" else "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm"
        files += [root / "benchmarks/MQTBench" / name,
                  root / "benchmarks/MQTBench/h,ry,rz,cx" / name]
    affinity_before = sorted(os.sched_getaffinity(0))
    core = affinity_before[0]
    os.sched_setaffinity(0, {core})
    os.environ.update(PYTHONHASHSEED="0", OMP_NUM_THREADS="1",
                      OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    manifest = {
        "schema": 1,
        "baseline_sha": args.baseline_sha,
        "candidate_sha": args.candidate_sha,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_affinity_before": affinity_before, "cpu_affinity_used": core,
        "executable_path": {k: str(v) for k, v in py.items()},
        "solver": "gpmc", "method": "hybrid", "backend": "python",
        "strategy": "Proportional", "cases": CASES,
        "blocks": BLOCKS, "run_timeout_seconds": DEADLINE,
        "process_timeout_seconds": OUTER_TIMEOUT,
        "qasm_and_harness_sha256": {str(p.relative_to(root)): digest(p) for p in files},
        "pythonhashseed": os.environ["PYTHONHASHSEED"],
    }
    for variant, binary in py.items():
        freeze = subprocess.run([str(binary), "-m", "pip", "freeze"],
                                text=True, capture_output=True)
        manifest[variant + "_pip_freeze"] = freeze.stdout
    (output / "environment.json").write_text(json.dumps(manifest, indent=2) + "\n")
    results = []
    failures = []
    with (output / "samples.jsonl").open("w", buffering=1) as fp:
        for case in CASES:
            # Coarse operation timer, disjoint from the actual A/B benchmark.
            for variant in VARIANTS:
                row = one_sample(root, py, case, variant, -2, 0, "probe", oracle=True)
                fp.write(json.dumps(row) + "\n")
                results.append(row)
                if not good(row):
                    failures.append({"case": case, "variant": variant, "kind": "probe",
                                     "status": row.get("result", {}).get("status"),
                                     "error": row.get("error")})
            if failures:
                continue
            for variant in VARIANTS:
                row = one_sample(root, py, case, variant, -1, 0, "warmup")
                fp.write(json.dumps(row) + "\n")
                results.append(row)
                if not good(row):
                    failures.append({"case": case, "variant": variant, "kind": "warmup"})
            if failures:
                continue
            for block in range(BLOCKS):
                order = ("baseline", "candidate", "candidate", "baseline") if block % 2 == 0 else ("candidate", "baseline", "baseline", "candidate")
                for position, variant in enumerate(order):
                    row = one_sample(root, py, case, variant, block, position, "measure")
                    fp.write(json.dumps(row) + "\n")
                    results.append(row)
                    if not good(row):
                        failures.append({"case": case, "variant": variant, "kind": "measure",
                                         "block": block, "position": position,
                                         "error": row.get("error"),
                                         "status": row.get("result", {}).get("status")})
                        break
                if failures:
                    break
    comparisons = []
    for case in CASES:
        case_rows = [x for x in results if x["case"] == case]
        measured = [x for x in case_rows if x["kind"] == "measure" and good(x)]
        times = {v: stats([x["result"]["elapsed_seconds"] for x in measured
                           if x["variant"] == v]) for v in VARIANTS}
        paired = []
        for block in range(BLOCKS):
            b = [x["result"]["elapsed_seconds"] for x in measured
                 if x["variant"] == "baseline" and x["block"] == block]
            c = [x["result"]["elapsed_seconds"] for x in measured
                 if x["variant"] == "candidate" and x["block"] == block]
            if len(b) == len(c) == 2 and statistics.median(b) > 0:
                paired.append(statistics.median(c) / statistics.median(b))
        status_set = sorted({x["result"]["status"] for x in case_rows if good(x)})
        if len(paired) != BLOCKS or len(status_set) != 1:
            failures.append({"case": case, "error": "INCOMPLETE_BLOCK_OR_STATUS_MISMATCH",
                             "paired": len(paired), "status_set": status_set})
        probes = {x["variant"]: x["result"]["stage_operations"]
                  for x in case_rows if x["kind"] == "probe" and good(x)}
        comparisons.append({"case": case, "samples": len(measured), "statuses": status_set,
                            "time_seconds": times,
                            "paired_ratio": stats(paired),
                            "operation_cost_pilot": probes})
    report = {"schema": 1, "outcome": "PASS" if not failures else "INCOMPLETE",
              "failures": failures, "comparisons": comparisons,
              "note": "Benchmark ratios measured without AST instrumentation. "
              "Probe operation timers are distinct pilot runs; no claim of algorithmic speedup without noise review."}
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    markdown = [
        "# Shared Omega/HH coeff-reuse A/B",
        "Same host, separate baseline/candidate installations, 3 ABBA/BAAB blocks each.",
        "",
        "| Case | Status | Samples | Baseline median (s) | Candidate median (s) | Paired ratio | MAD |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for x in comparisons:
        b = x["time_seconds"]["baseline"]
        c = x["time_seconds"]["candidate"]
        ratio = x["paired_ratio"]
        f = lambda d, key="median": "N/A" if d is None else ("%.6f" % d[key])
        markdown.append("| %s | %s | %s | %s | %s | %s | %s |" %
                        (x["case"], ",".join(x["statuses"]), x["samples"],
                         f(b), f(c), f(ratio), f(ratio, "mad")))
        for variant, probe in x["operation_cost_pilot"].items():
            markdown += ["", "## %s %s expand/coeff pilot" % (x["case"], variant),
                         "| Call site | Calls | Wall seconds |", "|---|---:|---:|"]
            for key, p in sorted(probe.items(), key=lambda kv: kv[1]["total_ns"], reverse=True):
                markdown.append("| %s | %d | %.6f |" %
                                (key, p["calls"], p["total_ns"] / 1e9))
    markdown += ["", "Outcome: " + report["outcome"]]
    (output / "summary.md").write_text("\n".join(markdown) + "\n")
    print("\n".join(markdown), flush=True)
    return 0 if not failures else 2


def good(row):
    value = row.get("result", {})
    return (row.get("exit_code") == 0
            and value.get("status") in ("equivalent", "equivalent*")
            and (value.get("oracle") in (None, value.get("status"))))


if __name__ == "__main__":
    sys.exit(main())

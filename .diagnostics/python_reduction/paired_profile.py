#!/usr/bin/env python3
"""One-run same-host A/B profiling for two representative Python reductions.

One subprocess per observation prevents accumulated SymEngine caches; the measured
elapsed_seconds comes from the public check_equivalence call, excluding startup
and QASM load. The subprocess wall time and raw output are retained separately.
"""
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
INPUTS = {
    "qaoa7": "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
    "grover4": "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
}
MODES = ("off", "on")
BLOCKS = 2
TIMEOUT = 65
SUBPROCESS_TIMEOUT = 85
OUTPUT = Path("python-reduction-profile-results").resolve()
SCRIPT = Path(".diagnostics/python_reduction/profile.py").resolve()
CASES_ROOT = Path("benchmarks/MQTBench").resolve()


def median_mad(xs):
    if not xs:
        return None
    m = statistics.median(xs)
    return {"median": m, "mad": statistics.median(abs(x - m) for x in xs),
            "n": len(xs), "raw": list(xs)}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_sample(case, mode, block, position, warmup=False):
    label = "warmup" if warmup else "sample"
    suffix = "%s_%s_%s_%s_%s" % (case, mode, label, block, position)
    json_path = OUTPUT / "individual" / (suffix + ".json")
    args = [sys.executable, "-u", str(SCRIPT), "--output", str(json_path),
            "--case-root", str(CASES_ROOT), "--cases", case,
            "--solver", "gpmc", "--timeout", str(TIMEOUT)]
    if mode == "on":
        args.append("--profile")
    record = {"case": case, "mode": mode, "block": block, "position": position,
              "warmup": warmup, "command": args, "timeout_seconds": SUBPROCESS_TIMEOUT,
              "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    started = time.perf_counter()
    try:
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                timeout=SUBPROCESS_TIMEOUT, check=False)
        record.update(returncode=result.returncode, stdout=result.stdout[-7000:],
                      stderr=result.stderr[-16000:])
        if json_path.is_file():
            payload = json.loads(json_path.read_text())
            record["profile"] = payload
            record["elapsed_seconds"] = payload["cases"][0]["elapsed_seconds"]
            record["status"] = payload["cases"][0]["status"]
    except subprocess.TimeoutExpired as exc:
        record.update(returncode=None, status="PROCESS_TIMEOUT",
                      stdout=(exc.stdout or b"").decode(errors="replace")[-7000:]
                      if isinstance(exc.stdout, bytes) else (exc.stdout or "")[-7000:],
                      stderr=(exc.stderr or b"").decode(errors="replace")[-16000:]
                      if isinstance(exc.stderr, bytes) else (exc.stderr or "")[-16000:])
    except Exception as exc:
        record.update(returncode=None, status="ERROR", error=repr(exc))
    record["subprocess_wall_seconds"] = time.perf_counter() - started
    print("MEASURE", case, mode, label, block, position,
          record.get("status", "NO_RESULT"),
          round(record["subprocess_wall_seconds"], 4), "s", flush=True)
    return record


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "individual").mkdir(parents=True, exist_ok=True)
    if not SCRIPT.is_file():
        raise FileNotFoundError(SCRIPT)
    qasm_files = [CASES_ROOT / INPUTS[c] for c in CASES] + [
        CASES_ROOT / "h,ry,rz,cx" / INPUTS[c] for c in CASES]
    for path in qasm_files:
        if not path.is_file():
            raise FileNotFoundError(path)
    cpu_before = sorted(os.sched_getaffinity(0))
    cpu = cpu_before[0]
    os.sched_setaffinity(0, {cpu})
    os.environ.update(PYTHONHASHSEED="0", OMP_NUM_THREADS="1",
                      OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    def capture(command):
        p = subprocess.run(command, text=True, capture_output=True, check=False)
        return {"exit_code": p.returncode, "output": (p.stdout + p.stderr)[-30000:]}
    manifest = {
        "schema": 1, "method": "same-runner sequential ABBA/BAAB",
        "python_version": platform.python_version(),
        "platform": platform.platform(), "case_root": str(CASES_ROOT),
        "cases": CASES, "modes": MODES, "blocks": BLOCKS,
        "solver": "gpmc", "backend": "python", "strategy": "Proportional",
        "method_quprs": "hybrid",
        "requested_timeout_seconds": TIMEOUT, "subprocess_timeout_seconds": SUBPROCESS_TIMEOUT,
        "cpu_affinity_original": cpu_before, "cpu_affinity_used": [cpu],
        "env": {k: os.environ.get(k) for k in
                ("PYTHONHASHSEED", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
        "git": capture(["git", "rev-parse", "HEAD"]),
        "pip_freeze": capture([sys.executable, "-m", "pip", "freeze"]),
        "lscpu": capture(["lscpu"]),
        "files_sha256": {str(p.relative_to(Path.cwd())): digest(p) for p in qasm_files + [SCRIPT]},
    }
    (OUTPUT / "environment.json").write_text(json.dumps(manifest, indent=2) + "\n")
    observations = []
    failures = []
    with (OUTPUT / "samples.jsonl").open("w", buffering=1) as raw:
        for case in CASES:
            # One warmup per mode, while still recording and checking its outcome.
            for mode in MODES:
                item = run_sample(case, mode, -1, 0, warmup=True)
                raw.write(json.dumps(item) + "\n")
                if item.get("returncode") != 0 or item.get("status") not in ("equivalent", "equivalent*"):
                    failures.append({"case": case, "stage": "warmup", "item": item})
            if any(f["case"] == case for f in failures):
                continue
            for block in range(BLOCKS):
                order = ("off", "on", "on", "off") if block % 2 == 0 else ("on", "off", "off", "on")
                for pos, mode in enumerate(order):
                    item = run_sample(case, mode, block, pos)
                    raw.write(json.dumps(item) + "\n")
                    observations.append(item)
                    if item.get("returncode") != 0 or item.get("status") not in ("equivalent", "equivalent*"):
                        failures.append({"case": case, "stage": "measurement",
                                         "mode": mode, "block": block, "position": pos,
                                         "status": item.get("status"), "returncode": item.get("returncode")})
                        break
                if any(f["case"] == case for f in failures):
                    break
    reports = []
    for case in CASES:
        rows = [x for x in observations if x["case"] == case and x.get("returncode") == 0
                and x.get("status") in ("equivalent", "equivalent*")]
        by_mode = {mode: [x["elapsed_seconds"] for x in rows if x["mode"] == mode]
                   for mode in MODES}
        ratios = []
        for block in range(BLOCKS):
            block_rows = [x for x in rows if x["block"] == block]
            a = [x["elapsed_seconds"] for x in block_rows if x["mode"] == "off"]
            b = [x["elapsed_seconds"] for x in block_rows if x["mode"] == "on"]
            if len(a) == len(b) == 2 and statistics.median(a) > 0:
                ratios.append(statistics.median(b) / statistics.median(a))
        stage = {}
        recursions = []
        for x in rows:
            if x["mode"] != "on":
                continue
            data = x["profile"]["cases"][0]
            recursions.append(data["recursion"])
            for key, value in data["timings"].items():
                rec = stage.setdefault(key, {"calls": [], "exclusive_seconds": [],
                                             "inclusive_seconds": []})
                rec["calls"].append(value["calls"])
                rec["exclusive_seconds"].append(value["exclusive_ns"] / 1e9)
                rec["inclusive_seconds"].append(value["inclusive_ns"] / 1e9)
        stage_summary = {key: {k: median_mad(v) for k, v in metric.items()}
                         for key, metric in stage.items()}
        if not stage_summary.get("free_symbols.output") or not stage_summary.get("free_symbols.phase"):
            failures.append({"case": case, "stage": "missing free_symbols counters"})
        if len(ratios) != BLOCKS:
            failures.append({"case": case, "stage": "insufficient ABBA/BAAB pairs",
                             "completed_blocks": len(ratios)})
        statuses = sorted({x.get("status") for x in rows})
        if len(statuses) != 1:
            failures.append({"case": case, "stage": "classification mismatch",
                             "statuses": statuses})
        reports.append({"case": case, "status": statuses, "samples": len(rows),
                        "timing_seconds": {m: median_mad(v) for m, v in by_mode.items()},
                        "paired_instrumentation_ratio": median_mad(ratios),
                        "stages": stage_summary, "recursion_samples": recursions})
    summary = {"schema": 1, "status": "PASS" if not failures else "INCOMPLETE",
               "failures": failures, "cases": reports,
               "interpretation": "Ratios quantify observer overhead, not solver/backend speedup. "
               "Exclusive stages are diagnostic and can vary with Python bookkeeping."}
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    lines = ["# Python Reduction Profiling: QAOA7 + Grover4",
             "Same runner, Python backend, GPMC hybrid, 2 ABBA/BAAB blocks, "
             "4 samples per mode per case.", "",
             "| Circuit | Samples | Off median (s) | On median (s) | Paired ratio |",
             "|---|---:|---:|---:|---:|"]
    for case in reports:
        off = case["timing_seconds"]["off"]
        on = case["timing_seconds"]["on"]
        ratio = case["paired_instrumentation_ratio"]
        def fmt(x):
            return "NOT_MEASURED" if x is None else "%.6f" % x["median"]
        lines.append("| %s | %d | %s | %s | %s |" %
                     (case["case"], case["samples"], fmt(off), fmt(on), fmt(ratio)))
        lines += ["", "## " + case["case"] + " stages (profiled samples)",
                  "| Stage | Calls median | Exclusive median (s) | Inclusive median (s) |",
                  "|---|---:|---:|---:|"]
        sorted_stages = sorted(case["stages"].items(),
                               key=lambda x: x[1]["exclusive_seconds"]["median"], reverse=True)
        for name, counts in sorted_stages:
            lines.append("| %s | %.1f | %.6f | %.6f |" %
                         (name, counts["calls"]["median"], counts["exclusive_seconds"]["median"],
                          counts["inclusive_seconds"]["median"]))
    lines += ["", "Experiment status: " + summary["status"],
              "This is instrumentation overhead, not an algorithmic speedup."]
    (OUTPUT / "summary.md").write_text("\n".join(lines) + "\n")
    for path in [OUTPUT / "summary.md", OUTPUT / "summary.json"]:
        print(path.read_text()[:20000] if path.suffix == ".md" else
              "SUMMARY_JSON " + str(path), flush=True)
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())

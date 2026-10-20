#!/usr/bin/env python3
"""Collect source-pinned, opt-in Rust native stage evidence, no speedup claims."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

CASES = ("qaoa7", "ghz4")
MODES = ("off", "on")
OUT = Path("rust-native-stage-results").resolve()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def process(command):
    r = subprocess.run(command, text=True, capture_output=True)
    return {"returncode": r.returncode, "stdout": r.stdout[-30000:],
            "stderr": r.stderr[-12000:]}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "individual").mkdir(exist_ok=True)
    affinity = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {affinity[0]})
    os.environ.update(PYTHONHASHSEED="0", OMP_NUM_THREADS="1",
                      OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    script = Path(".diagnostics/rust_stage_ledger/case.py").resolve()
    inputs = [script, Path(__file__).resolve(),
              Path("benchmarks/MQTBench/qaoa_nativegates_ibm_qiskit_opt0_7.qasm"),
              Path("benchmarks/MQTBench/h,ry,rz,cx/qaoa_nativegates_ibm_qiskit_opt0_7.qasm")]
    manifest = {
        "schema": "native-exclusive-stage-diagnostic-v0",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": process(["git", "rev-parse", "HEAD"]),
        "gpmc_gitlink": process(["git", "rev-parse", "HEAD:GPMC"]),
        "python": sys.version, "platform": platform.platform(),
        "affinity_before": affinity, "affinity_used": affinity[0],
        "pip_freeze": process([sys.executable, "-m", "pip", "freeze"]),
        "inputs_sha256": {str(p): sha(p) for p in inputs},
        "design": "Two cases, flag on/off per isolated process; attribution/correctness only",
    }
    (OUT / "environment.json").write_text(json.dumps(manifest, indent=2) + "\n")
    errors, results = [], []
    with (OUT / "samples.jsonl").open("w", buffering=1) as fp:
        for case in CASES:
            for mode in MODES:
                output = OUT / "individual" / (case + "_" + mode + ".json")
                command = [sys.executable, "-u", str(script), "--case", case,
                           "--output", str(output)]
                if mode == "on":
                    command.append("--profile")
                observation = {"case": case, "mode": mode,
                               "command": command, "hard_timeout": 110}
                started = time.perf_counter()
                try:
                    run = subprocess.run(command, capture_output=True, text=True,
                                         timeout=110)
                    observation.update(returncode=run.returncode,
                                       stdout=run.stdout[-10000:],
                                       stderr=run.stderr[-16000:])
                    if output.is_file():
                        observation["data"] = json.loads(output.read_text())
                except subprocess.TimeoutExpired as exc:
                    observation.update(returncode=None, error="HARD_TIMEOUT",
                                       stderr=str(exc))
                observation["process_wall_seconds"] = time.perf_counter() - started
                fp.write(json.dumps(observation) + "\n")
                results.append(observation)
                print("NATIVE_RUST", case, mode,
                      observation.get("returncode"), observation.get("stdout", "")[-350:],
                      flush=True)
                if observation.get("returncode") != 0 or "data" not in observation:
                    errors.append({"case": case, "mode": mode,
                                   "stderr": observation.get("stderr", ""),
                                   "error": observation.get("error")})
    for case in CASES:
        by_mode = {r["mode"]: r["data"] for r in results if r["case"] == case
                   and "data" in r and r.get("returncode") == 0}
        if set(by_mode) != set(MODES):
            errors.append({"case": case, "error": "MISSING_ON_OR_OFF"})
            continue
        if by_mode["off"]["status"] != by_mode["on"]["status"]:
            errors.append({"case": case, "error": "DIFFERENT_NATIVE_CLASSIFICATION"})
    samples = [r["data"] for r in results if "data" in r]
    summary = {
        "schema": "native-exclusive-stage-diagnostic-v0",
        "status": "PASS" if not errors else "INCOMPLETE",
        "errors": errors, "samples": samples,
        "caveats": [
            "One flag-on and flag-off request per circuit; not a performance A/B.",
            "Native core wall excludes FFI QASM parsing; wrapper wall includes the native FFI call.",
            "Child supervision wall includes spawn, wait, output and cleanup, not solver CPU time.",
            "Fine stages are Rust-only; Python comparative boundaries require a separately validated schema.",
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    report = ["# Opt-in native Rust stage timing", "",
              "| Case | Flag | Classification | Native wall (s) | GPMC children |",
              "|---|---|---|---:|---:|"]
    for sample in samples:
        raw = sample["native"]
        stage = raw["stage_ledger"]
        report.append("| %s | %s | %s | %.6f | %s |" % (
            sample["case"], "on" if sample["profile"] else "off",
            sample["status"], raw["verification_time_sec"],
            stage["solver_child_spawns"] if stage else "NOT_MEASURED"))
        if stage:
            report += ["", "## " + sample["case"] + " (native exclusive stages)",
                       "| Stage | Seconds |", "|---|---:|"]
            for name, value in stage["exclusive_seconds"].items():
                report.append("| %s | %.9f |" % (name, value))
    report.extend(["", "Result: " + summary["status"], "",
                   "On/off samples are for semantic parity, not performance speedup.",
                   "All raw FFI outputs are recorded in individual JSON files."])
    (OUT / "summary.md").write_text("\n".join(report) + "\n")
    print("\n".join(report), flush=True)
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())

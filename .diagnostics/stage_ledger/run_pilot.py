#!/usr/bin/env python3
"""One scoped Rust/Python stage ledger validation (QAOA7 + forced-WMC GHZ4).

Runs four isolated verification processes, each with its own predeclared
backend/method. Captures JSON evidence even when one backend fails, and fails
the Action rather than reclassifying a failure or guessing a missing stage.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

CASES = ("qaoa7", "ghz4_wmc_only")
BACKENDS = ("python", "rust")
HARD_TIMEOUT = 110
QU_PRS_TIMEOUT = 75
OUTPUT = Path("exclusive-stage-ledger-results").resolve()
ROOT = Path.cwd().resolve()
SCRIPT = ROOT / ".diagnostics/stage_ledger/exclusive_ledger.py"
QASMS = [
    ROOT / "benchmarks/MQTBench/qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
    ROOT / "benchmarks/MQTBench/h,ry,rz,cx/qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(*command):
    p = subprocess.run(list(command), capture_output=True, text=True)
    return {"code": p.returncode, "stdout": p.stdout[-16000:], "stderr": p.stderr[-10000:]}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path in (SCRIPT, *QASMS):
        if not path.is_file():
            raise FileNotFoundError(path)
    cpu_original = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu_original[0]})
    os.environ.update(
        PYTHONHASHSEED="0", OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
    )
    env = {
        "schema": "quprs-exclusive-stage-ledger-v0",
        "datetime_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": capture("git", "rev-parse", "HEAD"),
        "gpmc_gitlink": capture("git", "rev-parse", "HEAD:GPMC"),
        "python_version": sys.version,
        "platform": platform.platform(),
        "cpu_affinity_original": cpu_original,
        "cpu_affinity_used": [cpu_original[0]],
        "pip_freeze": capture(sys.executable, "-m", "pip", "freeze"),
        "module_files": {str(path.relative_to(ROOT)): digest(path)
                         for path in (SCRIPT, *QASMS)},
        "cases": CASES, "backends": BACKENDS,
        "verification_timeout_seconds": QU_PRS_TIMEOUT,
        "subprocess_hard_timeout_seconds": HARD_TIMEOUT,
        "hypothesis": (
            "Python fine time stages can be partitioned without overlap. "
            "Rust provides only coarse pathsum and WMC intervals. "
            "GHZ4 WMC-only must invoke actual GPMC subprocess on Python."
        ),
    }
    (OUTPUT / "environment.json").write_text(json.dumps(env, indent=2) + "\n")

    samples, failures = [], []
    for case in CASES:
        for backend in BACKENDS:
            basename = case + "_" + backend
            dest = OUTPUT / "individual" / (basename + ".json")
            cmd = [
                sys.executable, "-u", str(SCRIPT),
                "--case", case, "--backend", backend,
                "--case-root", str(ROOT / "benchmarks/MQTBench"),
                "--timeout", str(QU_PRS_TIMEOUT),
                "--output", str(dest),
            ]
            sample = {"case": case, "backend": backend, "command": cmd}
            start = time.perf_counter()
            try:
                p = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=HARD_TIMEOUT)
                sample["exit_code"] = p.returncode
                sample["stdout"] = p.stdout[-10000:]
                sample["stderr"] = p.stderr[-16000:]
                if dest.is_file():
                    sample["data"] = json.loads(dest.read_text())
                else:
                    sample["error"] = "NO_JSON"
            except subprocess.TimeoutExpired as exc:
                sample["exit_code"] = None
                sample["error"] = "HARD_PROCESS_TIMEOUT"
                sample["stderr"] = repr(exc)
            sample["process_wall_seconds"] = time.perf_counter() - start
            data = sample.get("data", {})
            print("LEDGER_CASE", case, backend,
                  data.get("result", sample.get("error", "no_result")),
                  "exit", sample.get("exit_code"),
                  "elapsed", round(sample["process_wall_seconds"], 4),
                  flush=True)
            samples.append(sample)
            if sample.get("exit_code") != 0 or not data:
                failures.append({"case": case, "backend": backend,
                                 "error": sample.get("error"), "stderr": sample.get("stderr")})
                continue
            stage = data["measurement"]
            if abs(stage["closure_error_seconds"]) > 1e-6:
                failures.append({"case": case, "backend": backend, "error": "LEDGER_NOT_CLOSED"})
            if data["result"] != data["independent_operator_oracle"]:
                failures.append({"case": case, "backend": backend, "error": "ORACLE_MISMATCH"})
            if case == "ghz4_wmc_only" and backend == "python" and data["actual_solver_invoked"] is not True:
                failures.append({"case": case, "backend": backend, "error": "NO_REAL_SOLVER_INVOCATION"})

    with (OUTPUT / "samples.jsonl").open("w") as fp:
        for sample in samples:
            fp.write(json.dumps(sample, sort_keys=True) + "\n")
    table = ["# Exclusive stage ledger: QAOA7 / forced-WMC GHZ4",
             "",
             "| Case | Backend | Status | Actual external solver? | Measured wall (s) | Stage coverage |",
             "|---|---|---|---|---:|---|"]
    for sample in samples:
        result = sample.get("data")
        if not result:
            table.append("| %s | %s | ERROR | N/A | N/A | Missing |" %
                         (sample["case"], sample["backend"]))
            continue
        stage = result["measurement"]
        table.append("| %s | %s | %s | %s | %.6f | %s |" %
                     (sample["case"], sample["backend"], result["result"],
                      result["actual_solver_invoked"],
                      stage["measured_wall_seconds"],
                      "fine Python" if sample["backend"] == "python" else "coarse Rust"))
        table += ["", "**" + sample["case"] + " " + sample["backend"] + "**",
                  "", "| Disjoint stage | Seconds |", "|---|---:|"]
        for name, duration in stage["exclusive_seconds"].items():
            table.append("| %s | %.9f |" % (name, duration))
    report = {
        "schema": "quprs-exclusive-stage-ledger-v0",
        "status": "PASS" if not failures else "INCOMPLETE",
        "n_cases": len(samples),
        "failures": failures,
        "samples": [s["data"] for s in samples if "data" in s],
        "explicit_caveats": [
            "One observation per backend/case; no speedup, variance, or cross-backend walltime claim.",
            "Rust stage resolution is coarse by design; absent components marked missing, never inferred.",
            "Do not add published pathsum_time, wmc_time, tool_time: nested intervals overlap.",
            "Python recorded subprocess duration includes process management, not solver CPU time.",
        ],
    }
    (OUTPUT / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    table.extend(["", "Status: " + report["status"],
                  "Only Python external solver invocation is instrumented and asserted.",
                  "Rust native solver invocation remains NOT_MEASURED in this schema."])
    (OUTPUT / "summary.md").write_text("\n".join(table) + "\n")
    print("\n".join(table), flush=True)
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())

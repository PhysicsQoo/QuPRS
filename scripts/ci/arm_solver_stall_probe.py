"""Bounded focused replay of the public Python/Ganak solver timeout case.

This is a diagnostic: no scientific test is skipped and any TIMEOUT remains a
failure. Descendants are discovered before termination and reaped best-effort.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import psutil

CASES = (
    ("single_no_cov", ["-n", "0"], False),
    ("single_cov", ["-n", "0", "--cov=src/QuPRS", "--cov-report="], False),
    ("xdist4_no_cov", ["-n", "4"], False),
    ("xdist4_cov", ["-n", "4", "--cov=src/QuPRS", "--cov-report="], False),
    # Broader but still bounded: reproduce contention across the full
    # fault-injection module, then its adjacent complex-weight fixtures.
    ("xdist_auto_failure_matrix_cov", ["-n", "auto", "--cov=src/QuPRS", "--cov-report="], True),
    ("xdist_auto_adjacent_cnf_cov", ["-n", "auto", "--cov=src/QuPRS", "--cov-report="], True),
)


def snapshot(pid):
    try:
        processes = [psutil.Process(pid)]
        processes.extend(processes[0].children(recursive=True))
        return [{
            "pid": p.pid,
            "ppid": p.ppid(),
            "status": p.status(),
            "name": p.name(),
        } for p in processes if p.is_running()]
    except psutil.Error:
        return []


def cleanup(proc):
    observed = snapshot(proc.pid)
    children = []
    for item in reversed(observed):
        try:
            children.append(psutil.Process(item["pid"]))
        except psutil.Error:
            pass
    for p in children:
        try:
            p.terminate()
        except psutil.Error:
            pass
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    elif proc.poll() is None:
        proc.terminate()
    _, remaining = psutil.wait_procs(children, timeout=3)
    for p in remaining:
        try:
            p.kill()
        except psutil.Error:
            pass
    if proc.poll() is None:
        proc.kill()
    try:
        proc.wait(timeout=4)
    except subprocess.TimeoutExpired:
        pass
    return observed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--budget-seconds", type=int, default=150)
    opt = parser.parse_args()
    if not 15 <= opt.budget_seconds <= 600:
        parser.error("budget outside safe range")
    opt.output.mkdir(parents=True, exist_ok=True)
    reports = []
    for name, flags, broader in CASES:
        selection = (
            ["test/test_solver_failure_matrix.py",
             "test/test_v0140_exact_printed_cnf.py"]
            if name == "xdist_auto_adjacent_cnf_cov"
            else ["test/test_solver_failure_matrix.py"]
            if broader
            else ["test/test_solver_failure_matrix.py::"
                  "test_public_wmc_solver_failure_is_never_inequivalence"]
        )
        cmd = [
            sys.executable, "-m", "pytest", *selection,
            "-v", "-ra", "-o", "faulthandler_timeout=45",
            "--disable-warnings", *flags,
        ]
        if not broader:
            cmd.extend(["-k", "python and ganak and timeout"])
        start = time.monotonic()
        with (opt.output / (name + ".log")).open("w", encoding="utf-8") as stream:
            proc = subprocess.Popen(
                cmd, stdout=stream, stderr=subprocess.STDOUT,
                start_new_session=(os.name == "posix"),
                env={**os.environ, "PYTHONFAULTHANDLER": "1"},
            )
            try:
                code = proc.wait(timeout=opt.budget_seconds)
                status = "PASS" if code == 0 else "FAIL"
            except subprocess.TimeoutExpired:
                code, status = None, "TIMEOUT"
            finally:
                processes = cleanup(proc)
        item = {
            "case": name, "status": status, "exit_code": code,
            "elapsed_seconds": round(time.monotonic() - start, 3),
            "source_sha": os.environ.get("GITHUB_SHA"),
            "python": sys.version,
            "command": cmd,
            "processes_at_cleanup": processes,
        }
        reports.append(item)
        (opt.output / "results.json").write_text(json.dumps(reports, indent=2))
        print(name + ": " + status, flush=True)
    return 0 if all(r["status"] == "PASS" for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())

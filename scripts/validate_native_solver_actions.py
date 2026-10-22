#!/usr/bin/env python3
"""Opt-in native solver lifecycle diagnosis; CI results are not fixed-host timings."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fixed_host_resource_repeats import run_bounded_trial  # noqa: E402

from QuPRS.utils import WMC  # noqa: E402
from QuPRS.utils.wmc_solvers import SOLVER_ARGUMENTS  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision(argument: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", argument], cwd=ROOT, text=True
    ).strip()


def active_pid(pid: int) -> bool:
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def positive_check(solver: str, backend: str, binary: Path, folder: Path, *, case: str = "grover4") -> dict:
    """Confirm actual native execve and positive equivalence of an original paper case."""
    trace = folder / "execve.log"
    report_path = folder / "profile.json"
    cmd = [
        "strace", "-f", "-qq", "-e", "trace=execve", "-o", str(trace),
        sys.executable, str(ROOT / "scripts/profile_benchmark_resources.py"),
        "--case", case,
        "--tool-name", solver, "--backend", backend,
        "--walltime-seconds", "75",
        "--solver-timeout-seconds", "45",
        "--memory-limit-mib", "3072",
        "--sample-interval-ms", "50",
        "--output", str(report_path),
    ]
    observation = run_bounded_trial(cmd, 90)
    record = {
        "kind": "positive", "solver": solver, "backend": backend, "case": case,
        "outer_observation": observation,
        "binary_sha256": sha256(binary),
        "native_execve": False, "positive_equivalence": False,
        "numeric_solver_time": False,
        "status": "INCONCLUSIVE",
    }
    if report_path.is_file():
        try:
            profile = json.loads(report_path.read_text())
            verdict = profile.get("verdict", {})
            solver_time = verdict.get("solver_time")
            record["positive_equivalence"] = (
                profile.get("complete") is True
                and profile.get("tool_name") == solver
                and profile.get("backend") == backend
                and verdict.get("accepted_positive") is True
                and verdict.get("tool_name") == solver
                and verdict.get("backend") == backend
            )
            # A fully reduced circuit can be equivalent without launching WMC.
            # Keep semantic success distinct from actual native-tool evidence.
            record["numeric_solver_time"] = (
                isinstance(solver_time, (int, float))
                and not isinstance(solver_time, bool)
                and math.isfinite(solver_time)
                and solver_time >= 0
            )
            record["input_sha256"] = profile.get("input_sha256")
        except (OSError, ValueError, TypeError):
            pass
    if trace.is_file():
        import re
        # Require a successful execve of the exact resolved packaged binary.
        for match in re.finditer(r'execve\("([^"]+)"[^)]*\)\s*=\s*0', trace.read_text()):
            if Path(match.group(1)).resolve() == binary.resolve():
                record["native_execve"] = True
                break
    if (record["native_execve"] and record["positive_equivalence"]
            and record["numeric_solver_time"]
            and observation["exit_code"] == 0
            and not observation["outer_timed_out"]
            and not observation["cleanup_needed"]
            and observation["cleanup_error"] is None):
        record["status"] = "PASS"
    return record


def forced_timeout(solver: str, binary: Path, folder: Path) -> dict:
    """Use the real native executable, blocked on a FIFO, in a detached session.

    A worker launches the native solver and exits only on external cancellation.
    The outer Linux subreaper must kill/reap the detached native executable.
    """
    fifo = folder / "blocked-input.cnf"
    pidfile = folder / "native.pid"
    os.mkfifo(fifo, 0o600)
    witness = {"native_execve": False, "pid": None}
    done = threading.Event()

    def witness_native() -> None:
        until = time.monotonic() + 5
        while not done.is_set() and time.monotonic() < until:
            try:
                pid = int(pidfile.read_text())
                witness["pid"] = pid
                if (active_pid(pid)
                        and Path(psutil.Process(pid).exe()).resolve() == binary.resolve()):
                    witness["native_execve"] = True
                    return
            except (OSError, ValueError, psutil.Error):
                pass
            done.wait(0.01)

    worker = (
        "import pathlib, subprocess, sys, time\n"
        "native = subprocess.Popen([sys.argv[1], sys.argv[2], sys.argv[3]],"
        " stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,"
        " stderr=subprocess.DEVNULL, start_new_session=True)\n"
        "pathlib.Path(sys.argv[4]).write_text(str(native.pid))\n"
        "time.sleep(60)\n"
    )
    monitor = threading.Thread(target=witness_native, daemon=True)
    monitor.start()
    try:
        observation = run_bounded_trial(
            [sys.executable, "-c", worker, str(binary),
             SOLVER_ARGUMENTS[solver][0], str(fifo), str(pidfile)],
            3.0,
        )
    finally:
        done.set()
        monitor.join(timeout=2)
        # FIFO is only a blocking fixture; artifact ZIPs must contain regular files.
        fifo.unlink(missing_ok=True)
    pid = witness["pid"]
    remaining = active_pid(pid) if pid is not None else None
    record = {
        "kind": "forced_timeout", "solver": solver,
        "binary_sha256": sha256(binary),
        "real_solver_execve_observed": witness["native_execve"],
        "native_pid": pid,
        "native_alive_after_cleanup": remaining,
        "outer_observation": observation,
        "status": "INCONCLUSIVE",
    }
    if (witness["native_execve"]
            and observation["outer_timed_out"]
            and observation["cleanup_needed"]
            and observation["cleanup_error"] is None
            and remaining is False):
        record["status"] = "PASS"
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--forced-only", action="store_true")
    mode.add_argument("--positive-only", action="store_true")
    parser.add_argument("--case", choices=("grover4", "qaoa7", "qft16", "vqe4", "graphstate16"), default="grover4")
    parser.add_argument("--backend", choices=("python", "rust", "both"), default="both")
    args = parser.parse_args()

    if sys.platform != "linux":
        parser.error("Native solver lifecycle diagnosis requires Linux")
    if not args.forced_only and not shutil.which("strace"):
        parser.error("strace is required for independent native execve evidence")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("Output directory must be absent or empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "purpose": "native solver correctness and lifecycle only; not fixed-host performance",
        "source_sha": git_revision("HEAD"),
        "tree_sha": git_revision("HEAD^{tree}"),
        "backend_selection": args.backend,
        "cases": [],
    }
    try:
        for solver in ("gpmc", "ganak"):
            with WMC(solver) as executable:
                binary = Path(executable).resolve(strict=True)
                if not os.access(binary, os.X_OK):
                    raise RuntimeError(f"Non-executable solver: {solver}")
                folder = args.output_dir / solver
                folder.mkdir()
                if not args.positive_only:
                    forced = forced_timeout(solver, binary, folder)
                    result["cases"].append(forced)
                    print(json.dumps({k: v for k, v in forced.items()
                                      if k != "outer_observation"}, sort_keys=True), flush=True)
                if not args.forced_only:
                    for backend in ("python", "rust"):
                        if args.backend != "both" and backend != args.backend:
                            continue
                        target = folder / backend
                        target.mkdir()
                        verdict = positive_check(solver, backend, binary, target, case=args.case)
                        result["cases"].append(verdict)
                        print(json.dumps({k: v for k, v in verdict.items()
                                          if k != "outer_observation"},
                                         sort_keys=True), flush=True)
    except Exception as exc:
        result["fatal_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        result["status"] = (
            "PASS" if result["cases"] and all(row["status"] == "PASS"
                                             for row in result["cases"])
            and "fatal_error" not in result else "INCONCLUSIVE"
        )
        (args.output_dir / "validation.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n"
        )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

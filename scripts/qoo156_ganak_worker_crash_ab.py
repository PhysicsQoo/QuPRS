#!/usr/bin/env python3
"""QOO-156 science-only test of *actual* pinned Ganak worker-crash cleanup.

On a real --mode=6 solver process: SIGSTOP Ganak, SIGKILL its immediate
QuPRS worker (NOT the CLI supervisor). Require a failed, non-scientific
CLI verdict and check whether the original solver PID survives.
Any survivor is cleaned by the test harness after the observation.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

import psutil
from QuPRS.utils import WMC

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks/MQTBench/vqe_nativegates_ibm_qiskit_opt0_4.qasm"
PINNED_SHA = "934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alive(pid: int, started: float) -> bool | None:
    try:
        p = psutil.Process(pid)
        return abs(p.create_time() - started) <= 0.1 and p.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return False
    except psutil.AccessDenied:
        return None  # unverifiable, never PASS


def run_case(cli: Path, solver: Path, folder: Path, label: str) -> dict:
    left = folder / "left.qasm"
    right = folder / "right.qasm"
    left.write_bytes(FIXTURE.read_bytes())
    right.write_bytes(FIXTURE.read_bytes().rstrip() + b"\nx q[0];\n")
    cmd = [
        str(cli), str(left), str(right), "--method", "wmc-only",
        "--tool", "ganak", "--strategy", "proportional",
        "--timeout", "10", "--quiet",
    ]
    env = os.environ.copy()
    env["QUPRS_GANAK_PATH"] = str(solver)
    env.pop("LD_PRELOAD", None)
    parent = subprocess.Popen(
        cmd, cwd=folder, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    ganak_pid: int | None = None
    ganak_birth: float | None = None
    worker_pid: int | None = None
    ganak_argv = None
    ganak_stopped = False
    worker_killed = False
    output = stderr = ""
    observed_active: bool | None = None
    began = time.monotonic()

    try:
        while time.monotonic() < began + 8:
            try:
                descendants = psutil.Process(parent.pid).children(recursive=True)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                break
            for p in descendants:
                try:
                    argv = p.cmdline()
                    if "--mode=6" not in argv or Path(p.exe()).resolve() != solver:
                        continue
                    if p.ppid() == parent.pid:
                        continue  # ensure genuine supervised child/worker
                    ganak_pid, ganak_birth = p.pid, p.create_time()
                    worker_pid = p.ppid()
                    # Only stop the exact pinned, live mode=6 process.
                    os.kill(ganak_pid, signal.SIGSTOP)
                    for _ in range(100):
                        try:
                            if psutil.Process(ganak_pid).status() == psutil.STATUS_STOPPED:
                                ganak_stopped = True
                                break
                        except (psutil.Error, ProcessLookupError):
                            break
                        time.sleep(0.002)
                    if not ganak_stopped:
                        break
                    ganak_argv = argv
                    # Destroy the worker while its real solver remains
                    # stopped. This isolates the subreaper crash-race guard.
                    os.kill(worker_pid, signal.SIGKILL)
                    worker_killed = True
                    break
                except (psutil.Error, ProcessLookupError, PermissionError):
                    continue
            if worker_killed:
                break
            if parent.poll() is not None:
                break
            time.sleep(0.001)

        try:
            output, stderr = parent.communicate(timeout=13)
        except subprocess.TimeoutExpired:
            os.killpg(parent.pid, signal.SIGKILL)
            output, stderr = parent.communicate(timeout=3)

        if ganak_pid is not None and ganak_birth is not None:
            for _ in range(100):
                observed_active = alive(ganak_pid, ganak_birth)
                if observed_active is False:
                    break
                time.sleep(0.01)
    finally:
        if parent.poll() is None:
            os.killpg(parent.pid, signal.SIGKILL)
            parent.wait(timeout=3)

    # Record outcome before external test-only cleanup; do not mask leaks.
    record = {
        "variant": label, "solver_sha256": sha(solver),
        "source_sha256": sha(FIXTURE), "cli_sha256": sha(cli),
        "solver_pid": ganak_pid, "solver_birth": ganak_birth,
        "worker_pid": worker_pid, "real_mode6_argv": ganak_argv,
        "ganak_was_stopped": ganak_stopped,
        "worker_was_sigkilled": worker_killed,
        "cli_exit_code": parent.returncode,
        "cli_stdout": output[-1000:], "cli_stderr": stderr[-1000:],
        "solver_alive_after_cli": observed_active,
        "elapsed_s": round(time.monotonic() - began, 3),
    }
    record["classification"] = (
        "CRASH_CLEANUP_PASS"
        if ganak_stopped and worker_killed
        and parent.returncode not in (None, 0)
        and observed_active is False and not output.strip().lower().startswith(
            ("equivalent", "not_equivalent", "unknown")
        )
        else "NOT_ADMITTED"
    )
    if observed_active is True and ganak_pid is not None and ganak_birth is not None:
        try:
            if alive(ganak_pid, ganak_birth) is True:
                os.kill(ganak_pid, signal.SIGKILL)
        except (ProcessLookupError, psutil.Error):
            pass
    return record


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pre-cli", type=Path, required=True)
    p.add_argument("--head-cli", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    args = p.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack, tempfile.TemporaryDirectory(prefix="qoo156-ganak-crash-") as temp:
        ganak = Path(stack.enter_context(WMC("ganak"))).resolve(strict=True)
        if sha(ganak) != PINNED_SHA:
            raise RuntimeError("Ganak is not the pinned upstream Linux ELF")
        work = Path(temp)
        results = []
        for variant, path in (("pre", args.pre_cli), ("head", args.head_cli)):
            r = run_case(path.resolve(strict=True), ganak, work, variant)
            results.append(r)
            print("QOO156_GANAK_WORKER_CRASH " + json.dumps({
                "variant": variant, "classification": r["classification"],
                "solver_alive": r["solver_alive_after_cli"],
                "worker_killed": r["worker_was_sigkilled"],
                "elapsed_s": r["elapsed_s"],
            }, sort_keys=True), flush=True)
        pre_ok = results[0]["classification"] == "CRASH_CLEANUP_PASS"
        head_ok = results[1]["classification"] == "CRASH_CLEANUP_PASS"
        if pre_ok and head_ok:
            classification = "BOTH_PASS_NO_INCREMENTAL_BENEFIT_OBSERVED"
        elif not pre_ok and head_ok and results[0]["ganak_was_stopped"] and results[0]["worker_was_sigkilled"]:
            classification = "HEAD_ONLY_PASS_POTENTIAL_HARDENING_BENEFIT"
        else:
            classification = "NOT_ADMITTED"
        summary = {"runs": results, "classification": classification}
        (args.evidence / "ganak-worker-crash-ab.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n"
        )
        print("QOO156_WORKER_CRASH_AB=" + summary["classification"], flush=True)
        return 0 if classification != "NOT_ADMITTED" else 2


if __name__ == "__main__":
    sys.exit(main())

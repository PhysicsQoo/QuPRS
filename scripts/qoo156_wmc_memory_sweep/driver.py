#!/usr/bin/env python3
"""QOO-156 bounded physical memory sweep of authentic release Rust CLI + WMC.

Records Linux cgroup-v2 memory.peak and memory.events along with genuine
solver PID/ELF/argv, without modifying solver source or instrumenting it.
A cgroup OOM coincident with a solver invocation is NOT proof which PID
the kernel selected as its OOM victim.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import psutil

SOLVER = os.environ["QOO156_SOLVER"]
CASE = os.environ["QOO156_CASE"]
LIMIT = int(os.environ["QOO156_LIMIT_MIB"])
EXPECTED_SHA = {
    "gpmc": "507919b9af456645b55dc73e7d4db4a56b9293a0fa3ba99f5f8a0986826ef4b1",
    "ganak": "934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd",
}
CASES = {"vqe4", "graphstate16", "qft16"}
S = Path("/sys/fs/cgroup")
SOLVER_BINARY = Path("/opt") / SOLVER
CLI = Path("/opt/QuPRS_cli")
SOURCE = Path("/opt/case.qasm")
SCIENCE = {"equivalent", "equivalent*", "not_equivalent",
           "Equivalent", "EquivalentUpToGlobalPhase", "NotEquivalent"}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for buf in iter(lambda: stream.read(1048576), b""):
            h.update(buf)
    return h.hexdigest()


def events():
    return {k: int(v) for k, v in (
        line.split() for line in (S / "memory.events").read_text().splitlines()
    )}


def solver_process(root):
    try:
        children = psutil.Process(root).children(recursive=True)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return None
    for child in children:
        try:
            if Path(child.exe()).resolve() != SOLVER_BINARY.resolve():
                continue
            argv = child.cmdline()
            if SOLVER == "ganak" and "--mode=6" not in argv:
                continue
            if SOLVER == "gpmc" and "-mode=1" not in argv:
                continue
            return child, argv
        except (psutil.Error, ProcessLookupError, PermissionError):
            continue
    return None


def solver_still_alive(pid, born):
    try:
        p = psutil.Process(pid)
        return abs(p.create_time() - born) < .1 and p.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return False
    except psutil.AccessDenied:
        return None


def main():
    if SOLVER not in EXPECTED_SHA or CASE not in CASES or LIMIT not in (64, 128, 256, 512, 1024):
        raise ValueError("Case, solver or memory cap is not on the bounded manifest")
    solver_sha = sha(SOLVER_BINARY)
    if solver_sha != EXPECTED_SHA[SOLVER]:
        raise ValueError("Pinned solver SHA mismatch")
    cap = (S / "memory.max").read_text().strip()
    actual_cap = int(cap) if cap != "max" else None
    if actual_cap != LIMIT * 1048576:
        raise RuntimeError("Kernel cgroup limit not equal to requested Docker cap")

    qasm = SOURCE.read_bytes()
    left = Path("/tmp/left.qasm")
    right = Path("/tmp/right.qasm")
    left.write_bytes(qasm)
    right.write_bytes(qasm.rstrip() + b"\nx q[0];\n")
    env = dict(os.environ, QUPRS_GPMC_PATH="/opt/gpmc", QUPRS_GANAK_PATH="/opt/ganak")
    env.pop("LD_PRELOAD", None)
    before = events()
    start = time.monotonic()
    cli = subprocess.Popen(
        [str(CLI), str(left), str(right), "--method", "wmc-only",
         "--strategy", "proportional", "--tool", SOLVER,
         "--timeout", "10", "--quiet"],
        cwd="/tmp", env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,
    )

    witnessed = None
    stopped = False
    out = err = ""
    forced_harness_kill = False
    try:
        # Only once the genuine executable and argv are observed do we
        # briefly SIGSTOP/SIGCONT; do not substitute or wrap any solver.
        end = start + 12
        while time.monotonic() < end:
            found = solver_process(cli.pid)
            if found is not None and witnessed is None:
                proc, argv = found
                try:
                    pid, birth = proc.pid, proc.create_time()
                    os.kill(pid, signal.SIGSTOP)
                    for _ in range(50):
                        try:
                            if psutil.Process(pid).status() == psutil.STATUS_STOPPED:
                                stopped = True
                                break
                        except psutil.Error:
                            break
                        time.sleep(.001)
                    if stopped:
                        witnessed = {
                            "pid": pid, "birth_time": birth, "ppid": proc.ppid(),
                            "argv": argv, "elf_sha256": solver_sha,
                        }
                        os.kill(pid, signal.SIGCONT)
                except (psutil.Error, ProcessLookupError, PermissionError):
                    pass
            if cli.poll() is not None:
                break
            time.sleep(.001)
        try:
            out, err = cli.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            forced_harness_kill = True
            os.killpg(cli.pid, signal.SIGKILL)
            out, err = cli.communicate(timeout=5)
    finally:
        if cli.poll() is None:
            forced_harness_kill = True
            os.killpg(cli.pid, signal.SIGKILL)
            cli.wait(timeout=5)

    after = events()
    peak = int((S / "memory.peak").read_text().strip())
    oom_delta = after.get("oom_kill", 0) - before.get("oom_kill", 0)
    verdict = out.strip()
    no_partial = verdict == "" or verdict == "Timeout"
    actual_solver_gone = (solver_still_alive(
        witnessed["pid"], witnessed["birth_time"]
    ) if witnessed else None)
    if (witnessed and stopped and not forced_harness_kill
            and oom_delta == 0 and cli.returncode == 0 and verdict in SCIENCE):
        result = "COMPLETE_WITHIN_CAP"
    elif (witnessed and stopped and not forced_harness_kill
            and oom_delta > 0 and cli.returncode != 0 and no_partial
            and actual_solver_gone is False):
        result = "CONTAINER_OOM_AFTER_SOLVER_STARTED_NO_VERDICT"
    elif (witnessed and stopped and not forced_harness_kill
            and oom_delta == 0 and cli.returncode == 124 and verdict == "Timeout"
            and actual_solver_gone is False):
        result = "SOLVER_TIMEOUT_WITHIN_CAP"
    else:
        result = "NOT_ADMITTED"

    record = {
        "classification": result, "solver": SOLVER, "case": CASE,
        "limit_mib": LIMIT, "kernel_memory_max_bytes": actual_cap,
        "kernel_memory_peak_bytes": peak, "memory_peak_mib": round(peak / 1048576, 3),
        "kernel_oom_kill_delta": oom_delta,
        "solver_sha256": solver_sha, "cli_sha256": sha(CLI),
        "qasm_source_sha256": sha(SOURCE),
        "solver_process": witnessed, "solver_stop_confirmed": stopped,
        "solver_alive_after_cli": actual_solver_gone,
        "cli_exit_code": cli.returncode, "verdict": verdict if verdict in SCIENCE else None,
        "stdout_tail": out[-350:], "stderr_tail": err[-900:],
        "harness_forced_kill": forced_harness_kill,
        "duration_observational_only_seconds": round(time.monotonic() - start, 3),
        "note": "Docker external physical limit; internal --max-memory-mib NOT tested. "
                "Kernel OOM event does not establish which process was selected as OOM victim.",
    }
    print("QOO156_WMC_PEAK_JSON=" + json.dumps(record, sort_keys=True), flush=True)
    print(f"QOO156_WMC_PEAK_{SOLVER}_{CASE}_{LIMIT}={result}", flush=True)
    return 0 if result != "NOT_ADMITTED" else 2


if __name__ == "__main__":
    sys.exit(main())

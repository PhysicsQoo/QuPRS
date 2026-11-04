#!/usr/bin/env python3
"""Authentic release GPMC/Ganak under QuPRS CLI's OWN nested memory.max.

This uses test-only privileged cgroup bootstrap (root *harness*) to delegate
an empty parent to a NONROOT CLI, exercising a real WMC solver descendant
under the CLI-created child cgroup. Scientific verdict, kernel OOM and solver
PID/ELF/argv are checked separately. No performance timing certificate.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import psutil

from pilot import delegated_parent, move_and_drop_to_unprivileged, read_events_fd, UID, MIB

TESTS = (
    ("gpmc", "qft16", 256, 32, "-mode=1"),
    ("ganak", "vqe4", 256, 64, "--mode=6"),
)
BINARY_SHA = {
    "gpmc": "507919b9af456645b55dc73e7d4db4a56b9293a0fa3ba99f5f8a0986826ef4b1",
    "ganak": "934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd",
}
PREFIX = Path("/opt")


def sha(file):
    h = hashlib.sha256()
    with open(file, "rb") as stream:
        for buf in iter(lambda: stream.read(1048576), b""):
            h.update(buf)
    return h.hexdigest()


def solver_identity(root_pid, executable, expected_mode):
    try:
        descendants = psutil.Process(root_pid).children(recursive=True)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return None
    for proc in descendants:
        try:
            if Path(proc.exe()).resolve() != executable.resolve():
                continue
            argv = proc.cmdline()
            if expected_mode not in argv:
                continue
            return dict(pid=proc.pid, birth=proc.create_time(),
                        argv=argv, elf_sha256=sha(executable))
        except (psutil.Error, PermissionError, ProcessLookupError):
            continue
    return None


def pid_dead(pid, birth):
    try:
        proc = psutil.Process(pid)
        return abs(proc.create_time() - birth) > 0.1 or proc.status() == psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return True
    except psutil.AccessDenied:
        return False


def run_case(delegated, solver, circuit, limit, mode, high_cap):
    label = f"{solver}-{circuit}-{'high' if high_cap else 'low'}"
    raw = (PREFIX / f"{circuit}.qasm").read_bytes()
    left = Path("/tmp") / f"{label}-left.qasm"
    right = Path("/tmp") / f"{label}-right.qasm"
    left.write_bytes(raw)
    right.write_bytes(raw.rstrip() + b"\nx q[0];\n")
    os.chmod(left, 0o644)
    os.chmod(right, 0o644)
    env = dict(os.environ, QUPRS_GPMC_PATH="/opt/gpmc", QUPRS_GANAK_PATH="/opt/ganak")
    env.pop("QUPRS_CLI_TEST_ALLOC_MIB", None)
    # The exact release solver binary and its full arguments are checked,
    # not a stub/fixture or a simulated subprocess.
    expected_sha = BINARY_SHA[solver]
    executable = PREFIX / solver
    if sha(executable) != expected_sha:
        raise RuntimeError(f"{label}: mismatched real Solver SHA")
    cmd = [
        "/opt/QuPRS_cli", str(left), str(right), "--quiet",
        "--method", "wmc-only", "--strategy", "proportional",
        "--tool", solver, "--timeout", "12",
        "--max-memory-mib", str(limit),
    ]
    child = subprocess.Popen(
        cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, preexec_fn=lambda: move_and_drop_to_unprivileged(delegated),
    )
    memory_group = delegated / f"quprs-cli-{child.pid}"
    event_fd = None
    max_bytes = None
    last_events = {}
    peak_bytes = 0
    witness = None
    deadline = time.monotonic() + 18
    try:
        while time.monotonic() < deadline:
            if event_fd is None:
                try:
                    max_bytes = int((memory_group / "memory.max").read_text().strip())
                    event_fd = os.open(str(memory_group / "memory.events"), os.O_RDONLY)
                except (OSError, ValueError):
                    pass
            if event_fd is not None:
                try:
                    last_events = read_events_fd(event_fd)
                    peak_bytes = max(
                        peak_bytes, int((memory_group / "memory.peak").read_text()))
                except (OSError, ValueError):
                    pass
            if witness is None:
                witness = solver_identity(child.pid, executable, mode)
            if child.poll() is not None:
                break
            time.sleep(.001)
        try:
            stdout, stderr = child.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate(timeout=3)
            raise RuntimeError(f"{label}: harness killed an unresponsive CLI")
        if event_fd is not None:
            try:
                last_events = read_events_fd(event_fd)
            except OSError:
                pass
        gone = pid_dead(witness["pid"], witness["birth"]) if witness else None
        value = dict(
            case=label, solver=solver, qasm_sha256=sha(PREFIX / f"{circuit}.qasm"),
            exact_solver_elf_sha256=expected_sha, cli_sha256=sha("/opt/QuPRS_cli"),
            cap_mib=limit, readback_max_bytes=max_bytes,
            cgroup_oom_kill=last_events.get("oom_kill"), peak_bytes=peak_bytes,
            solver_process=witness, solver_pid_gone=gone, cli_uid=UID,
            cli_exit_code=child.returncode, stdout=stdout[-250:],
            stderr=stderr[-800:], harness_killed_cli=False,
        )
        acceptable = (
            max_bytes == limit * MIB and witness is not None and
            witness["elf_sha256"] == expected_sha and
            witness["argv"][0].endswith("/" + solver) and
            mode in witness["argv"] and gone is True
        )
        if high_cap:
            acceptable &= (child.returncode == 0 and
                           stdout.strip() == "not_equivalent" and
                           last_events.get("oom_kill", 0) == 0)
        else:
            acceptable &= (child.returncode == 125 and
                           stdout == "" and
                           "MemoryLimitExceeded" in stderr and
                           last_events.get("oom_kill", 0) >= 1)
        value["admitted"] = bool(acceptable)
        print("QOO156_INTERNAL_REAL_WMC_JSON=" +
              json.dumps(value, sort_keys=True), flush=True)
        return value
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=3)
        if event_fd is not None:
            os.close(event_fd)


def main():
    delegated = delegated_parent()
    results = []
    try:
        for solver, circuit, high, low, mode in TESTS:
            for high_cap, limit in ((True, high), (False, low)):
                item = run_case(delegated, solver, circuit, limit, mode, high_cap)
                results.append(item)
        print("QOO156_INTERNAL_REAL_WMC_MANIFEST=" +
              json.dumps(results, sort_keys=True), flush=True)
        if not all(item["admitted"] for item in results):
            raise SystemExit("QOO156_INTERNAL_REAL_WMC=NOT_ADMITTED")
        print("QOO156_INTERNAL_REAL_WMC=PASS", flush=True)
    finally:
        try:
            (delegated / "supervisor").rmdir()
            delegated.rmdir()
        except OSError as exc:
            print(f"QOO156_INTERNAL_REAL_WMC_CGROUP_CLEANUP_PENDING={exc}",
                  file=sys.stderr)


if __name__ == "__main__":
    main()

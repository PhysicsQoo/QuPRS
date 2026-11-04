#!/usr/bin/env python3
"""Ganak 2.8.0 real PID + in-CLI-cgroup forced OOM, source-pinned pilot.

Separate from the natural 64/70 MiB cap attempt: the latter correctly
returns typed OOM but cannot certify the Ganak PID prior to worker death.
Here, the *requested* 256 MiB cap stays unchanged. After genuine Ganak is
observed/stopped, a test-only pressure process is admitted to that very same
CLI-created worker cgroup and touches physical pages. No solver patching.
This is deliberate adversarial OOM, NOT Ganak's natural memory requirement.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from pilot import delegated_parent, move_and_drop_to_unprivileged, read_events_fd, UID, MIB
from release_solver import run_case, solver_identity, pid_dead, sha, BINARY_SHA

CAP = 256
BIN = Path("/opt/ganak")
FIXTURE = Path("/opt/vqe4.qasm")
PRESSURE = """
import time
pages=[]
for j in range(320):
    item=bytearray(1048576)
    for i in range(0,len(item),4096):
        item[i]=1
    pages.append(item)
    time.sleep(.002)
print("PRESSURE_FINISHED",flush=True)
time.sleep(1)
"""


def join_worker_group_and_drop(group):
    fd = os.open(str(group / "cgroup.procs"), os.O_WRONLY)
    try:
        v = str(os.getpid()).encode("ascii")
        if os.write(fd, v) != len(v):
            os._exit(117)
    finally:
        os.close(fd)
    os.setgroups([])
    os.setgid(UID)
    os.setuid(UID)


def adversarial_case(delegate):
    raw = FIXTURE.read_bytes()
    left = Path("/tmp") / "ganak-pressure-left.qasm"
    right = Path("/tmp") / "ganak-pressure-right.qasm"
    left.write_bytes(raw)
    right.write_bytes(raw.rstrip() + b"\nx q[0];\n")
    os.chmod(left, 0o644)
    os.chmod(right, 0o644)
    if sha(BIN) != BINARY_SHA["ganak"]:
        raise RuntimeError("pinned Ganak ELF SHA mismatch")

    env = dict(os.environ, QUPRS_GANAK_PATH="/opt/ganak",
               QUPRS_GPMC_PATH="/opt/gpmc")
    env.pop("QUPRS_CLI_TEST_ALLOC_MIB", None)
    cli = subprocess.Popen(
        ["/opt/QuPRS_cli", str(left), str(right), "--quiet",
         "--method", "wmc-only", "--strategy", "proportional",
         "--tool", "ganak", "--max-memory-mib", str(CAP),
         "--timeout", "14"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
        preexec_fn=lambda: move_and_drop_to_unprivileged(delegate),
    )
    worker_group = delegate / f"quprs-cli-{cli.pid}"
    memfd = None
    initial_events = None
    latest_events = None
    readback = None
    oom_group = None
    solver = None
    stopped = False
    resumed = False
    pressured = False
    pressure = None
    pressure_harness_kill = False
    peak_bytes = 0
    t0 = time.monotonic()
    try:
        while time.monotonic() - t0 < 17:
            if memfd is None:
                try:
                    readback = int((worker_group / "memory.max").read_text().strip())
                    oom_group = (worker_group / "memory.oom.group").read_text().strip()
                    memfd = os.open(str(worker_group / "memory.events"), os.O_RDONLY)
                    initial_events = read_events_fd(memfd)
                except (OSError, ValueError):
                    pass
            if memfd is not None:
                try:
                    latest_events = read_events_fd(memfd)
                    peak_bytes = max(
                        peak_bytes, int((worker_group / "memory.peak").read_text().strip()))
                except (OSError, ValueError):
                    pass
            if solver is None:
                solver = solver_identity(cli.pid, BIN, "--mode=6")
                if solver is not None:
                    # Observe the immutable ELF+argv+PID BEFORE adding pressure.
                    os.kill(solver["pid"], signal.SIGSTOP)
                    try:
                        import psutil
                        for _ in range(100):
                            if psutil.Process(solver["pid"]).status() == psutil.STATUS_STOPPED:
                                stopped = True
                                break
                            time.sleep(.001)
                    except (psutil.Error, ProcessLookupError):
                        stopped = False
                    if not stopped:
                        raise RuntimeError("real Ganak PID not demonstrably stopped")
                    if readback != CAP * MIB or oom_group != "1":
                        raise RuntimeError("wrong live worker cgroup memory.max/oom.group")
                    print("QOO156_REAL_GANAK_PREPRESSURE=" +
                          json.dumps(dict(solver=solver, memory_max_bytes=readback,
                                          memory_oom_group=oom_group), sort_keys=True),
                          flush=True)
                    # Pressure is admitted into the SAME native Rust worker
                    # group, after observing the true Ganak process.
                    pressure = subprocess.Popen(
                        [sys.executable, "-u", "-c", PRESSURE],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True,
                        preexec_fn=lambda: join_worker_group_and_drop(worker_group),
                    )
                    pressured = True
                    # Keep the authentic Ganak PID alive in SIGSTOP until
                    # the kernel OOMs this entire cgroup. Resuming it now
                    # would let fast VQE4 finish before bounded pressure
                    # reaches memory.max, invalidating victim attribution.
                    # A NOT_ADMITTED cleanup still sends SIGCONT in finally.
            if cli.poll() is not None:
                break
            time.sleep(.001)
        try:
            out, err = cli.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            cli.kill()
            out, err = cli.communicate(timeout=3)
            raise RuntimeError("unresponsive CLI; harness kill NOT an OOM certificate")
        if memfd is not None:
            try:
                latest_events = read_events_fd(memfd)
            except OSError:
                pass
        result = dict(
            classification="NOT_ADMITTED",
            cli_sha256=sha("/opt/QuPRS_cli"), ganak_sha256=sha(BIN),
            qasm_sha256=sha(FIXTURE), real_ganak=solver,
            real_ganak_stopped=stopped, real_ganak_resumed=resumed,
            test_pressure_in_same_worker_group=pressured,
            memory_max_readback_bytes=readback, memory_oom_group=oom_group,
            worker_peak_bytes=peak_bytes,
            kernel_oom_kill_delta=(
                latest_events.get("oom_kill", 0) - initial_events.get("oom_kill", 0)
                if latest_events is not None and initial_events is not None else None),
            ganak_pid_gone=pid_dead(solver["pid"],solver["birth"]) if solver else None,
            cli_exit_code=cli.returncode, cli_stdout=out,
            cli_stderr_tail=err[-500:], cli_uid=UID,
        )
        positive = (
            solver is not None and stopped and pressured
            and readback == CAP * MIB and oom_group == "1"
            and result["kernel_oom_kill_delta"] is not None
            and result["kernel_oom_kill_delta"] >= 1
            and result["ganak_pid_gone"] is True
            and cli.returncode == 125 and out == ""
            and "MemoryLimitExceeded" in err
        )
        if positive:
            result["classification"] = "REAL_GANAK_INTERNAL_CGROUP_OOM_AND_NO_FALSE_VERDICT"
        print("QOO156_INTERNAL_REAL_GANAK_PRESSURE_JSON=" +
              json.dumps(result,sort_keys=True),flush=True)
        return result
    finally:
        if pressure is not None:
            if pressure.poll() is None:
                pressure_harness_kill = True
                pressure.kill()
            pressure.communicate(timeout=4)
        if solver is not None and not resumed:
            try:
                os.kill(solver["pid"], signal.SIGCONT)
            except ProcessLookupError:
                pass
        if cli.poll() is None:
            cli.kill()
            cli.wait(timeout=4)
        if memfd is not None:
            os.close(memfd)
        if pressure_harness_kill:
            print("QOO156_PRESSURE_HELPER_CLEANUP_ONLY=TRUE",flush=True)


def main():
    delegated=delegated_parent()
    try:
        high=run_case(delegated,"ganak","vqe4",CAP,"--mode=6",True)
        forced=adversarial_case(delegated)
        valid=(high.get("admitted") is True and forced["classification"] ==
               "REAL_GANAK_INTERNAL_CGROUP_OOM_AND_NO_FALSE_VERDICT")
        print("QOO156_INTERNAL_REAL_GANAK_PRESSURE=PASS" if valid
              else "QOO156_INTERNAL_REAL_GANAK_PRESSURE=NOT_ADMITTED",flush=True)
        if not valid:
            raise SystemExit(2)
    finally:
        try:
            (delegated/"supervisor").rmdir()
            delegated.rmdir()
        except OSError as exc:
            print(f"QOO156_GANAK_CGROUP_CLEANUP_PENDING={exc}",file=sys.stderr)


if __name__=="__main__":
    main()

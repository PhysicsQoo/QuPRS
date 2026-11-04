#!/usr/bin/env python3
"""QOO-156: bounded real WMC solver inside a Docker daemon memory envelope.

This is NOT a certification of QuPRS --max-memory-mib. The container parent
observes the real solver PID/executable and cgroup memory.events. It never
patches solver binaries or re-labels a generic SIGKILL as internal CLI OOM.
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

METHOD = "wmc-only"
SOLVER = os.environ["QOO156_SOLVER"]
LIMIT_MIB = int(os.environ["QOO156_LIMIT_MIB"])
CLI = Path("/opt/QuPRS_cli")
REAL_SOLVER = Path("/opt/" + SOLVER)
SOURCE = Path("/opt/vqe4.qasm")
EXPECTED_GANAK_SHA = "934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def events():
    f = Path("/sys/fs/cgroup/memory.events")
    return {k: int(v) for k, v in (line.split() for line in f.read_text().splitlines())}


def live_solver(cli_pid):
    try:
        descendants = psutil.Process(cli_pid).children(recursive=True)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return None
    for proc in descendants:
        try:
            if Path(proc.exe()).resolve() != REAL_SOLVER.resolve():
                continue
            args = proc.cmdline()
            if SOLVER == "ganak" and "--mode=6" not in args:
                continue
            return proc, args
        except (psutil.Error, ProcessLookupError, PermissionError):
            continue
    return None


def main():
    if SOLVER not in ("ganak", "gpmc") or LIMIT_MIB not in (256, 1024):
        raise ValueError("bounded pilot only accepts gpmc/ganak and 256/1024 MiB")
    expected_bytes = LIMIT_MIB * 1024 * 1024
    max_text = Path("/sys/fs/cgroup/memory.max").read_text().strip()
    actual_bytes = int(max_text) if max_text != "max" else None
    source = SOURCE.read_bytes()
    left = Path("/tmp/left.qasm")
    right = Path("/tmp/right.qasm")
    left.write_bytes(source)
    right.write_bytes(source.rstrip() + b"\nx q[0];\n")

    solver_sha = sha(REAL_SOLVER)
    if SOLVER == "ganak" and solver_sha != EXPECTED_GANAK_SHA:
        raise RuntimeError("unexpected Ganak 2.8.0 release SHA256")
    env = os.environ.copy()
    env.pop("LD_PRELOAD", None)
    env["QUPRS_GANAK_PATH"] = "/opt/ganak"
    env["QUPRS_GPMC_PATH"] = "/opt/gpmc"

    args = [
        str(CLI), str(left), str(right), "--method", METHOD,
        "--strategy", "proportional", "--tool", SOLVER,
        "--timeout", "16", "--quiet",
    ]
    before = events()
    cli = subprocess.Popen(
        args, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd="/tmp", start_new_session=True,
    )
    observed = None
    elapsed_start = time.monotonic()
    out = err = ""
    try:
        # We need proof that the authentic solver did run, not merely CLI
        # returning a cached/simplified scientific verdict without WMC.
        while time.monotonic() - elapsed_start < 15:
            found = live_solver(cli.pid)
            if found is not None:
                proc, argv = found
                try:
                    ppid, born = proc.ppid(), proc.create_time()
                    pid = proc.pid
                    os.kill(pid, signal.SIGSTOP)
                    for _ in range(100):
                        try:
                            if psutil.Process(pid).status() == psutil.STATUS_STOPPED:
                                observed = {
                                    "pid": pid, "ppid": ppid, "born": born,
                                    "argv": argv, "elf_sha256": solver_sha,
                                    "stopped": True,
                                }
                                break
                        except psutil.Error:
                            break
                        time.sleep(.001)
                    if observed is not None:
                        # Allow the actual solver to complete an authentic
                        # calculation, after proving live PID+binary identity.
                        os.kill(pid, signal.SIGCONT)
                        break
                except (psutil.Error, ProcessLookupError, PermissionError):
                    pass
            if cli.poll() is not None:
                break
            time.sleep(.001)
        try:
            out, err = cli.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(cli.pid, signal.SIGKILL)
            out, err = cli.communicate(timeout=5)
    finally:
        if cli.poll() is None:
            os.killpg(cli.pid, signal.SIGKILL)
            cli.wait(timeout=5)

    after = events()
    oom_delta = after.get("oom_kill", 0) - before.get("oom_kill", 0)
    verdict = out.strip()
    science_verdicts = {
        "equivalent", "equivalent*", "not_equivalent",
        "Equivalent", "EquivalentUpToGlobalPhase", "NotEquivalent",
    }
    verdict_valid = verdict in science_verdicts
    no_partial_verdict = not verdict_valid and not verdict
    if oom_delta == 0:
        # Stronger than merely "no crash": authentic solver is observed
        # and the complete scientific verdict must be returned.
        passed = bool(
            actual_bytes == expected_bytes and observed is not None
            and cli.returncode == 0 and verdict_valid
        )
        classification = "REAL_WMC_COMPLETE_PASS" if passed else "NOT_ADMITTED"
    else:
        # An externally OOM-killed process may cause the CLI to return 125,
        # but only cgroup evidence identifies it as memory-related.
        passed = bool(
            actual_bytes == expected_bytes and observed is not None
            and cli.returncode != 0 and no_partial_verdict
        )
        classification = "REAL_WMC_EXTERNAL_OOM_SAFE" if passed else "NOT_ADMITTED"

    record = {
        "case": "MQTBench_vqe4_with_extra_X",
        "cli_sha256": sha(CLI),
        "qasm_source_sha256": sha(SOURCE),
        "solver": SOLVER,
        "solver_sha256": solver_sha,
        "solver_seen": observed,
        "requested_limit_mib": LIMIT_MIB,
        "kernel_memory_max_bytes": actual_bytes,
        "kernel_oom_kill_delta": oom_delta,
        "cli_return_code": cli.returncode,
        "complete_science_verdict": verdict if verdict_valid else None,
        "no_partial_verdict": no_partial_verdict,
        "stdout_tail": out[-1000:],
        "stderr_tail": err[-1400:],
        "classification": classification,
        "cli_internal_memory_guard": "NOT_TESTED",
    }
    print("QOO156_REAL_WMC_DOCKER_JSON=" + json.dumps(record, sort_keys=True), flush=True)
    print(f"QOO156_REAL_WMC_DOCKER_{SOLVER}_{LIMIT_MIB}={classification}", flush=True)
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""True Linux OOM selection of authentic GPMC/Ganak solver, test-only pressure.

The real solver binary/argv is verified, SIGSTOP'ed and its oom_score_adj
increased before a separate bounded sibling allocates memory inside the
same Docker cgroup. This creates an *adversarial* kernel OOM, not evidence
of solver's natural working-set requirement. No solver code is modified.
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
CAP_MIB = 256
ROOT = Path("/sys/fs/cgroup")
CLI = Path("/opt/QuPRS_cli")
BIN = Path("/opt") / SOLVER
QASM = Path("/opt/vqe4.qasm")
EXPECTED = {
    "gpmc": "507919b9af456645b55dc73e7d4db4a56b9293a0fa3ba99f5f8a0986826ef4b1",
    "ganak": "934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd",
}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def memory_events():
    return {k: int(v) for k, v in (
        line.split() for line in (ROOT / "memory.events").read_text().splitlines()
    )}


def running(pid, born):
    try:
        p = psutil.Process(pid)
        return abs(p.create_time() - born) < .1 and p.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return False
    except psutil.AccessDenied:
        return None


def find_solver(parent_pid):
    try:
        children = psutil.Process(parent_pid).children(recursive=True)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return None
    for proc in children:
        try:
            if Path(proc.exe()).resolve() != BIN.resolve():
                continue
            args = proc.cmdline()
            if SOLVER == "ganak" and "--mode=6" not in args:
                continue
            if SOLVER == "gpmc" and "-mode=1" not in args:
                continue
            return proc, args
        except (psutil.Error, ProcessLookupError, PermissionError):
            continue
    return None


def main():
    if SOLVER not in EXPECTED:
        raise ValueError("only pinned GPMC and Ganak are supported")
    fingerprint = sha(BIN)
    if fingerprint != EXPECTED[SOLVER]:
        raise RuntimeError("solver ELF hash differs from pinned release")
    cap_text = (ROOT / "memory.max").read_text().strip()
    if cap_text != str(CAP_MIB * 1048576):
        raise RuntimeError("exact 256 MiB Docker memory.max was not installed")
    raw = QASM.read_bytes()
    a = Path("/tmp/left.qasm")
    b = Path("/tmp/right.qasm")
    a.write_bytes(raw)
    b.write_bytes(raw.rstrip() + b"\nx q[0];\n")
    env = dict(os.environ, QUPRS_GANAK_PATH="/opt/ganak", QUPRS_GPMC_PATH="/opt/gpmc")
    env.pop("LD_PRELOAD", None)
    cmd = [str(CLI), str(a), str(b), "--method", "wmc-only",
           "--tool", SOLVER, "--strategy", "proportional",
           "--timeout", "12", "--quiet"]
    before = memory_events()
    t0 = time.monotonic()
    cli = subprocess.Popen(
        cmd, env=env, cwd="/tmp",
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,
    )
    target = None
    score_adjustment = None
    stopped = False
    pressure = None
    pressure_exit = None
    observed_cli_exit = None
    out = err = ""
    harness_killed_solver = False
    try:
        while time.monotonic() - t0 < 7:
            solver = find_solver(cli.pid)
            if solver is not None:
                proc, args = solver
                pid = proc.pid
                born = proc.create_time()
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
                    target = {
                        "pid": pid, "birth": born, "ppid": proc.ppid(),
                        "argv": args, "elf_sha256": fingerprint,
                    }
                    try:
                        Path(f"/proc/{pid}/oom_score_adj").write_text("1000")
                        score_adjustment = int(Path(f"/proc/{pid}/oom_score_adj").read_text())
                    except OSError as ex:
                        score_adjustment = f"NOT_ADMITTED: {ex!r}"
                break
            if cli.poll() is not None:
                break
            time.sleep(.001)

        if target and stopped and score_adjustment == 1000:
            # Host-side observer must receive a flushed identity witness
            # BEFORE the pressure child can OOM-kill this entire driver.
            # Losing the final in-container JSON must not erase provenance.
            print("QOO156_SOLVER_PREPRESSURE_JSON=" + json.dumps({
                "solver": SOLVER, "target": target,
                "oom_score_adj": score_adjustment,
                "solver_elf_sha256": fingerprint,
                "cli_sha256": sha(CLI),
                "qasm_source_sha256": sha(QASM),
                "kernel_oom_before": before.get("oom_kill", 0),
            }, sort_keys=True), flush=True)
            # The higher solver oom_score_adj forces an adversarial victim
            # preference. Do not equate this with actual WMC memory demand.
            # Bound all allocations and make one child touch actual pages.
            # Gradual, bounded 1-MiB page-committed chunks let the parent
            # stop test pressure on the FIRST kernel OOM event instead of
            # allowing a burst of kills that can destroy its witness.
            pressure_code = """
import time
blocks=[]
for j in range(320):
    block=bytearray(1048576)
    for i in range(0,1048576,4096):
        block[i]=1
    blocks.append(block)
    time.sleep(.010)
print('PRESSURE_FINISHED',flush=True)
time.sleep(2)
"""
            pressure = subprocess.Popen(
                [sys.executable, "-c", pressure_code],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                start_new_session=True,
            )
            end = time.monotonic() + 6
            while time.monotonic() < end:
                now = memory_events()
                if now.get("oom_kill", 0) > before.get("oom_kill", 0):
                    # Immediately release all stress-child allocations.
                    # The observed kernel OOM victim must still be checked
                    # independently; killing the pressure process is not proof.
                    if pressure.poll() is None:
                        pressure.kill()
                    break
                if pressure.poll() is not None:
                    break
                time.sleep(.001)
            try:
                pressure.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                pressure.kill()
                pressure.communicate(timeout=3)
            pressure_exit = pressure.returncode

        try:
            out, err = cli.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            # Distinct from the kernel event; never count this as OOM safety.
            if target and running(target["pid"], target["birth"]) is True:
                harness_killed_solver = True
                os.kill(target["pid"], signal.SIGKILL)
            try:
                out, err = cli.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(cli.pid, signal.SIGKILL)
                out, err = cli.communicate(timeout=3)
        observed_cli_exit = cli.returncode
    finally:
        if pressure is not None and pressure.poll() is None:
            pressure.kill()
            pressure.wait(timeout=3)
        if target and running(target["pid"], target["birth"]) is True:
            # Never leave a SIGSTOP'ed real solver orphan after a failed test.
            try:
                os.kill(target["pid"], signal.SIGKILL)
                harness_killed_solver = True
            except ProcessLookupError:
                pass
        if cli.poll() is None:
            os.killpg(cli.pid, signal.SIGKILL)
            cli.wait(timeout=3)

    after = memory_events()
    delta = after.get("oom_kill", 0) - before.get("oom_kill", 0)
    gone = (running(target["pid"], target["birth"]) is False) if target else False
    accepted = (
        target is not None and stopped and score_adjustment == 1000
        and delta >= 1 and gone and not harness_killed_solver
        # With an EXTERNAL Docker memory cap, QuPRS does not own the cgroup
        # and cannot truthfully classify the kernel's OOM reason. Its worker
        # exits 1 after receiving a real Solver SIGKILL; the outer supervisor
        # preserves that nonzero exit. Only this Docker test harness can
        # attribute the SIGKILL to memory.events oom_kill.
        and observed_cli_exit is not None and observed_cli_exit != 0 and out == ""
        and f"{SOLVER} failed: status=signal: 9 (SIGKILL)" in err
        and "WorkerFailed" in err
    )
    data = {
        "classification": "REAL_SOLVER_EXTERNAL_KERNEL_OOM_NO_FALSE_VERDICT_PASS" if accepted
                          else "NOT_ADMITTED",
        "solver": SOLVER, "solver_elf_sha256": fingerprint,
        "qasm_source_sha256": sha(QASM),
        "cli_sha256": sha(CLI),
        "target_solver": target, "solver_sigstop_confirmed": stopped,
        "solver_oom_score_adj": score_adjustment,
        "cgroup_memory_max_bytes": CAP_MIB * 1048576,
        "cgroup_memory_peak_bytes": int((ROOT / "memory.peak").read_text().strip()),
        "kernel_oom_kill_delta": delta,
        "solver_pid_no_longer_active": gone,
        "pressure_exit": pressure_exit,
        "test_harness_killed_solver": harness_killed_solver,
        "cli_returncode": observed_cli_exit, "cli_stdout": out[-500:],
        "cli_stderr": err[-1000:],
        "elapsed_observational_seconds": round(time.monotonic() - t0, 3),
        "scope": "Adversarial pressure victim-selection test: NOT natural Solver RSS or general case-memory requirement",
        "internal_cli_max_memory_mib": "NOT_TESTED",
        "cli_failure_semantics": "Externally enforced Docker OOM: generic WorkerFailed nonzero; kernel memory.events evidence is external. No claim of typed CLI MemoryLimitExceeded/125.",
        "worker_reports_authentic_solver_sigkill": f"{SOLVER} failed: status=signal: 9 (SIGKILL)" in err,
    }
    print("QOO156_SOLVER_OOM_VICTIM_JSON=" + json.dumps(data,sort_keys=True), flush=True)
    print(f"QOO156_SOLVER_OOM_VICTIM_{SOLVER}={data['classification']}", flush=True)
    return 0 if accepted else 2


if __name__ == "__main__":
    sys.exit(main())

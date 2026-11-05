#!/usr/bin/env python3
"""Opt-in Linux delegated cgroup-v2 smoke for QOO-175 research branches.

Run on a disposable Linux runner with a writable, delegated memory
controller. Does not invoke the quantum solver and does not claim
scientific-parity validation. No modification to host cgroup layout unless
the exact requested isolated leaf can be allocated and removed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import signal
import time
import tempfile
import subprocess
import sys
from pathlib import Path

# Standalone research witness: do not import the QuPRS package or require
# a built PyO3 extension simply to exercise the delegated kernel controller.
_resources_file = Path(__file__).resolve().parents[1] / "src" / "QuPRS" / "interface" / "rust_resources.py"
_spec = importlib.util.spec_from_file_location("qoo175_kernel_resources", _resources_file)
if _spec is None or _spec.loader is None:
    raise RuntimeError("private cgroup resource module is not readable")
_resources = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_resources)
MemoryCgroup = _resources.MemoryCgroup
ResourceAdmissionError = _resources.ResourceAdmissionError


_SUPERVISOR = r"""
import os, subprocess, sys
token = os.read(0, 1)
if token != b'1':
    sys.exit(31)
code = (
    "from pathlib import Path; import sys; "
    "m = Path('/proc/self/cgroup').read_text(); "
    "print('CHILD_CGROUP=' + m.strip(), flush=True)"
)
child = subprocess.run([sys.executable, '-c', code],
                       capture_output=True, text=True, timeout=10)
if child.returncode:
    sys.stderr.write(child.stderr)
    sys.exit(32)
sys.stdout.write(child.stdout)
"""


def positive_group_proof(limit_mib: int) -> dict:
    if sys.platform != "linux":
        raise ResourceAdmissionError("requires Linux")
    os.environ["QUPRS_ISOLATED_MAX_MEMORY_MIB"] = str(limit_mib)
    group = MemoryCgroup.create_if_requested()
    assert group is not None
    process = None
    snapshot = None
    cleanup_error = None
    try:
        process = subprocess.Popen(
            [sys.executable, "-c", _SUPERVISOR],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True,
            close_fds=True, text=False,
        )
        # The SUPERVISOR blocks reading an admission byte and cannot spawn
        # its child until its own cgroup membership is verified.
        group.admit(process.pid)
        stdout, stderr = process.communicate(input=b"1", timeout=15)
        if process.returncode != 0:
            raise AssertionError(
                f"supervisor rejected admission: {process.returncode}: {stderr[-500:]!r}"
            )
        message = stdout.decode("utf-8", "replace").strip()
        expected = group.path.name
        if not message.startswith("CHILD_CGROUP=0::") or expected not in message:
            raise AssertionError(f"Worker did not inherit isolated leaf: {message!r}")
        memory_max = (group.path / "memory.max").read_text().strip()
        if memory_max != str(limit_mib * 1024 * 1024):
            raise AssertionError("kernel memory.max did not match requested MiB")
        if group.oom_observed():
            raise AssertionError("unexpected OOM during non-stress admission test")
        snapshot = {
            "status": "PASS",
            "physical_memory_mib": limit_mib,
            "worker_cgroup": message.removeprefix("CHILD_CGROUP="),
            "memory_max_bytes": int(memory_max),
            "worker_spawn_after_supervisor_admission": True,
            "scope": "kernel_cgroup_inheritance_only",
        }
    finally:
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=3)
        try:
            group.cleanup()
        except Exception as exc:
            cleanup_error = exc
        if cleanup_error is not None:
            raise RuntimeError("kernel pilot leaf cleanup failed") from cleanup_error
    return snapshot


_OOM_CHILD = r"""
import os, sys
if os.read(0, 1) != b"1":
    sys.exit(31)
size = int(sys.argv[1]) * 1024 * 1024
block = bytearray(size)
# Touch physical pages: malloc/overcommit alone is not OOM evidence.
for i in range(0, size, 4096):
    block[i] = 1
print("UNEXPECTED_ALLOCATION_FINISHED", flush=True)
"""


def forced_oom_proof(limit_mib: int) -> dict:
    """Only allocates inside a requested capped leaf, after admission."""
    os.environ["QUPRS_ISOLATED_MAX_MEMORY_MIB"] = str(limit_mib)
    group = MemoryCgroup.create_if_requested()
    assert group is not None
    child = None
    try:
        # The test asserts an OOM KILL, not merely physical-memory pressure.
        # Disable swap ONLY for this newly created private cgroup leaf.
        # Otherwise swapping can allow a 288 MiB workload to finish under
        # memory.max=192 MiB while physical memory stays within the cap.
        swap_limit = group.path / "memory.swap.max"
        try:
            swap_limit.write_text("0")
            observed = swap_limit.read_text().strip()
        except OSError as exc:
            raise ResourceAdmissionError(
                "kernel witness requires writable leaf-local memory.swap.max"
            ) from exc
        if observed != "0":
            raise ResourceAdmissionError("kernel did not apply leaf-local swap cap")
        child = subprocess.Popen(
            [sys.executable, "-c", _OOM_CHILD, str(limit_mib + 320)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True,
            close_fds=True,
        )
        group.admit(child.pid)
        out, err = child.communicate(input=b"1", timeout=20)
        events = (group.path / "memory.events").read_text()
        current = (group.path / "memory.current").read_text().strip()
        peak_file = group.path / "memory.peak"
        peak = peak_file.read_text().strip() if peak_file.exists() else "unavailable"
        swap_current = (group.path / "memory.swap.current").read_text().strip()
        if child.returncode != -signal.SIGKILL:
            raise AssertionError(
                "expected kernel SIGKILL with leaf-local swap disabled; "
                f"returncode={child.returncode}, stdout={out[-160:]!r}, "
                f"stderr={err[-160:]!r}, current={current}, peak={peak}, "
                f"swap_current={swap_current}, memory.events={events!r}"
            )
        oom_kills = _resources._unique_counter(events, "oom_kill")
        if not group.oom_observed() or oom_kills < 1:
            raise AssertionError(
                "worker died but memory.events did not certify a kernel cgroup OOM kill"
            )
        return {
            "status": "PASS",
            "physical_memory_mib": limit_mib,
            "worker_oom_exit": child.returncode,
            "memory_events_oom_kill": oom_kills,
            "leaf_swap_max_bytes": 0,
            "memory_peak_bytes": peak,
            "scope": "kernel_cgroup_oom_and_cleanup",
        }
    finally:
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait(timeout=3)
        try:
            group.cleanup()
        except Exception as exc:
            raise RuntimeError("OOM pilot cgroup cleanup failed") from exc


_DETACHED_SUPERVISOR = r"""
import os, subprocess, sys, time
if os.read(0, 1) != b"1":
    sys.exit(31)
child = subprocess.Popen(
    [sys.executable, "-c", "import time;time.sleep(30)"],
    start_new_session=True,
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
with open(sys.argv[1], "w", encoding="ascii") as f:
    f.write(str(child.pid))
    f.flush()
time.sleep(30)
"""


def detached_descendant_proof(limit_mib: int) -> dict:
    """Simulate a SIGKILL'ed supervisor leaving a detached Solver child.

    A parent-owned cgroup is allowed to terminate only PIDs inside its own
    newly created leaf. This does not change a host's subreaper settings.
    """
    os.environ["QUPRS_ISOLATED_MAX_MEMORY_MIB"] = str(limit_mib)
    group = MemoryCgroup.create_if_requested()
    assert group is not None
    supervisor = None
    grandchild_pid = None
    cleanup_done = False
    with tempfile.TemporaryDirectory(prefix="qoo175-detached-") as temp:
        witness_file = Path(temp) / "orphan.pid"
        try:
            supervisor = subprocess.Popen(
                [sys.executable, "-c", _DETACHED_SUPERVISOR, str(witness_file)],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                close_fds=True, start_new_session=True,
            )
            group.admit(supervisor.pid)
            supervisor.stdin.write(b"1")
            supervisor.stdin.flush()
            deadline = time.monotonic() + 5
            while not witness_file.exists():
                if time.monotonic() >= deadline:
                    raise AssertionError("detached Solver child not observed")
                time.sleep(0.01)
            grandchild_pid = int(witness_file.read_text())
            before = Path(f"/proc/{grandchild_pid}/cgroup").read_text()
            if group.path.name not in before:
                raise AssertionError("detached child never entered owned cgroup leaf")
            os.kill(supervisor.pid, signal.SIGKILL)
            supervisor.wait(timeout=2)
            group.cleanup()
            cleanup_done = True
            if group.path.exists():
                raise AssertionError("cgroup cleanup did not remove detached-child leaf")
            status_file = Path(f"/proc/{grandchild_pid}/status")
            if status_file.exists():
                status_text = status_file.read_text()
                state = next(
                    (line.split(":", 1)[1].strip().split()[0]
                     for line in status_text.splitlines()
                     if line.startswith("State:")), ""
                )
                if state not in {"Z", "X", "x"}:
                    raise AssertionError(
                        f"detached child still executing after cleanup, state={state}"
                    )
            return {
                "status": "PASS",
                "physical_memory_mib": limit_mib,
                "detached_solver_inherited_private_cgroup": True,
                "supervisor_killed_with_sigkill": True,
                "detached_child_not_running_after_cleanup": True,
                "private_leaf_removed": True,
                "scope": "kernel_parent_owned_cgroup_detached_descendant_cleanup",
            }
        finally:
            if supervisor is not None and supervisor.poll() is None:
                try:
                    os.killpg(supervisor.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                supervisor.wait(timeout=3)
            if not cleanup_done:
                try:
                    group.cleanup()
                except Exception as exc:
                    raise RuntimeError("detached-child test cgroup cleanup failed") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--memory-mib", type=int, default=192)
    parser.add_argument("--oom", action="store_true", help="perform bounded in-cgroup OOM witness")
    parser.add_argument("--detached", action="store_true", help="verify cgroup cleanup of detached child after supervisor SIGKILL")
    args = parser.parse_args()
    if not 64 <= args.memory_mib <= 4096:
        parser.error("memory-mib must be between 64 and 4096")
    if args.oom and args.detached:
        parser.error("choose either --oom or --detached")
    if args.oom and args.memory_mib > 256:
        parser.error("OOM stress is capped at 256 MiB to protect disposable hosts")
    try:
        if args.oom:
            result = forced_oom_proof(args.memory_mib)
        elif args.detached:
            result = detached_descendant_proof(args.memory_mib)
        else:
            result = positive_group_proof(args.memory_mib)
    except ResourceAdmissionError as exc:
        print(json.dumps({
            "status": "NOT_MET",
            "reason": str(exc),
            "scope": "kernel_cgroup_inheritance_only",
        }, sort_keys=True))
        return 2
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "reason": str(exc),
            "scope": "kernel_cgroup_inheritance_only",
        }, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
        child = subprocess.Popen(
            [sys.executable, "-c", _OOM_CHILD, str(limit_mib + 96)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True,
            close_fds=True,
        )
        group.admit(child.pid)
        out, err = child.communicate(input=b"1", timeout=20)
        if child.returncode != -signal.SIGKILL:
            raise AssertionError(
                f"expected cgroup SIGKILL, received {child.returncode}: "
                f"{out[-100:]!r} {err[-100:]!r}"
            )
        events = (group.path / "memory.events").read_text()
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--memory-mib", type=int, default=192)
    parser.add_argument("--oom", action="store_true", help="perform bounded in-cgroup OOM witness")
    args = parser.parse_args()
    if not 64 <= args.memory_mib <= 4096:
        parser.error("memory-mib must be between 64 and 4096")
    try:
        result = (forced_oom_proof(args.memory_mib)
                  if args.oom else positive_group_proof(args.memory_mib))
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

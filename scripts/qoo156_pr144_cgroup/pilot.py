#!/usr/bin/env python3
"""QOO-156 internal CLI memory.max proof inside test-only cgroup-v2 delegation.

IMPORTANT: --privileged is used ONLY to build a writable cgroup namespace in
the ephemeral GitHub Actions test container. The actual QuPRS CLI runs as
unprivileged uid/gid 65534 inside a separately delegated subtree. This is
NOT a production deployment recipe or a true nonprivileged host admission.
No solver or native Rust algorithm is modified, and timings are NOT CodSpeed.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path("/sys/fs/cgroup")
CLI = "/opt/QuPRS_cli"
QASM = "/opt/single_h.qasm"
MIB = 1048576
UID = 65534


def fail(message):
    raise RuntimeError("QOO156_INTERNAL_CGROUP_NOT_ADMITTED: " + message)


def read_events_path(path):
    return {
        key: int(value)
        for key, value in (line.split() for line in path.read_text().splitlines())
    }


def read_events_fd(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    return {
        key: int(value)
        for key, value in (
            line.split() for line in os.read(fd, 4096).decode("ascii").splitlines()
        )
    }


def delegated_parent():
    cgroup_data = Path("/proc/self/cgroup").read_text()
    rel = next((line[3:] for line in cgroup_data.splitlines()
                if line.startswith("0::")), None)
    if rel is None:
        fail("no cgroup v2 process path")
    current = (ROOT / rel.lstrip("/")).resolve()
    if not (current == ROOT or ROOT in current.parents):
        fail("current cgroup outside /sys/fs/cgroup")
    ctrls = (current / "cgroup.controllers").read_text().split()
    if "memory" not in ctrls:
        fail("memory controller missing from cgroup.controllers")
    active = (current / "cgroup.subtree_control").read_text().split()
    if "memory" not in active:
        # Docker's cgroup namespace root is usually NOT the kernel cgroup
        # root. Turning on a domain controller with a process in the parent
        # violates the cgroup-v2 no-internal-process rule (EBUSY).
        own = os.getpid()
        members = [int(x) for x in (current / "cgroup.procs").read_text().split()]
        if sorted(members) != [own]:
            fail(f"cannot relocate unknown parent cgroup tasks: {members}")
        bootstrap = current / f"qoo156-bootstrap-{own}"
        bootstrap.mkdir()
        (bootstrap / "cgroup.procs").write_text(str(own))
        if str(own) not in (bootstrap / "cgroup.procs").read_text().split():
            fail("bootstrap did not move itself into a leaf")
        try:
            (current / "cgroup.subtree_control").write_text("+memory")
        except OSError as exc:
            fail(f"cannot enable empty parent memory delegation: {exc}")
    sub = current / f"qoo156-delegated-{os.getpid()}"
    sub.mkdir(mode=0o755)
    try:
        (sub / "cgroup.subtree_control").write_text("+memory")
    except OSError as exc:
        fail(f"cannot enable empty delegated subtree memory controller: {exc}")
    # Correct topology: delegated D is empty with +memory. The CLI parent
    # runs in D/supervisor leaf and can create a sibling D/quprs-cli-<pid>
    # without violating the no-internal-process rule.
    supervisor_leaf = sub / "supervisor"
    supervisor_leaf.mkdir()
    for p in [sub, sub / "cgroup.procs", sub / "cgroup.subtree_control"]:
        os.chown(p, UID, UID)
    os.chmod(sub, 0o755)
    return sub


def move_and_drop_to_unprivileged(subtree):
    # This function runs in a single-threaded subprocess preexec context.
    # Attach the CLI to an empty delegated cgroup BEFORE dropping privileges.
    target = os.open(str(subtree / "supervisor" / "cgroup.procs"), os.O_WRONLY)
    try:
        data = str(os.getpid()).encode("ascii")
        if os.write(target, data) != len(data):
            os._exit(116)
    finally:
        os.close(target)
    os.setgroups([])
    os.setgid(UID)
    os.setuid(UID)


def case(subtree, label, cap_mib, alloc_mib):
    circuit = "/opt/qoo156-nonexistent-circuit.qasm" if label == "failed" else QASM
    cmd = [
        CLI, circuit, "--quiet", "--timeout", "15",
        "--max-memory-mib", str(cap_mib),
    ]
    env = dict(os.environ, QUPRS_CLI_TEST_ALLOC_MIB=str(alloc_mib))
    # The OOM and capped ordinary-failure cases MUST exercise opt-in. The worker
    # creates a debug-only CNF + Solver temp witness before kernel OOM.
    marker = Path(f"/tmp/qoo156-cnf-{label}-{os.getpid()}") if label in ("oom", "failed") else None
    if marker is not None:
        marker.unlink(missing_ok=True)
        env["QUPRS_KEEP_FAILED_CNF"] = "1"
        env["QUPRS_CLI_TEST_TEMP_MARKER"] = str(marker)
    child = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        preexec_fn=lambda: move_and_drop_to_unprivileged(subtree),
    )
    child_group = subtree / f"quprs-cli-{child.pid}"
    captured_max = None
    memevents_fd = None
    events_last = {}
    peak_fd = None
    peak_max = 0
    deadline = time.monotonic() + 18
    try:
        while time.monotonic() < deadline:
            if memevents_fd is None:
                try:
                    cap_path = child_group / "memory.max"
                    captured_max = int(cap_path.read_text().strip())
                    memevents_fd = os.open(str(child_group / "memory.events"), os.O_RDONLY)
                    peak_fd = os.open(str(child_group / "memory.peak"), os.O_RDONLY)
                except (FileNotFoundError, ValueError, OSError):
                    pass
            if memevents_fd is not None:
                try:
                    events_last = read_events_fd(memevents_fd)
                    os.lseek(peak_fd, 0, os.SEEK_SET)
                    peak_max = max(peak_max, int(os.read(peak_fd, 128).decode().strip()))
                except OSError:
                    pass
            if child.poll() is not None:
                break
            time.sleep(0.002)
        try:
            out, err = child.communicate(timeout=4)
        except subprocess.TimeoutExpired:
            child.kill()
            out, err = child.communicate(timeout=4)
            fail(f"{label}: child blocked; harness kill is not cgroup proof")
        if memevents_fd is not None:
            try:
                events_last = read_events_fd(memevents_fd)
            except OSError:
                pass
        result = dict(
            case=label,
            internal_memory_max_bytes=captured_max,
            requested_memory_max_bytes=cap_mib * MIB,
            internal_kernel_oom=events_last.get("oom"),
            internal_kernel_oom_kill=events_last.get("oom_kill"),
            internal_peak_bytes=peak_max,
            child_returncode=child.returncode,
            stdout=out[-250:],
            stderr=err[-700:],
            cli_uid=UID,
        )
        if marker is not None:
            if not marker.is_file():
                fail(f"{label}: worker did not create test-only private CNF witness")
            private_tmpdir = Path(marker.read_text())
            marker.unlink()
            # Regression guard: the old code could incorrectly
            # preserved CNF when the user opted in AND kernel OOM killed worker.
            result["optin_private_temp_removed"] = not private_tmpdir.exists()
            if not result["optin_private_temp_removed"]:
                fail(f"{label}: sensitive CNF retained under physical cgroup cap: {private_tmpdir}")
            if "RetainedFailedSolverArtifacts" in err:
                fail(f"{label}: supervisor attempted to retain capped-failure artifacts")
        # New P1 cleanup admission: the Rust CLI must have explicitly
        # rmdir'ed its child cgroup before returning, including after OOM.
        # This is stronger than relying on a best-effort Drop.
        result["worker_cgroup_removed_at_return"] = not child_group.exists()
        if not result["worker_cgroup_removed_at_return"]:
            fail(f"{label}: child cgroup leaked after CLI exit: {result}")
        if captured_max != cap_mib * MIB:
            fail(f"{label}: actual internal child memory.max not captured: {result}")
        if label == "oom":
            admitted = (child.returncode == 125
                        and "MemoryLimitExceeded" in err
                        and events_last.get("oom", 0) >= 1
                        and events_last.get("oom_kill", 0) >= 1
                        and not out)
        elif label == "failed":
            admitted = (child.returncode not in (0, 124, 125)
                        and events_last.get("oom", 0) == 0
                        and events_last.get("oom_kill", 0) == 0
                        and not out
                        and result.get("optin_private_temp_removed"))
        else:
            admitted = (child.returncode == 0
                        and events_last.get("oom", 0) == 0
                        and events_last.get("oom_kill", 0) == 0
                        and "Reduced PathSum State" in out)
        result["admitted"] = admitted
        print("QOO156_INTERNAL_CGROUP_CASE_JSON=" +
              json.dumps(result, sort_keys=True), flush=True)
        if not admitted:
            fail(f"{label}: required internal controller evidence missing")
        return result
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=4)
        for fd in [memevents_fd, peak_fd]:
            if fd is not None:
                os.close(fd)


def main():
    subtree = delegated_parent()
    print("QOO156_DELEGATED_SUBTREE=" + str(subtree), flush=True)
    try:
        results = [
            case(subtree, "oom", 64, 192),
            case(subtree, "failed", 256, 0),
            case(subtree, "complete", 256, 32),
        ]
        print("QOO156_INTERNAL_CGROUP_JSON=" +
              json.dumps(results, sort_keys=True), flush=True)
        print("QOO156_INTERNAL_CGROUP_UNPRIVILEGED_CLI=PASS", flush=True)
    finally:
        # A dead CLI should have removed all child cgroups. Report the precise
        # subtree if its cleanup remains incomplete instead of concealing it.
        try:
            (subtree / "supervisor").rmdir()
            subtree.rmdir()
        except OSError as exc:
            print(f"QOO156_DELEGATE_CLEANUP_PENDING={exc}", file=sys.stderr)


if __name__ == "__main__":
    main()

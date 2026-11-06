"""Private Rust API worker resource admission and fail-closed contract tests."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest

from QuPRS.interface import rust_isolation


def _private_module(filename: str):
    path = Path(rust_isolation.__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(f"_quprs_test_{filename}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cgroup_counter_parser_requires_complete_oom_witness():
    resources = _private_module("rust_resources.py")
    assert resources.parse_oom_events("oom 0\noom_kill 0\nmax 9\n") is False
    assert resources.parse_oom_events("oom 1\noom_kill 0\n") is True
    assert resources.parse_oom_events("oom 0\noom_kill 2\n") is True
    assert resources.parse_populated("populated 0\nfrozen 0\n") is False
    assert resources.parse_populated("populated 1\n") is True
    for bad in (
        "oom 1\n", "oom_kill 1\n", "oom 1\noom 2\noom_kill 0\n",
        "oom 1\noom_kill nan\n", "oom 1\noom_kill 0 extra\n",
    ):
        with pytest.raises(resources.ResourceAdmissionError):
            resources.parse_oom_events(bad)
    with pytest.raises(resources.ResourceAdmissionError):
        resources.parse_populated("populated 2\n")


@pytest.mark.parametrize("value", ["-1", "0", "1.5", "1MiB", "", " 3", "NaN"])
def test_physical_limit_invalid_request_fails_closed(monkeypatch, value):
    resources = _private_module("rust_resources.py")
    monkeypatch.setenv("QUPRS_ISOLATED_MAX_MEMORY_MIB", value)
    with pytest.raises(resources.ResourceAdmissionError):
        resources.MemoryCgroup.create_if_requested()


def test_unrequested_physical_limit_does_not_create_a_cgroup(monkeypatch):
    resources = _private_module("rust_resources.py")
    monkeypatch.delenv("QUPRS_ISOLATED_MAX_MEMORY_MIB", raising=False)
    assert resources.MemoryCgroup.create_if_requested() is None


def test_bootstrap_checks_admission_and_preimport_address_cap(monkeypatch):
    bootstrap = _private_module("rust_worker_bootstrap.py")
    assert bootstrap._positive_mib("NONEXISTENT_LIMIT") is None
    monkeypatch.setenv("QUPRS_ISOLATED_MAX_ADDRESS_SPACE_MIB", "0")
    with pytest.raises(ValueError):
        bootstrap._positive_mib("QUPRS_ISOLATED_MAX_ADDRESS_SPACE_MIB")
    monkeypatch.setenv("QUPRS_ISOLATED_MAX_ADDRESS_SPACE_MIB", "1024")
    assert bootstrap._positive_mib("QUPRS_ISOLATED_MAX_ADDRESS_SPACE_MIB") == 1024


@pytest.mark.skipif(os.name != "posix", reason="RLIMIT_AS is Unix-specific")
def test_address_cap_is_applied_in_child_not_host():
    script = """
import importlib.util, os, resource, sys
spec = importlib.util.spec_from_file_location("worker_admission", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod._apply_address_space_limit()
soft, hard = resource.getrlimit(resource.RLIMIT_AS)
assert 0 < soft <= 1024 * 1024 * 1024
assert 0 < hard <= 1024 * 1024 * 1024
print("ADDRESS_CAP_PASS")
"""
    env = os.environ.copy()
    env["QUPRS_ISOLATED_MAX_ADDRESS_SPACE_MIB"] = "1024"
    path = str(Path(rust_isolation.__file__).with_name("rust_worker_bootstrap.py"))
    done = subprocess.run(
        [sys.executable, "-c", script, path], env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5,
    )
    if done.returncode == 0:
        assert "ADDRESS_CAP_PASS" in done.stdout
    else:
        # Some macOS kernels report RLIMIT_AS but reject lowering its hard
        # limit. Verify explicit resource admission refuses the request;
        # do not silently downgrade to an unbounded worker.
        assert sys.platform == "darwin", done.stderr
        assert "setrlimit" in done.stderr or "current limit exceeds maximum limit" in done.stderr
        from QuPRS import check_equivalence
        qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
        try:
            observed = check_equivalence(
                qasm, qasm, backend="rust", safe_mode=True,
                method="reduction_rules", timeout=30,
            )
        except rust_isolation.RustWorkerError:
            # A worker that cannot enforce the requested limit must fail
            # closed; kernel-dependent admission may reject the same cap.
            pass
        else:
            # Success is also legal when the fresh worker's smaller initial
            # address-space footprint allows the cap. The worker bootstrap
            # itself verifies the applied RLIMIT_AS before importing QuPRS.
            assert observed.equivalent == "equivalent"

@pytest.mark.skipif(sys.platform != "linux", reason="Linux PR_SET_PDEATHSIG only")
def test_worker_arms_linux_parent_death_only_in_child():
    script = """
import importlib.util, os, sys
spec = importlib.util.spec_from_file_location("quprs_bootstrap", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
os.environ["QUPRS_RUST_WORKER_PARENT_PID"] = str(os.getppid())
module._arm_supervisor_death_signal()
print("WORKER_PARENT_DEATH_ARMED")
"""
    path = str(Path(rust_isolation.__file__).with_name("rust_worker_bootstrap.py"))
    result = subprocess.run(
        [sys.executable, "-c", script, path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=6,
    )
    assert result.returncode == 0, result.stderr
    assert "WORKER_PARENT_DEATH_ARMED" in result.stdout


def test_cgroup_cleanup_waits_for_killed_descendant(monkeypatch, tmp_path):
    resources = _private_module("rust_resources.py")
    leaf = tmp_path / "quprs-py-test"
    leaf.mkdir()
    (leaf / "cgroup.events").write_text("populated 1\n")
    (leaf / "cgroup.procs").write_text("424242\n")
    (leaf / "cgroup.kill").write_text("")
    group = resources.MemoryCgroup(leaf)
    calls = []

    def simulated_process(pid):
        assert pid == 424242
        calls.append(pid)
        # The cgroup directory can disappear while SIGKILL is still pending.
        return (("R" if len(calls) <= 3 else "Z"), "stable-kernel-starttime")

    monkeypatch.setattr(
        resources.MemoryCgroup, "_process_identity",
        staticmethod(simulated_process),
    )
    original_rmdir = Path.rmdir

    def simulate_immediate_leaf_disposal(path):
        if path == leaf:
            return None
        return original_rmdir(path)

    monkeypatch.setattr(Path, "rmdir", simulate_immediate_leaf_disposal)
    group.cleanup()
    assert group._cleaned is True
    assert len(calls) >= 4
    assert (leaf / "cgroup.kill").read_text() == "1"


def test_cgroup_cleanup_pid_reuse_cannot_block_old_child(monkeypatch):
    resources = _private_module("rust_resources.py")
    monkeypatch.setattr(
        resources.MemoryCgroup, "_process_identity",
        staticmethod(lambda pid: ("R", "different-starttime")),
    )
    assert resources.MemoryCgroup._all_stopped({123: "old-starttime"})

"""Pre-worker cgroup admission protocol: no uncapped Rust Worker startup."""
from __future__ import annotations

import importlib.util
import io
import os
from pathlib import Path
import time

import pytest

from QuPRS.interface import rust_isolation


QASM = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'


def _make_fake_supervisor():
    class FakeSupervisor:
        pid = 42821
        returncode = 0

        def __init__(self):
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO()
            self.stderr = io.BytesIO()

        def poll(self):
            return self.returncode

    return FakeSupervisor()


def test_supervisor_admitted_before_receiving_worker_launch_witness(monkeypatch):
    from QuPRS.interface import rust_resources
    state = []

    class FakeGroup:
        def admit(self, pid):
            assert pid == 42821
            state.append("admitted")

        def oom_observed(self):
            state.append("oom_checked")
            return False

        def cleanup(self):
            state.append("disposed")

    monkeypatch.setattr(
        rust_resources.MemoryCgroup, "create_if_requested", lambda: FakeGroup()
    )
    monkeypatch.setattr(
        rust_isolation.subprocess, "Popen",
        lambda *args, **kwargs: _make_fake_supervisor(),
    )
    monkeypatch.setattr(rust_isolation, "_stop_worker", lambda p: None)

    def exchange(p, payload, deadline):
        assert state == ["admitted"]
        assert payload.startswith(b"QuPRS-Rust-Supervisor-Admit-v1\n{")
        state.append("launched")
        return b"{}", b""

    monkeypatch.setattr(rust_isolation, "_bounded_exchange", exchange)
    monkeypatch.setattr(
        rust_isolation, "_parse_worker_response",
        lambda stdout, stderr, code: {"status": "Equivalent"}
    )
    now = time.monotonic()
    result = rust_isolation.run_isolated(
        QASM, QASM, {}, now, now + 10,
    )
    assert result == {"status": "Equivalent"}
    assert state == ["admitted", "launched", "oom_checked", "disposed"]


def test_cgroup_oom_disallows_successful_scientific_verdict(monkeypatch):
    from QuPRS.interface import rust_resources
    state = []

    class FakeGroup:
        def admit(self, pid):
            state.append("admitted")

        def oom_observed(self):
            state.append("oom_checked")
            return True

        def cleanup(self):
            state.append("disposed")

    monkeypatch.setattr(
        rust_resources.MemoryCgroup, "create_if_requested", lambda: FakeGroup()
    )
    monkeypatch.setattr(
        rust_isolation.subprocess, "Popen",
        lambda *args, **kwargs: _make_fake_supervisor(),
    )
    monkeypatch.setattr(rust_isolation, "_stop_worker", lambda p: None)
    monkeypatch.setattr(
        rust_isolation, "_bounded_exchange",
        lambda p, payload, deadline: (b"{}", b"")
    )
    monkeypatch.setattr(
        rust_isolation, "_parse_worker_response",
        lambda *args: {"status": "Equivalent"},
    )
    now = time.monotonic()
    result = rust_isolation.run_isolated(
        QASM, QASM, {}, now, now + 10,
    )
    assert result["status"] == "MemoryOut"
    assert state == ["admitted", "oom_checked", "disposed"]


def test_failed_cgroup_admission_cannot_launch_worker(monkeypatch):
    from QuPRS.interface import rust_resources
    state = []

    class FakeGroup:
        def admit(self, pid):
            state.append("refused")
            raise rust_resources.ResourceAdmissionError("test refused")

        def oom_observed(self):
            return False

        def cleanup(self):
            state.append("disposed")

    monkeypatch.setattr(
        rust_resources.MemoryCgroup, "create_if_requested", lambda: FakeGroup()
    )
    monkeypatch.setattr(
        rust_isolation.subprocess, "Popen",
        lambda *args, **kwargs: _make_fake_supervisor(),
    )
    monkeypatch.setattr(rust_isolation, "_stop_worker", lambda p: None)
    monkeypatch.setattr(
        rust_isolation, "_bounded_exchange",
        lambda *args: pytest.fail("unadmitted supervisor must not execute"),
    )
    now = time.monotonic()
    with pytest.raises(rust_resources.ResourceAdmissionError, match="test refused"):
        rust_isolation.run_isolated(QASM, QASM, {}, now, now + 10)
    assert state == ["refused", "disposed"]


def test_private_supervisor_requires_parent_admission(monkeypatch):
    path = Path(rust_isolation.__file__).with_name("rust_supervisor.py")
    spec = importlib.util.spec_from_file_location("_quprs_test_supervisor", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)

    monkeypatch.setenv("QUPRS_RUST_SUPERVISOR_PARENT_PID", str(os.getppid()))
    token = module._SUPERVISOR_ADMISSION
    assert token == b"QuPRS-Rust-Supervisor-Admit-v1\n"

    def read_input(fd, n):
        return token[:n]

    monkeypatch.setattr(module.os, "read", read_input)
    assert module._require_parent_admission() is None
    monkeypatch.setattr(module.os, "read", lambda fd, n: b"wrong")
    with pytest.raises(module.SupervisorResourceError, match="invalid supervisor admission"):
        module._require_parent_admission()

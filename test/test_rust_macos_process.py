"""Contract tests for macOS native Worker process-tree supervision.

The Rust CLI is the reference: isolate one Worker, cancel via deadline or
signal, kill observed detached Solver descendants, publish no partial science.
These tests exercise only the opt-in Python Supervisor's process helper.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from QuPRS.interface import rust_isolation


def _macos_tree_module():
    path = Path(rust_isolation.__file__).with_name("rust_macos_process.py")
    spec = importlib.util.spec_from_file_location("qoo175_macos_tree_tests", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _record(parent: int, state: str, birth: str):
    return (parent, state, birth)


def test_macos_process_tree_parser_and_pid_birth_witness(monkeypatch):
    mod = _macos_tree_module()
    text = (
        " 42  1 Ss Fri Nov  6 01:02:03 2026\n"
        " 43 42 S  Fri Nov  6 01:02:04 2026\n"
    )

    class Result:
        stdout = text
        stderr = ""
        returncode = 0

    monkeypatch.setattr(mod.subprocess, "run", lambda *args, **kwargs: Result())
    records = mod._snapshot()
    assert records[42] == (1, "S", "Fri Nov 6 01:02:03 2026")
    assert records[43] == (42, "S", "Fri Nov 6 01:02:04 2026")


def test_macos_tree_remembers_detached_descendant_after_reparent(monkeypatch):
    mod = _macos_tree_module()
    original = {
        42: _record(1, "S", "worker-birth"),
        43: _record(42, "S", "solver-birth"),
        44: _record(43, "S", "grandchild-birth"),
    }
    monkeypatch.setattr(mod, "_snapshot", lambda: original)
    tree = mod.DarwinProcessTree(42)
    tree._observe(original)
    assert tree._owned == {
        42: "worker-birth", 43: "solver-birth", 44: "grandchild-birth"
    }
    # A process detached from the worker's original process group and got
    # reparented, but its prior PID+starttime identity remains recognized.
    after = {
        43: _record(1, "S", "solver-birth"),
        44: _record(43, "S", "grandchild-birth"),
    }
    tree._observe(after)
    assert 43 in tree._owned and 44 in tree._owned


def test_macos_pid_reuse_is_never_killed(monkeypatch):
    mod = _macos_tree_module()
    before = {
        42: _record(1, "S", "worker-birth"),
        43: _record(42, "S", "old-solver"),
    }
    after = {
        42: _record(1, "S", "worker-birth"),
        43: _record(42, "S", "new-unrelated-process"),
    }
    state = {"records": before}
    monkeypatch.setattr(mod, "_snapshot", lambda: state["records"])
    tree = mod.DarwinProcessTree(42)
    tree._observe(before)
    state["records"] = after
    monkeypatch.setattr(mod.os, "kill", lambda *args: pytest.fail("PID reuse signalled"))
    with pytest.raises(mod.ProcessTreeError, match="reused"):
        tree.kill_observed_descendants()


def test_macos_ps_failure_is_fail_closed(monkeypatch):
    mod = _macos_tree_module()
    root = {42: _record(1, "S", "worker")}
    monkeypatch.setattr(mod, "_snapshot", lambda: root)
    tree = mod.DarwinProcessTree(42)

    def fail():
        raise mod.ProcessTreeError("ps timed out")

    monkeypatch.setattr(mod, "_snapshot", fail)
    with pytest.raises(mod.ProcessTreeError, match="ps timed out"):
        tree.kill_observed_descendants()


@pytest.mark.skipif(sys.platform != "darwin", reason="real macOS ps and process groups")
def test_macos_detached_solver_is_killed_by_private_python_supervisor(tmp_path):
    mod = _macos_tree_module()
    witness = tmp_path / "solver.pid"
    root_script = """
import subprocess, sys, time
p = subprocess.Popen(
    [sys.executable, "-c", "import time;time.sleep(30)"],
    start_new_session=True, stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
with open(sys.argv[1], "w", encoding="ascii") as f:
    f.write(str(p.pid))
time.sleep(30)
"""
    worker = subprocess.Popen(
        [sys.executable, "-c", root_script, str(witness)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )
    tracked = None
    child_pid = None
    try:
        tracked = mod.DarwinProcessTree(worker.pid)
        tracked.start()
        deadline = time.monotonic() + 6
        while not witness.is_file():
            assert time.monotonic() < deadline, "detached test Solver was never spawned"
            time.sleep(.02)
        child_pid = int(witness.read_text())
        # Sampler runs only inside the isolated supervisor in production.
        observe_deadline = time.monotonic() + 3
        while child_pid not in tracked._owned:
            assert time.monotonic() < observe_deadline, "Sampler missed live Solver"
            time.sleep(.02)
        tracked.kill_observed_descendants()
        rust_isolation._stop_worker(worker)
        tracked.verify_stopped()
    finally:
        if child_pid is not None:
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if worker.poll() is None:
            rust_isolation._stop_worker(worker)

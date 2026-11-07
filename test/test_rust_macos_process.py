"""Contract and fault-injection tests for native macOS process supervision."""
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

def _module():
    path = Path(rust_isolation.__file__).with_name("rust_macos_process.py")
    spec = importlib.util.spec_from_file_location("quprs_macos_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _fake(monkeypatch, mod):
    uid = os.geteuid()
    records = {42: (1, 2, uid, 100, 11), 43: (42, 3, uid, 100, 12)}
    monkeypatch.setattr(mod, "_info", lambda pid: records.get(pid))
    monkeypatch.setattr(mod, "_children", lambda pid: [
        child for child, info in records.items() if info[0] == pid
    ])
    return records

def test_kernel_bsdinfo_layout_has_expected_136_bytes():
    import ctypes
    mod = _module()
    assert ctypes.sizeof(mod._BSDInfo) == 136

def test_native_macos_tracking_reparent_and_microsecond_birth(monkeypatch):
    mod = _module()
    records = _fake(monkeypatch, mod)
    tree = mod.DarwinProcessTree(42)
    tree._sample()
    assert 43 in tree._owned
    records[43] = (1, 3, os.geteuid(), 100, 12)
    tree._sample()
    assert 43 in tree._owned

def test_macos_reused_pid_in_same_second_is_never_signalled(monkeypatch):
    mod = _module()
    records = _fake(monkeypatch, mod)
    tree = mod.DarwinProcessTree(42)
    tree._sample()
    records[43] = (42, 3, os.geteuid(), 100, 13)  # same second, new microsecond
    monkeypatch.setattr(mod.os, "kill", lambda *a: pytest.fail("reused PID signalled"))
    with pytest.raises(mod.ProcessTreeError, match="reused|identity"):
        tree.kill_observed_descendants()

def test_macos_monitor_failure_still_kills_known_child(monkeypatch):
    mod = _module()
    records = _fake(monkeypatch, mod)
    tree = mod.DarwinProcessTree(42)
    tree._sample()
    killed = []
    monkeypatch.setattr(mod.os, "kill", lambda pid, signum: killed.append(pid))
    tree._error = mod.ProcessTreeError("forced scanner failure")
    def broken_scan():
        raise mod.ProcessTreeError("forced snapshot failure")
    monkeypatch.setattr(tree, "_sample", broken_scan)
    with pytest.raises(mod.ProcessTreeError, match="monitoring failed"):
        tree.kill_observed_descendants()
    assert killed == [43], "known detached Solver must still be killed"

def test_macos_bounded_cleanup_when_descendants_survive(monkeypatch):
    mod = _module()
    records = _fake(monkeypatch, mod)
    tree = mod.DarwinProcessTree(42)
    tree._sample()
    tree._cleanup_deadline = time.monotonic() - 1
    with pytest.raises(mod.ProcessTreeError, match="deadline|survived"):
        tree.verify_stopped()

def test_macos_descendant_limit_fails_closed(monkeypatch):
    mod = _module()
    records = _fake(monkeypatch, mod)
    for pid in range(100, 100+mod._MAX_PIDS):
        records[pid] = (42, 2, os.geteuid(), 100, pid)
    tree = mod.DarwinProcessTree(42)
    with pytest.raises(mod.ProcessTreeError, match="too many|exceeded"):
        tree._sample()

@pytest.mark.skipif(sys.platform != "darwin", reason="native Darwin libproc")
def test_macos_detached_solver_cleanup_real_kernel(tmp_path):
    mod = _module()
    pidfile = tmp_path / "solver.pid"
    script = (
        "import os,subprocess,sys,time\\n"
        "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(25)'],"
        "start_new_session=True,stdin=subprocess.DEVNULL,"
        "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\\n"
        "temp_pidfile=sys.argv[1]+'.tmp'\\n"
        "with open(temp_pidfile,'w') as f:\\n"
        "    f.write(str(p.pid))\\n"
        "os.replace(temp_pidfile,sys.argv[1])\\n"
        "time.sleep(25)\\n"
    )
    worker = subprocess.Popen(
        [sys.executable, "-c", script, str(pidfile)],
        start_new_session=True, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
    )
    child = None
    try:
        tree = mod.DarwinProcessTree(worker.pid)
        tree.start()
        deadline = time.monotonic()+6
        while not pidfile.exists():
            assert time.monotonic() < deadline
            time.sleep(.02)
        child = int(pidfile.read_text())
        while child not in tree._owned:
            assert time.monotonic() < deadline, "live Solver was never observed"
            time.sleep(.01)
        tree.kill_observed_descendants()
        rust_isolation._stop_worker(worker)
        tree.verify_stopped()
    finally:
        if child is not None:
            try: os.kill(child, signal.SIGKILL)
            except ProcessLookupError: pass
        if worker.poll() is None: rust_isolation._stop_worker(worker)


def test_libproc_zero_count_with_errno_is_not_silent_empty_tree(monkeypatch):
    import ctypes
    import errno
    mod = _module()
    class Lib:
        def proc_listchildpids(self, pid, buffer, size):
            ctypes.set_errno(errno.EPERM)
            return 0
    monkeypatch.setattr(mod, "_lib", lambda: Lib())
    with pytest.raises(mod.ProcessTreeError, match="enumeration failed"):
        mod._children(42)

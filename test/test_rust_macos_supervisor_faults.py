"""End-to-end native macOS Python Supervisor fault contracts.

A private test harness swaps only the Worker subprocess with a deterministic
detached-Solver fixture; the actual Supervisor.run/IPC/deadline/cleanup execute.
No test-only switch or fake solver is added to the production implementation.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import pytest

from QuPRS.interface import rust_isolation


_FAKE_WORKER = """
import os,subprocess,sys,time
witness=b'QuPRS-Rust-Worker-Admit-v1\\n'
if sys.stdin.buffer.read(len(witness))!=witness: sys.exit(97)
sys.stdin.buffer.read()
child=subprocess.Popen(
    [sys.executable,'-c','import time;time.sleep(30)'],
    stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,start_new_session=True,
)
with open(sys.argv[1], 'w') as f:
    f.write(str(child.pid))
time.sleep(30)
"""

_SUPERVISOR = """
import importlib.util,os,subprocess,sys
path=os.environ['QUPRS_PILOT_SUPERVISOR']
spec=importlib.util.spec_from_file_location('qoo175_private_supervisor',path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
original=subprocess.Popen
def fixture_spawn(args,**kwargs):
    if str(args[1]).endswith('rust_worker_bootstrap.py'):
        args=[sys.executable,'-c',os.environ['QUPRS_PILOT_WORKER'],
              os.environ['QUPRS_PILOT_PIDFILE']]
    return original(args,**kwargs)
m.subprocess.Popen=fixture_spawn
sys.exit(m.run())
"""

@pytest.mark.skipif(sys.platform != "darwin", reason="macOS real PID and signal behavior")
@pytest.mark.parametrize("stop", ["deadline", "sigterm"])
def test_supervisor_real_ipc_detached_solver_cleanup(tmp_path, stop):
    supervisor_path = Path(rust_isolation.__file__).with_name("rust_supervisor.py")
    pidfile = tmp_path / "detached.pid"
    env = os.environ.copy()
    env.update({
        "QUPRS_RUST_SUPERVISOR_PARENT_PID": str(os.getpid()),
        "QUPRS_PILOT_SUPERVISOR": str(supervisor_path),
        "QUPRS_PILOT_WORKER": _FAKE_WORKER,
        "QUPRS_PILOT_PIDFILE": str(pidfile),
    })
    p = subprocess.Popen(
        [sys.executable, "-I", "-c", _SUPERVISOR],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, start_new_session=True,
    )
    child = None
    try:
        now = time.monotonic()
        req = {
            "version": 1, "request_started_monotonic_sec": now,
            "deadline_monotonic_sec": now + 4.0,
        }
        payload = b"QuPRS-Rust-Supervisor-Admit-v1\n" + json.dumps(req).encode()
        p.stdin.write(payload)
        p.stdin.close()
        p.stdin = None
        deadline = time.monotonic() + 6
        while not pidfile.is_file() and p.poll() is None:
            assert time.monotonic() < deadline, "fake solver never launched"
            time.sleep(.02)
        assert pidfile.is_file(), "fake solver was not admitted"
        child = int(pidfile.read_text())
        if stop == "sigterm":
            # Keep a short observation window for the real Supervisor sampler.
            time.sleep(.3)
            p.send_signal(signal.SIGTERM)
        output, error = p.communicate(timeout=12)
        assert p.returncode == (0 if stop == "deadline" else 143), (
            p.returncode, error.decode(errors="replace")
        )
        assert b"equivalent" not in output.lower()
        if stop == "deadline":
            result = json.loads(output)
            assert result["result"]["status"] == "Timeout"
        else:
            assert output == b"", "cancellation cannot publish science"
        # Inspect via the same native libproc API rather than ps textual output.
        from QuPRS.interface import rust_macos_process as native
        state = native._info(child)
        assert state is None or state[1] == 5, (
            "detached solver survived Supervisor.cleanup", child, state
        )
    finally:
        if child is not None:
            try: os.kill(child, signal.SIGKILL)
            except ProcessLookupError: pass
        if p.poll() is None:
            p.kill()
            p.wait(timeout=4)


@pytest.mark.skipif(os.name != "posix", reason="POSIX cancellation contract")
@pytest.mark.parametrize("signal_number,exit_code", [
    (signal.SIGINT, 130), (signal.SIGTERM, 143),
])
def test_supervisor_signal_before_parent_admission_is_cli_typed(signal_number, exit_code):
    """Cancellation before admission must be 130/143, not resource exit 125.

    There is no Worker to reap in this phase. The process must not publish a
    scientific verdict or treat SIGTERM as a resource/supervision failure.
    """
    supervisor = Path(rust_isolation.__file__).with_name("rust_supervisor.py")
    env = os.environ.copy()
    env["QUPRS_RUST_SUPERVISOR_PARENT_PID"] = str(os.getpid())
    process = subprocess.Popen(
        [sys.executable, "-I", str(supervisor)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env, start_new_session=True,
    )
    try:
        # On the target CI interpreters only stdlib is imported before the
        # Supervisor starts reading the inherited parent-admission pipe.
        time.sleep(.6)
        assert process.poll() is None, "Supervisor exited before admission"
        process.send_signal(signal_number)
        stdout, stderr = process.communicate(timeout=6)
        assert process.returncode == exit_code, stderr.decode(errors="replace")
        assert stdout == b"", "early cancellation published scientific output"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=4)

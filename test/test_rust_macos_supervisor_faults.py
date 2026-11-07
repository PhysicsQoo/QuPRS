"""End-to-end native macOS Python Supervisor fault contracts.

A private test harness swaps only the Worker subprocess with a deterministic
detached-Solver fixture; the actual Supervisor.run/IPC/deadline/cleanup execute.
No test-only switch or fake solver is added to the production implementation.
"""
import json
import os
from pathlib import Path
import signal
import select
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
# Publish the PID only after the writer is closed; file existence must be
# a complete PID witness even when the host polls concurrently.
temp_pidfile = sys.argv[1] + '.tmp'
with open(temp_pidfile, 'w') as f:
    f.write(str(child.pid))
os.replace(temp_pidfile, sys.argv[1])
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


_SUPERVISOR_ARMED_BEFORE_ADMISSION = """
import importlib.util,os,sys
path=os.environ['QUPRS_TEST_SUPERVISOR_PATH']
spec=importlib.util.spec_from_file_location('quprs_armed_supervisor',path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
try:
    # Test the actual private supervisor after its control handlers are armed.
    # A cold interpreter cannot translate signals received during import.
    mod._set_supervisor_controls()
    os.write(2, b'SUPERVISOR_CONTROLS_READY\\n')
    sys.exit(mod.run())
except mod.SupervisorInterrupted as exc:
    sys.exit(128 + exc.signum)
"""


@pytest.mark.skipif(os.name != "posix", reason="POSIX cancellation contract")
@pytest.mark.parametrize("signal_number,exit_code", [
    (signal.SIGINT, 130), (signal.SIGTERM, 143),
])
def test_supervisor_signal_after_controls_before_parent_admission_is_cli_typed(signal_number, exit_code):
    """Cancellation before admission must be 130/143, not resource exit 125.

    There is no Worker to reap in this phase. The process must not publish a
    scientific verdict or treat SIGTERM as a resource/supervision failure.
    """
    supervisor = Path(rust_isolation.__file__).with_name("rust_supervisor.py")
    env = os.environ.copy()
    env["QUPRS_RUST_SUPERVISOR_PARENT_PID"] = str(os.getpid())
    env["QUPRS_TEST_SUPERVISOR_PATH"] = str(supervisor)
    process = subprocess.Popen(
        [sys.executable, "-I", "-c", _SUPERVISOR_ARMED_BEFORE_ADMISSION],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env, start_new_session=True,
    )
    try:
        # A fixed sleep can send SIGTERM during CPython import, before any
        # Python handler exists. Require a real controls-armed readiness witness
        # while the Supervisor is still blocked on parent admission instead.
        readable, _, _ = select.select([process.stderr], [], [], 6)
        assert readable, "Supervisor never armed its cancellation controls"
        marker = process.stderr.readline()
        assert marker == b"SUPERVISOR_CONTROLS_READY\\n", marker
        assert process.poll() is None, "Supervisor exited before admission"
        process.send_signal(signal_number)
        stdout, stderr = process.communicate(timeout=6)
        assert process.returncode == exit_code, stderr.decode(errors="replace")
        assert stdout == b"", "early cancellation published scientific output"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=4)

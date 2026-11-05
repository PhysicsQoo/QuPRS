"""Private, standalone POSIX supervisor for isolated QuPRS Rust verification.

Launched as a script (not -m) so this supervisor imports only Python's stdlib
until the worker is created. On Linux this *separate* process becomes a child
subreaper; the embedding Python application is never modified.
"""
from __future__ import annotations

import ctypes
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

_PROTOCOL_VERSION = 1
_MAX_REQUEST_BYTES = 64 * 1024 * 1024
_MAX_RESULT_BYTES = 16 * 1024 * 1024


class SupervisorResourceError(RuntimeError):
    pass


class SupervisorInterrupted(RuntimeError):
    pass


def _interrupt_supervisor(signum, frame):
    raise SupervisorInterrupted(f"signal {signum} canceled isolated worker")


def _set_supervisor_controls() -> None:
    signal.signal(signal.SIGTERM, _interrupt_supervisor)
    signal.signal(signal.SIGINT, _interrupt_supervisor)
    if sys.platform != 'linux':
        return
    libc = ctypes.CDLL(None, use_errno=True)
    # PR_SET_CHILD_SUBREAPER = 36, PR_SET_PDEATHSIG = 1.
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER')
    if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_PDEATHSIG')
    expected_parent = int(os.environ['QUPRS_RUST_SUPERVISOR_PARENT_PID'])
    if os.getppid() != expected_parent:
        raise SupervisorResourceError('supervisor parent disappeared before admission')


def _children() -> list[int]:
    if sys.platform != 'linux':
        return []
    try:
        entries = os.listdir('/proc')
    except OSError as exc:
        raise SupervisorResourceError('cannot inspect procfs children') from exc
    own = os.getpid()
    children = []
    for name in entries:
        if not name.isdecimal():
            continue
        try:
            with open('/proc/%s/stat' % name, encoding='ascii') as f:
                tail = f.read().rsplit(') ', 1)[1].split()
            ppid = int(tail[1])
            pid = int(name)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        except (OSError, IndexError, ValueError) as exc:
            raise SupervisorResourceError('invalid procfs process tree snapshot') from exc
        if ppid == own:
            children.append(pid)
    return children


def _cleanup_adopted_children() -> None:
    if sys.platform != 'linux':
        return
    for _ in range(100):
        children = _children()
        if not children:
            return
        for pid in children:
            # Verify parent before signalling to reduce PID-reuse ambiguity.
            try:
                with open('/proc/%d/stat' % pid, encoding='ascii') as f:
                    parent = int(f.read().rsplit(') ', 1)[1].split()[1])
                if parent == os.getpid():
                    os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, FileNotFoundError):
                pass
        while True:
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break
            if pid <= 0:
                break
        time.sleep(.01)
    raise SupervisorResourceError('orphaned solver descendant survived cleanup')


def _module():
    path = Path(__file__).with_name('rust_isolation.py')
    spec = importlib.util.spec_from_file_location('_quprs_private_worker_io', path)
    if spec is None or spec.loader is None:
        raise SupervisorResourceError('cannot load private worker I/O')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _reply(payload: dict) -> None:
    output = json.dumps(payload, allow_nan=False, separators=(',', ':')).encode()
    if len(output) > _MAX_RESULT_BYTES:
        raise SupervisorResourceError('supervisor reply exceeds limit')
    sys.stdout.buffer.write(output)
    sys.stdout.buffer.flush()


def run() -> int:
    _set_supervisor_controls()
    iolib = _module()
    raw = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
    if len(raw) > _MAX_REQUEST_BYTES:
        raise SupervisorResourceError('request exceeds IPC limit')
    req = json.loads(raw)
    if not isinstance(req, dict) or req.get('version') != _PROTOCOL_VERSION:
        raise SupervisorResourceError('bad IPC protocol version')
    deadline = req.get('deadline_monotonic_sec')
    if (isinstance(deadline, bool) or not isinstance(deadline, (int, float))
        or not math.isfinite(deadline)):
        raise SupervisorResourceError('missing monotonic deadline')
    started = req.get('request_started_monotonic_sec')
    if not isinstance(started, (int, float)) or isinstance(started, bool):
        raise SupervisorResourceError('missing request start time')
    if deadline <= time.monotonic():
        _reply({'version': 1, 'ok': True, 'result': {
            'status': 'Timeout', 'verification_time_sec': time.monotonic() - started}})
        return 0
    p = subprocess.Popen(
        [sys.executable, '-m', 'QuPRS.interface.rust_isolation'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        close_fds=True, start_new_session=True, bufsize=0,
    )
    timed_out = False
    output = None
    worker_error = None
    try:
        try:
            stdout, stderr = iolib._bounded_exchange(p, raw, deadline)
            output = iolib._parse_worker_response(stdout, stderr, p.returncode)
        except iolib._WorkerDeadlineExceeded:
            timed_out = True
        except Exception as exc:
            worker_error = exc
    finally:
        cleanup_error = None
        try:
            iolib._stop_worker(p)
        except Exception as exc:
            cleanup_error = exc
        try:
            _cleanup_adopted_children()
        except Exception as exc:
            if cleanup_error is None:
                cleanup_error = exc
        if cleanup_error is not None:
            raise SupervisorResourceError('worker or descendant cleanup failed') from cleanup_error
    if worker_error is not None:
        if isinstance(worker_error, (ValueError, TypeError)):
            _reply({'version': 1, 'ok': False,
                    'error_type': type(worker_error).__name__,
                    'message': str(worker_error)[:512]})
            return 0
        raise SupervisorResourceError('worker protocol or solver execution failed') from worker_error
    if timed_out:
        _reply({'version': 1, 'ok': True, 'result': {
            'status': 'Timeout', 'verification_time_sec': time.monotonic() - started}})
        return 0
    _reply({'version': 1, 'ok': True, 'result': output})
    return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except Exception as exc:
        print('Rust supervisor failed: %s: %s' %
              (type(exc).__name__, str(exc)[:512]), file=sys.stderr)
        sys.exit(125)

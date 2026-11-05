"""macOS native process-tree supervision for the opt-in Rust Python Worker.

Match the Rust CLI's observable cleanup contract, not Linux cgroup guarantees.
Fast daemonization, forced Supervisor SIGKILL and identity-check-to-kill races
remain beyond the guarantees of user-space process observation.
"""
from __future__ import annotations

import ctypes
import errno
import os
import signal
import threading
import time

class ProcessTreeError(RuntimeError):
    pass

# Public XNU proc_info.h (PROC_PIDTBSDINFO=3), param.h (MAXCOMLEN=16).
class _BSDInfo(ctypes.Structure):
    _fields_ = [(x, ctypes.c_uint32) for x in (
        "flags status xstatus pid ppid uid gid ruid rgid svuid svgid reserved"
    ).split()] + [
        ("comm", ctypes.c_char * 16), ("name", ctypes.c_char * 32),
    ] + [(x, ctypes.c_uint32) for x in (
        "nfiles pgid pjobc tdev tpgid"
    ).split()] + [
        ("nice", ctypes.c_int32), ("start_sec", ctypes.c_uint64),
        ("start_usec", ctypes.c_uint64),
    ]

_MAX_PIDS = 128
_LIB = None

def _lib():
    global _LIB
    if _LIB is None:
        try:
            lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
            lib.proc_pidinfo.argtypes = [
                ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                ctypes.c_void_p, ctypes.c_int,
            ]
            lib.proc_pidinfo.restype = ctypes.c_int
            lib.proc_listchildpids.argtypes = [
                ctypes.c_int, ctypes.c_void_p, ctypes.c_int,
            ]
            lib.proc_listchildpids.restype = ctypes.c_int
            _LIB = lib
        except (OSError, AttributeError) as exc:
            raise ProcessTreeError("macOS libproc unavailable") from exc
    return _LIB

def _info(pid):
    data = _BSDInfo()
    ctypes.set_errno(0)
    size = _lib().proc_pidinfo(pid, 3, 0, ctypes.byref(data), ctypes.sizeof(data))
    if size == 0 and ctypes.get_errno() == errno.ESRCH:
        return None
    if size != ctypes.sizeof(data) or data.pid != pid:
        raise ProcessTreeError("cannot certify native PID identity")
    if not data.start_sec or data.start_usec >= 1000000:
        raise ProcessTreeError("invalid native process birth")
    return (int(data.ppid), int(data.status), int(data.uid),
            int(data.start_sec), int(data.start_usec))

def _children(pid):
    buf = (ctypes.c_int * (_MAX_PIDS + 1))()
    count = _lib().proc_listchildpids(pid, ctypes.byref(buf), ctypes.sizeof(buf))
    if count < 0 or count >= len(buf):
        raise ProcessTreeError("macOS child enumeration failed or exceeded limit")
    result = [int(buf[i]) for i in range(count) if buf[i] > 1]
    if len(result) != len(set(result)):
        raise ProcessTreeError("duplicate macOS child PID")
    return result

def _birth(info):
    return info[2:]  # uid, second, microsecond

def _alive(info):
    return info is not None and info[1] != 5  # XNU SZOMB

class DarwinProcessTree:
    def __init__(self, worker_pid):
        root = _info(worker_pid)
        if worker_pid <= 1 or not _alive(root) or root[2] != os.geteuid():
            raise ProcessTreeError("Worker birth/ownership admission failed")
        self.worker_pid = worker_pid
        self._owned = {worker_pid: _birth(root)}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._error = None
        self._cleanup_deadline = None

    def _sample(self):
        with self._lock:
            queue = list(self._owned.items())
            index = 0
            while index < len(queue):
                parent, token = queue[index]
                index += 1
                current = _info(parent)
                if not _alive(current):
                    continue
                if _birth(current) != token:
                    raise ProcessTreeError("tracked parent PID reused")
                for child in _children(parent):
                    child_info = _info(child)
                    if not _alive(child_info) or child_info[0] != parent:
                        continue
                    if child_info[2] != os.geteuid():
                        raise ProcessTreeError("owned Solver changed user")
                    birth = _birth(child_info)
                    if child in self._owned and self._owned[child] != birth:
                        raise ProcessTreeError("tracked Solver PID reused")
                    if child not in self._owned:
                        if len(self._owned) >= _MAX_PIDS:
                            raise ProcessTreeError("too many owned Solver descendants")
                        self._owned[child] = birth
                        queue.append((child, birth))

    def _poll(self):
        while not self._stop.wait(.06):
            try:
                self._sample()
            except Exception as exc:
                self._error = exc
                self._stop.set()
                return

    def start(self):
        self._sample()
        self._thread = threading.Thread(
            target=self._poll, name="quprs-darwin-process-tree", daemon=True
        )
        self._thread.start()

    def kill_observed_descendants(self):
        # One bounded clock for scanner shutdown, final observation and kills.
        self._cleanup_deadline = time.monotonic() + 2.
        errors = []
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=max(0, self._cleanup_deadline-time.monotonic()))
            if self._thread.is_alive():
                errors.append("scanner not stopped")
        if self._error is not None:
            errors.append("descendant monitoring failed")
        if not self._thread or not self._thread.is_alive():
            try:
                self._sample()
            except Exception:
                errors.append("final process observation failed")
        with self._lock:
            owned = list(self._owned.items())
        # Even if the scanner errored, still kill all already observed children.
        for pid, token in reversed(owned):
            if pid in (self.worker_pid, os.getpid()):
                continue
            if time.monotonic() >= self._cleanup_deadline:
                errors.append("cleanup deadline exceeded")
                break
            try:
                before = _info(pid)
                if not _alive(before):
                    continue
                if _birth(before) != token:
                    errors.append("owned PID identity changed")
                    continue
                again = _info(pid)
                if not _alive(again):
                    continue
                if _birth(again) != token:
                    errors.append("owned PID changed before signal")
                    continue
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except (ProcessTreeError, OSError):
                errors.append("known descendant could not be terminated")
        if errors:
            raise ProcessTreeError("; ".join(dict.fromkeys(errors)))

    def verify_stopped(self):
        if self._cleanup_deadline is None:
            raise ProcessTreeError("cleanup was not attempted")
        with self._lock:
            owned = dict(self._owned)
        while True:
            living = []
            for pid, token in owned.items():
                if pid == self.worker_pid:
                    continue
                info = _info(pid)
                if _alive(info):
                    if _birth(info) != token:
                        raise ProcessTreeError("descendant PID reused during verification")
                    living.append(pid)
            if not living:
                return
            rem = self._cleanup_deadline-time.monotonic()
            if rem <= 0:
                raise ProcessTreeError("macOS Solver descendant survived cleanup")
            time.sleep(min(rem, .02))

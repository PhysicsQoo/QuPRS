"""macOS process-tree tracking for the private Rust API supervisor.

Mirrors the Rust CLI's native ps-based ancestry cleanup contract while the
worker runs. Unlike Linux cgroup v2, Darwin cannot guarantee containment of
rapidly detached or reparented processes, nor recovery after supervisor SIGKILL.
This helper runs ONLY inside a dedicated safe_mode=True supervisor.
"""
from __future__ import annotations

import os
import signal
import subprocess
import threading
import time


class ProcessTreeError(RuntimeError):
    """A macOS process-tree observation or cleanup could not be certified."""


# The CLI uses ps PID/PPID enumeration on macOS. Add a process birth witness
# before signalling, to avoid killing a PID that was recycled after sampling.
# 'lstart' is a second-resolution identity hint, not a kernel process handle.
_PS_COLUMNS = "pid=,ppid=,stat=,lstart="
_TERMINAL_STATES = frozenset({"Z", "X"})


def _snapshot() -> dict[int, tuple[int, str, str]]:
    environment = os.environ.copy()
    environment["LC_ALL"] = "C"
    try:
        result = subprocess.run(
            ["/bin/ps", "-axo", _PS_COLUMNS], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=2, check=False, env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProcessTreeError("cannot enumerate macOS process tree") from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise ProcessTreeError("macOS ps process enumeration failed")
    rows: dict[int, tuple[int, str, str]] = {}
    for line in result.stdout.splitlines():
        fields = line.split()
        # pid, ppid, stat, five lstart tokens (weekday, month, day, time, year).
        if len(fields) != 8:
            continue
        pid_text, ppid_text, state = fields[:3]
        if not pid_text.isascii() or not pid_text.isdecimal():
            continue
        if not ppid_text.isascii() or not ppid_text.isdecimal():
            continue
        if not state or not state[0].isalpha():
            continue
        pid, ppid = int(pid_text), int(ppid_text)
        if pid in rows:
            raise ProcessTreeError("duplicate PID in macOS process enumeration")
        rows[pid] = (ppid, state[0], " ".join(fields[3:]))
    if not rows:
        raise ProcessTreeError("macOS ps returned no usable PID records")
    return rows


class DarwinProcessTree:
    """Track observed descendants of one worker with bounded ps snapshots.

    It is deliberately not a sandbox or a guarantee against a process that
    forks, daemonizes, and re-parents between successive observations.
    """

    def __init__(self, worker_pid: int):
        if not isinstance(worker_pid, int) or worker_pid <= 1:
            raise ProcessTreeError("invalid supervised worker PID")
        self.worker_pid = worker_pid
        records = _snapshot()
        root = records.get(worker_pid)
        if root is None or root[1] in _TERMINAL_STATES:
            raise ProcessTreeError("worker vanished before process-tree admission")
        self._owned: dict[int, str] = {worker_pid: root[2]}
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._error: Exception | None = None
        self._thread: threading.Thread | None = None

    def _observe(self, records: dict[int, tuple[int, str, str]]) -> None:
        with self._lock:
            # Only follow the original worker and already verified descendants.
            # A re-used PID is NOT a new descendant to be signalled.
            verified = {
                pid for pid, birth in self._owned.items()
                if pid in records and records[pid][2] == birth
                and records[pid][1] not in _TERMINAL_STATES
            }
            current = set(verified)
            changed = True
            while changed:
                changed = False
                for pid, (ppid, state, birth) in records.items():
                    if ppid not in current or pid == self.worker_pid:
                        continue
                    if pid in self._owned and self._owned[pid] != birth:
                        raise ProcessTreeError("macOS owned descendant PID was reused")
                    if pid not in self._owned:
                        self._owned[pid] = birth
                    if pid not in current and state not in _TERMINAL_STATES:
                        current.add(pid)
                        changed = True

    def _poll(self) -> None:
        while not self._stop.wait(0.12):
            try:
                self._observe(_snapshot())
            except Exception as exc:
                with self._lock:
                    self._error = exc
                self._stop.set()
                return

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._poll, name="quprs-macos-worker-tree", daemon=True,
        )
        self._thread.start()

    def _finish_sampling(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
            if self._thread.is_alive():
                raise ProcessTreeError("macOS descendant sampler did not terminate")
        with self._lock:
            error = self._error
        if error is not None:
            raise ProcessTreeError("macOS descendant monitoring failed") from error
        # The final snapshot must precede the worker-group kill: the kernel
        # may reparent a detached Solver immediately when its parent exits.
        self._observe(_snapshot())

    def kill_observed_descendants(self) -> None:
        self._finish_sampling()
        records = _snapshot()
        # A descendant may have changed process group; kill only owned PIDs
        # with a matching birth witness, and never signal our supervisor.
        with self._lock:
            identities = list(self._owned.items())
        for pid, birth in reversed(identities):
            if pid == self.worker_pid or pid == os.getpid():
                continue
            row = records.get(pid)
            if row is None or row[2] != birth or row[1] in _TERMINAL_STATES:
                continue
            # Recheck immediately before kill to reduce PID reuse races.
            fresh = _snapshot().get(pid)
            if fresh is None or fresh[2] != birth or fresh[1] in _TERMINAL_STATES:
                continue
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                continue
            except PermissionError as exc:
                raise ProcessTreeError("cannot kill observed macOS Solver descendant") from exc

    def verify_stopped(self) -> None:
        # Stop only when each observed descendant disappears, becomes zombie,
        # or has a different process birth token (PID was reused).
        deadline = time.monotonic() + 2
        with self._lock:
            identities = dict(self._owned)
        while True:
            records = _snapshot()
            live = [
                pid for pid, birth in identities.items()
                if pid != self.worker_pid and pid in records
                and records[pid][2] == birth
                and records[pid][1] not in _TERMINAL_STATES
            ]
            if not live:
                return
            if time.monotonic() >= deadline:
                raise ProcessTreeError("observed macOS Solver descendant survived cleanup")
            time.sleep(.02)

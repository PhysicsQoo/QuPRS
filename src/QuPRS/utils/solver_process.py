"""Cross-platform bounded execution of an external WMC solver.

Capture into temporary files instead of pipes so a stalled solver cannot block
on a full stdout/stderr pipe. Only a bounded excerpt is loaded into memory.
A private process group/session permits cancellation of its descendants.
"""
from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass

SOLVER_ENV_LOCK = threading.RLock()
# Serializes QuPRS-managed solver resource resolution and Rust environment
# overrides until the Rust FFI accepts an explicit per-invocation path.
MAX_STREAM_BYTES = 1024 * 1024
_POLL_SECONDS = 0.02


class SolverTimeout(TimeoutError):
    """The external solver exceeded its remaining monotonic deadline."""


class SolverOutputLimitError(RuntimeError):
    """The solver exceeded the diagnostic-output limit."""


class SolverProcessError(RuntimeError):
    """The solver could not be started or supervised."""


@dataclass(frozen=True)
class SolverOutput:
    returncode: int
    stdout: str
    stderr: str


def _terminate_tree(proc: subprocess.Popen) -> None:
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif os.name == "nt":
        # Terminate descendants before the direct child where supported.
        try:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True, timeout=5, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        proc.kill()
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired as exc:
        raise SolverProcessError("Failed to reap solver process") from exc


def run(command: list[str], timeout: float) -> SolverOutput:
    """Execute one solver invocation with a subprocess-specific deadline.

    A whole-verification hard deadline additionally requires supervising any
    in-process reduction work. This function only promises child supervision.
    """
    if timeout <= 0:
        raise SolverTimeout("SolverTimeout: no time remaining before spawn")
    flags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        if os.name == "nt" else 0
    )
    deadline = time.monotonic() + timeout
    with tempfile.TemporaryFile(mode="w+b") as stdout_file, tempfile.TemporaryFile(
        mode="w+b"
    ) as stderr_file:
        try:
            proc = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=(os.name == "posix"),
                creationflags=flags,
            )
        except OSError as exc:
            raise SolverProcessError(f"SolverUnavailable: {exc}") from exc

        try:
            while True:
                if (
                    os.fstat(stdout_file.fileno()).st_size > MAX_STREAM_BYTES
                    or os.fstat(stderr_file.fileno()).st_size > MAX_STREAM_BYTES
                ):
                    raise SolverOutputLimitError(
                        "SolverOutputLimit: diagnostic stream exceeds 1 MiB"
                    )
                if time.monotonic() >= deadline:
                    raise SolverTimeout("SolverTimeout: subprocess deadline exceeded")
                code = proc.poll()
                if code is not None:
                    break
                time.sleep(min(_POLL_SECONDS, max(0, deadline - time.monotonic())))

            if (
                os.fstat(stdout_file.fileno()).st_size > MAX_STREAM_BYTES
                or os.fstat(stderr_file.fileno()).st_size > MAX_STREAM_BYTES
            ):
                raise SolverOutputLimitError(
                    "SolverOutputLimit: diagnostic stream exceeds 1 MiB"
                )
            stdout_file.seek(0)
            stderr_file.seek(0)
            return SolverOutput(
                returncode=code,
                stdout=stdout_file.read(MAX_STREAM_BYTES).decode("utf-8", "replace"),
                stderr=stderr_file.read(MAX_STREAM_BYTES).decode("utf-8", "replace"),
            )
        finally:
            # Child exit does not imply its descendants are gone. Always reap
            # and terminate members left in the private group/session.
            _terminate_tree(proc)

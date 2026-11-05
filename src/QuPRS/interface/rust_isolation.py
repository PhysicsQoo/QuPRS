"""Experimental process isolation for the existing Rust safe_mode Python API.

This module is deliberately private. The parent supervises one fresh Python
interpreter which imports and invokes the same PyO3 extension as the direct
Rust path. It is not the standalone Rust CLI and does not change the public
check_equivalence signature.

The first-stage supervisor enforces a monotonic worker deadline and bounded
IPC on POSIX. It does NOT yet certify detached solver-grandchild cleanup,
physical-memory caps, or preemption of parent-side Qiskit serialization.
"""
from __future__ import annotations

import json
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time

import psutil

_MAX_REQUEST_BYTES = 64 * 1024 * 1024
_MAX_RESULT_BYTES = 16 * 1024 * 1024
_MAX_DIAGNOSTIC_BYTES = 1024 * 1024
_CHUNK_BYTES = 64 * 1024
_PROTOCOL_VERSION = 1


class RustWorkerError(RuntimeError):
    """The isolated worker or its protocol could not be trusted."""


class _WorkerDeadlineExceeded(TimeoutError):
    pass


def _close_selector_stream(selector, stream):
    try:
        selector.unregister(stream)
    except KeyError:
        pass
    stream.close()


def _bounded_exchange(process, payload: bytes, deadline: float) -> tuple[bytes, bytes]:
    """Exchange one complete JSON request and response with bounded pipes.

    POSIX nonblocking selectors prevent a blocked stdin writer or excessive
    stdout/stderr from escaping the parent deadline. Both output EOFs are
    required before a result is accepted.
    """
    results = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": _MAX_RESULT_BYTES, "stderr": _MAX_DIAGNOSTIC_BYTES}
    sent = 0

    with selectors.DefaultSelector() as selector:
        for stream, events, kind in (
            (process.stdin, selectors.EVENT_WRITE, "stdin"),
            (process.stdout, selectors.EVENT_READ, "stdout"),
            (process.stderr, selectors.EVENT_READ, "stderr"),
        ):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, events, kind)

        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _WorkerDeadlineExceeded("isolated Rust worker timed out")
            events = selector.select(remaining)
            if not events:
                raise _WorkerDeadlineExceeded("isolated Rust worker timed out")
            for key, _ in events:
                stream, kind = key.fileobj, key.data
                if kind == "stdin":
                    if sent == len(payload):
                        _close_selector_stream(selector, stream)
                        continue
                    try:
                        written = os.write(stream.fileno(), payload[sent:sent + _CHUNK_BYTES])
                    except BrokenPipeError as exc:
                        raise RustWorkerError("worker closed its input prematurely") from exc
                    if written == 0:
                        raise RustWorkerError("worker did not consume input")
                    sent += written
                    if sent == len(payload):
                        _close_selector_stream(selector, stream)
                else:
                    chunk = os.read(stream.fileno(), _CHUNK_BYTES)
                    if not chunk:
                        _close_selector_stream(selector, stream)
                        continue
                    target = results[kind]
                    if len(target) + len(chunk) > limits[kind]:
                        raise RustWorkerError(f"worker {kind} exceeded IPC output limit")
                    target.extend(chunk)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _WorkerDeadlineExceeded("isolated Rust worker timed out")
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise _WorkerDeadlineExceeded("isolated Rust worker timed out") from exc

    return bytes(results["stdout"]), bytes(results["stderr"])


def _stop_worker(process):
    """Reap the worker and kill visible descendants, including detached groups.

    Capturing descendants BEFORE killing the parent closes the common
    detached-session escape; it is not a kernel-enforced containment boundary.
    A dedicated subreaper/cgroup supervisor is needed to guarantee no escaped
    descendants after arbitrary daemonization, races or supervisor SIGKILL.
    """
    survivors = []
    try:
        try:
            root = psutil.Process(process.pid)
            descendants = root.children(recursive=True)
        except psutil.NoSuchProcess:
            descendants = []
        except (psutil.AccessDenied, psutil.Error) as exc:
            raise RustWorkerError("cannot enumerate isolated worker descendants") from exc

        # Kill recorded descendants first. psutil.Process identity includes
        # creation time, preventing PID reuse from targeting unrelated work.
        for child in reversed(descendants):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
            except (psutil.AccessDenied, psutil.Error) as exc:
                raise RustWorkerError("cannot terminate isolated worker descendant") from exc
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired as exc:
            raise RustWorkerError("isolated worker could not be reaped") from exc

        # A finished direct child does not establish reaping of grandchildren.
        # Zombies are already dead; live survivors are a resource failure.
        for child in descendants:
            try:
                if child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
                    survivors.append(child.pid)
            except psutil.NoSuchProcess:
                pass
        if survivors:
            raise RustWorkerError("isolated worker descendants survived termination")
    finally:
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None and not stream.closed:
                stream.close()


def _parse_worker_response(stdout: bytes, stderr: bytes, returncode: int) -> dict:
    """Return a complete verified worker result, never a partial verdict."""
    if returncode != 0:
        message = stderr.decode("utf-8", "replace").strip()
        raise RustWorkerError(
            f"isolated Rust worker exited with {returncode}: {message[:512]}"
        )
    try:
        response = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RustWorkerError("invalid isolated Rust result envelope") from exc
    if not isinstance(response, dict) or response.get("version") != _PROTOCOL_VERSION:
        raise RustWorkerError("isolated Rust protocol version mismatch")
    if response.get("ok") is False:
        message = str(response.get("message", "worker failed"))[:512]
        if response.get("error_type") == "ValueError":
            raise ValueError(message)
        if response.get("error_type") == "TypeError":
            raise TypeError(message)
        raise RustWorkerError(f"isolated Rust worker error: {message}")
    result = response.get("result")
    if response.get("ok") is not True or not isinstance(result, dict):
        raise RustWorkerError("isolated Rust worker returned no complete result")
    status = result.get("status")
    if status not in {
        "Equivalent", "Equivalent (Up to Global Phase)", "Not Equivalent",
        "Unknown", "Timeout", "MemoryOut",
    }:
        raise RustWorkerError("isolated Rust worker returned an invalid status")
    if status not in {"Timeout", "MemoryOut"} and not {
        "qubits", "gates1", "gates2", "stats", "final_ps",
    }.issubset(result):
        raise RustWorkerError("isolated Rust result is missing required fields")
    return result


def run_isolated(
    circuit1: str,
    circuit2: str,
    options: dict,
    request_started: float,
    request_deadline: float,
) -> dict:
    """Run the Rust FFI in a separate process without changing public options."""
    if os.name != "posix":
        raise RustWorkerError("experimental Rust isolation requires a POSIX host")
    # A virtual-address cap must never be misrepresented as a physical RSS
    # limit. cgroup delegation/admission is a separate integration gate.
    if "QUPRS_ISOLATED_MAX_MEMORY_MIB" in os.environ:
        raise RustWorkerError(
            "physical-memory cap requires an unavailable delegated cgroup supervisor"
        )

    request = {
        "version": _PROTOCOL_VERSION,
        "circuit1": circuit1,
        "circuit2": circuit2,
        "options": options,
    }
    payload = json.dumps(request, allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > _MAX_REQUEST_BYTES:
        raise RustWorkerError("isolated Rust request exceeds IPC input limit")
    if time.monotonic() >= request_deadline:
        return {
            "status": "Timeout",
            "verification_time_sec": time.monotonic() - request_started,
        }

    # Parent owns the temporary namespace even if the child is SIGKILL'ed.
    with tempfile.TemporaryDirectory(prefix="quprs-rust-worker-") as temporary:
        environment = os.environ.copy()
        environment["TMPDIR"] = temporary
        environment["TMP"] = temporary
        environment["TEMP"] = temporary
        worker_bootstrap = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "_rust_worker_bootstrap.py"
        )
        worker = subprocess.Popen(
            [sys.executable, worker_bootstrap],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            start_new_session=True,
            close_fds=True,
            bufsize=0,
        )
        timed_out = False
        try:
            try:
                stdout, stderr = _bounded_exchange(worker, payload, request_deadline)
            except _WorkerDeadlineExceeded:
                timed_out = True
                stdout, stderr = b"", b""
            if timed_out:
                return {
                    "status": "Timeout",
                    "verification_time_sec": time.monotonic() - request_started,
                }
            return _parse_worker_response(stdout, stderr, worker.returncode)
        finally:
            _stop_worker(worker)


def _worker_main() -> int:
    """Private child entry point; stdout contains exactly one JSON envelope."""
    try:
        data = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
        if len(data) > _MAX_REQUEST_BYTES:
            raise ValueError("worker request exceeds input limit")
        request = json.loads(data)
        if not isinstance(request, dict) or request.get("version") != _PROTOCOL_VERSION:
            raise ValueError("worker protocol version mismatch")
        circuit1, circuit2 = request["circuit1"], request["circuit2"]
        options = request["options"]
        if not isinstance(circuit1, str) or not isinstance(circuit2, str):
            raise TypeError("worker requires two QASM strings or paths")
        if not isinstance(options, dict):
            raise TypeError("worker options must be a dictionary")
        tool_name = options["tool_name"]
        if not isinstance(tool_name, str):
            raise TypeError("invalid solver name")

        # Solver extraction, environment override and its lifetime are
        # child-local. No shared parent environment or Python global lock.
        from QuPRS import _pathsum_rust
        from QuPRS.utils import WMC, get_ganak_path

        key = f"QUPRS_{tool_name.upper()}_PATH"
        resource = get_ganak_path(verify=False) if tool_name == "ganak" else WMC(tool_name)
        with resource as executable:
            os.environ[key] = str(executable)
            result = _pathsum_rust.check_equivalence(
                circuit1, circuit2,
                method=options["method"],
                strategy=options["strategy"],
                tool_name=tool_name,
                timeout=options["timeout"],
                safe_mode=False,  # worker already runs in its own process
                wmc_phase_tolerance=options["wmc_phase_tolerance"],
                approximate_distance_tolerance=options["approximate_distance_tolerance"],
                rr_tolerance=options["rr_tolerance"],
                phase_tolerance=options["phase_tolerance"],
                gpmc_precision_digits=options["gpmc_precision_digits"],
            )
        envelope = {"version": _PROTOCOL_VERSION, "ok": True, "result": result}
    except Exception as exc:
        envelope = {
            "version": _PROTOCOL_VERSION,
            "ok": False,
            "error_type": type(exc).__name__,
            "message": str(exc)[:512],
        }

    try:
        output = json.dumps(envelope, allow_nan=False, separators=(",", ":")).encode("utf-8")
        if len(output) > _MAX_RESULT_BYTES:
            raise RustWorkerError("worker result exceeds IPC output limit")
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.flush()
        return 0
    except Exception as exc:
        print(f"isolated Rust worker output failure: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_worker_main())

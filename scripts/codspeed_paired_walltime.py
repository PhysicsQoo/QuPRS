"""Source-pinned, warm-process CodSpeed WallTime harness for PR #131.

The parent benchmark uses the same harness for each source revision. A worker
runs inside that revision's own virtualenv and persists across measurements;
thus Python interpreter startup/import is excluded from the timed RPC. The
full public QuPRS verification (including external Solver waits) is measured.

This is an exploratory shared-runner experiment, not an official Macro Runner.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any


# id -> (QASM fixture, reduction strategy, input reversal, chosen solver)
CASES = {
    "vqe4_gpmc": ("vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", False, "gpmc"),
    "graphstate16_gpmc": ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "naive", False, "gpmc"),
    "grover4_gpmc": ("grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", True, "gpmc"),
    "qft16_gpmc": ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", True, "gpmc"),
    "graphstate16_ganak": ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "naive", False, "ganak"),
    "qft16_ganak": ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", True, "ganak"),
    "qaoa7_gpmc": ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", False, "gpmc"),
}
POSITIVE_CASES = set(CASES) - {"graphstate16_gpmc", "graphstate16_ganak"}
# The historical source-pinned Graphstate16 pair has a tiny exact-source
# discrepancy: a tolerant positive is not equivalent to a strict source proof.


def verify_one(root: Path, case: str) -> dict[str, Any]:
    from QuPRS import check_equivalence  # loaded in the version-specific worker

    filename, strategy, reverse, solver = CASES[case]
    left = root / "benchmarks" / "MQTBench" / filename
    right = root / "benchmarks" / "MQTBench" / "h,ry,rz,cx" / filename
    if not left.is_file() or not right.is_file():
        raise FileNotFoundError(f"QASM fixture not found: {left}, {right}")
    if reverse:
        left, right = right, left
    result = check_equivalence(
        str(left), str(right), method="hybrid", strategy=strategy,
        tool_name=solver, backend="rust", timeout=120,
    )
    invoked = getattr(result, "wmc_solver_invoked", None)
    if invoked is None:
        # Older main/dev results can expose only the solver-time field.
        # Keep the lower-confidence inference clearly labeled in metadata.
        if hasattr(result, "tool_time"):
            invoked_label = "true" if result.tool_time is not None else "false"
            stage_provenance = "legacy_tool_time_inference"
        else:
            invoked_label = "unavailable"
            stage_provenance = "unavailable"
    else:
        invoked_label = "true" if bool(invoked) else "false"
        stage_provenance = "explicit_solver_invoked"
    return {
        "case": case,
        "verdict": str(result.equivalent),
        "solver_invoked": invoked_label,
        "stage_provenance": stage_provenance,
        "stage": "wmc" if invoked_label == "true" else (
            "rr" if invoked_label == "false" else "unavailable"
        ),
        "rr_approximate": str(getattr(result, "rr_approximate", "unavailable")),
    }


def _recv_json_line(conn: socket.socket) -> dict[str, Any]:
    with conn.makefile("rb") as inp:
        line = inp.readline(16385)
    if not line or len(line) >= 16385:
        raise RuntimeError("Worker protocol returned no valid response")
    response = json.loads(line)
    if not isinstance(response, dict):
        raise TypeError("Worker reply must be a JSON object")
    return response


def _serve(root: Path, path: Path) -> None:
    # The socket carries protocol bytes; solver/library stdout cannot corrupt
    # response framing. Private local directory is provided by the CI fixture.
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing socket {path}")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        os.chmod(path, 0o600)
        server.listen(1)
        try:
            while True:
                conn, _ = server.accept()
                with conn:
                    try:
                        with conn.makefile("rb") as inp:
                            message = json.loads(inp.readline(16385))
                        if message.get("command") == "stop":
                            reply = {"status": "stopped"}
                            conn.sendall((json.dumps(reply) + "\n").encode())
                            return
                        if message.get("command") == "ping":
                            reply = {"status": "ready", "pid": os.getpid()}
                        elif message.get("command") == "verify":
                            reply = {"status": "ok", **verify_one(root, message["case"]), "pid": os.getpid()}
                        else:
                            raise ValueError("Unsupported benchmark worker command")
                    except Exception as exc:
                        reply = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
                    conn.sendall((json.dumps(reply, sort_keys=True) + "\n").encode())
        finally:
            path.unlink(missing_ok=True)


class PersistentWorker:
    """Worker ownership, bounded RPC, and process-tree cleanup outside timing."""

    def __init__(self, python: Path, script: Path, root: Path, socket_path: Path):
        self.python = python
        self.script = script
        self.root = root
        self.socket_path = socket_path
        self.process: subprocess.Popen | None = None
        self._stderr_handle = None
        self._pid: int | None = None

    def start(self) -> "PersistentWorker":
        if self.process is not None:
            raise RuntimeError("Worker was already started")
        self.socket_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._stderr_handle = (self.socket_path.parent / "worker.stderr.log").open("ab")
        self.process = subprocess.Popen(
            [str(self.python), str(self.script), "--worker", str(self.root), str(self.socket_path)],
            cwd=self.root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=self._stderr_handle,
            start_new_session=True,
        )
        deadline = time.monotonic() + 90  # readiness guard, NOT a performance measurement
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"Persistent worker exited early: {self.process.returncode}")
            if self.socket_path.is_socket():
                try:
                    self._pid = int(self.request("ping", timeout=2)["pid"])
                    return self
                except (OSError, TimeoutError):
                    # Socket bind and listen are not a single atomic event.
                    pass
            time.sleep(0.05)
        raise TimeoutError("Persistent worker readiness timed out")

    def request(self, command: str, case: str | None = None, *, timeout: float = 140) -> dict[str, Any]:
        request = {"command": command}
        if case is not None:
            request["case"] = case
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(timeout)  # default exceeds verifier's 120s deadline
            conn.connect(str(self.socket_path))
            conn.sendall((json.dumps(request) + "\n").encode())
            # Half-close the request, allowing a single reliable line reply.
            conn.shutdown(socket.SHUT_WR)
            answer = _recv_json_line(conn)
        if answer.get("status") == "error":
            raise RuntimeError(answer.get("error", "Worker failed without details"))
        return answer

    def verify(self, case: str) -> dict[str, Any]:
        if case not in CASES:
            raise KeyError(case)
        response = self.request("verify", case)
        if response.get("status") != "ok" or response.get("case") != case:
            raise AssertionError("Worker response belongs to a different invocation")
        if response.get("pid") != self._pid:
            raise AssertionError("Worker unexpectedly restarted during measurement")
        return response

    def close(self) -> None:
        process = self.process
        if process is None:
            return
        try:
            if process.poll() is None:
                try:
                    self.request("stop", timeout=2)
                except (OSError, RuntimeError, TimeoutError, ValueError):
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Kill the spawned session, not only its Python parent;
                    # worker may have launched an external GPMC/Ganak solver.
                    if os.name == "posix":
                        import signal
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    else:
                        process.kill()
                    process.wait(timeout=5)
        finally:
            self.socket_path.unlink(missing_ok=True)
            self.process = None
            if self._stderr_handle:
                self._stderr_handle.close()
                self._stderr_handle = None

    def __enter__(self) -> "PersistentWorker":
        try:
            return self.start()
        except Exception:
            self.close()
            raise

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("root", type=Path)
    parser.add_argument("socket", type=Path)
    args = parser.parse_args()
    if not args.worker:
        parser.error("This helper starts only in worker mode")
    _serve(args.root.resolve(), args.socket)


if __name__ == "__main__":
    main()

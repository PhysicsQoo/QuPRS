#!/usr/bin/env python3
"""QOO-156: true static Ganak --mode=6 cancellation, no solver modifications.

Run a small *bounded* sequence of versioned QASM examples. Observe a real
pinned Ganak ELF counting process (not its --version preflight), SIGSTOP that
PID, and require the outer Rust CLI timeout to kill it without orphans.
An unobserved process is NOT_ADMITTED, never silently counted as PASS.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

import psutil
from QuPRS.utils import WMC

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("vqe4", "vqe_nativegates_ibm_qiskit_opt0_4.qasm"),
    ("qaoa7", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm"),
    ("graphstate16", "graphstate_nativegates_ibm_qiskit_opt0_16.qasm"),
    ("qft16", "qft_nativegates_ibm_qiskit_opt0_16.qasm"),
)
PINNED_GANAK_SHA256 = "934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def still_active(pid: int, start_time: float) -> bool:
    try:
        p = psutil.Process(pid)
        if abs(p.create_time() - start_time) > 0.1:
            return False
        return p.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
        # AccessDenied is NOT proof that the process has terminated.
        return True


def actual_ganak(cli: psutil.Process, binary: Path):
    """Only accept Ganak --mode=6 with CLI ancestry, matching ELF and PID."""
    try:
        descendants = cli.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return None
    for process in descendants:
        try:
            command = process.cmdline()
            if "--mode=6" not in command:
                continue
            if Path(process.exe()).resolve() != binary:
                continue
            return process, command
        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
            continue
    return None


def bounded_run(cli_binary: Path, binary: Path, name: str, source: Path, workspace: Path, seconds: int) -> dict:
    left = workspace / f"{name}-left.qasm"
    right = workspace / f"{name}-right.qasm"
    original = source.read_bytes()
    left.write_bytes(original)
    # Difference is explicit and source-backed; force a genuine miter WMC
    # instead of a trivial all-gates-identical shortcut.
    right.write_bytes(original.rstrip() + b"\nx q[0];\n")
    cmd = [
        str(cli_binary), str(left), str(right),
        "--method", "wmc-only", "--tool", "ganak",
        "--strategy", "proportional", "--timeout", str(seconds),
        "--quiet",
    ]
    env = os.environ.copy()
    env["QUPRS_GANAK_PATH"] = str(binary)
    # The signed/static Ganak ELF cannot load LD_PRELOAD and is never replaced.
    env.pop("QOO156_GANAK_PAUSE_SO", None)
    env.pop("QOO156_PAUSE_REAL_GANAK", None)
    env.pop("LD_PRELOAD", None)
    process = subprocess.Popen(
        cmd, env=env, cwd=workspace, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,
    )
    cli_proc = psutil.Process(process.pid)
    found = None
    found_args = None
    pid = None
    creation = None
    observed_stopped = False
    start = time.monotonic()
    limit = start + seconds + 3.0
    stdout = stderr = ""
    try:
        while time.monotonic() < limit:
            observed = actual_ganak(cli_proc, binary)
            if observed is not None:
                candidate, args = observed
                try:
                    creation = candidate.create_time()
                    pid = candidate.pid
                    # SIGSTOP via external test process. No executable patch,
                    # wrapper, LD_PRELOAD, or Ganak argument changes.
                    os.kill(pid, signal.SIGSTOP)
                    # Re-read identity and state after signaling. A fast
                    # solver might have exited between discovery and kill.
                    if still_active(pid, creation):
                        for _ in range(20):
                            try:
                                if psutil.Process(pid).status() == psutil.STATUS_STOPPED:
                                    observed_stopped = True
                                    break
                            except psutil.Error:
                                break
                            time.sleep(0.001)
                    if observed_stopped:
                        found, found_args = pid, args
                        break
                except (psutil.Error, ProcessLookupError, PermissionError):
                    pass
            if process.poll() is not None:
                break
            time.sleep(0.001)
        try:
            stdout, stderr = process.communicate(timeout=seconds + 5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=5)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)

    if found is not None and creation is not None:
        for _ in range(150):
            if not still_active(found, creation):
                break
            time.sleep(0.02)
    leaked = found is not None and creation is not None and still_active(found, creation)
    if leaked and found is not None:
        # Never leave a stopped Ganak process behind even when the program
        # has a cleanup defect. The original verdict remains NOT_ADMITTED.
        try:
            if abs(psutil.Process(found).create_time() - creation) < 0.1:
                os.kill(found, signal.SIGKILL)
        except (psutil.NoSuchProcess, ProcessLookupError):
            pass

    timeout = process.returncode == 124 and stdout.strip() == "Timeout"
    admitted = bool(observed_stopped and found is not None and timeout and not leaked)
    return {
        "case": name,
        "source_path": str(source.relative_to(ROOT)),
        "source_sha256": sha256(source),
        "left_sha256": sha256(left),
        "right_sha256": sha256(right),
        "solver_sha256": sha256(binary),
        "solver_pid": found,
        "solver_start_time": creation if found is not None else None,
        "observed_args": found_args,
        "mode6_stopped": observed_stopped,
        "timeout_exit_124": timeout,
        "cli_returncode": process.returncode,
        "live_orphan_after_cli": leaked,
        "duration_seconds": round(time.monotonic() - start, 3),
        "stdout_tail": stdout[-1000:],
        "stderr_tail": stderr[-2000:],
        "classification": "REAL_GANAK_CLEANUP_PASS" if admitted else "NOT_ADMITTED",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cli", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=10)
    args = p.parse_args()
    if not (2 <= args.timeout <= 20):
        p.error("timeout must stay bounded between 2 and 20 seconds")
    cli = args.cli.resolve(strict=True)
    args.evidence.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack, tempfile.TemporaryDirectory(prefix="qoo156-ganak-mode6-") as temp:
        real = Path(stack.enter_context(WMC("ganak"))).resolve(strict=True)
        fingerprint = sha256(real)
        if fingerprint != PINNED_GANAK_SHA256:
            raise RuntimeError("Ganak ELF hash differs from pinned Linux x86_64 distribution")
        attempts = []
        for case, filename in CASES:
            fixture = ROOT / "benchmarks/MQTBench" / filename
            if not fixture.is_file():
                raise FileNotFoundError(fixture)
            record = bounded_run(cli, real, case, fixture, Path(temp), args.timeout)
            attempts.append(record)
            print("QOO156_REAL_GANAK " + json.dumps({
                "case": case, "classification": record["classification"],
                "solver_pid": record["solver_pid"],
                "timeout": record["timeout_exit_124"],
                "elapsed_s": record["duration_seconds"],
            }, sort_keys=True), flush=True)
            if record["classification"] == "REAL_GANAK_CLEANUP_PASS":
                break

        summary = {
            "classification": "PASS" if any(
                a["classification"] == "REAL_GANAK_CLEANUP_PASS" for a in attempts
            ) else "NOT_ADMITTED",
            "solver": "ganak",
            "original_solver_sha256": fingerprint,
            "method": "wmc-only",
            "solver_args": ["--mode=6"],
            "source": "versioned MQTBench QASM with explicit extra X on same qubits",
            "attempts": attempts,
        }
        (args.evidence / "ganak-mode6-live-cancel.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n"
        )
        print("QOO156_REAL_GANAK_CERTIFICATE=" + summary["classification"], flush=True)
        return 0 if summary["classification"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())

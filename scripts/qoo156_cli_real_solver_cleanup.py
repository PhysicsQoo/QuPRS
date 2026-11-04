#!/usr/bin/env python3
"""QOO-156 experimental end-to-end real GPMC/Ganak worker-tree cancellation.

A live solver binary must be observed (not merely an override or mock).
A real solver is deliberately SIGSTOP'd, making cleanup observable. Results
are source-pinned observational evidence, not scientific WMC verdicts.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack

import psutil
from QuPRS.utils import WMC


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def is_owned(pid: int, cli_pid: int) -> bool:
    try:
        process = psutil.Process(pid)
        return any(parent.pid == cli_pid for parent in process.parents())
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def alive_after_timeout(pid: int, started: float | None) -> bool:
    try:
        process = psutil.Process(pid)
        if started is not None and abs(process.create_time() - started) > 0.1:
            return False  # recycled PID is not the tested process
        return process.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return False


def run_probe(cli: Path, name: str, real: Path, fixture: Path, folder: Path) -> dict:
    pid_file = folder / f"{name}-solver-pid.txt"
    wrapper_log = folder / f"{name}-wrapper.log"
    env = os.environ.copy()
    env["QUPRS_GPMC_PATH"] = str(real) if name != "gpmc" else str(folder / "gpmc-stop-wrapper")
    env["QUPRS_GANAK_PATH"] = str(real) if name == "ganak" else env.get("QUPRS_GANAK_PATH", "")
    if name == "gpmc":
        env["QOO156_REAL_GPMC"] = str(real)
        env["QOO156_PID_FILE"] = str(pid_file)
        env["QOO156_WRAPPER_LOG"] = str(wrapper_log)
    if name == "ganak" and os.getenv("QOO156_GANAK_PAUSE_SO"):
        # A test-only constructor sees --mode=6 after exec of the real
        # signed/pinned Ganak ELF. Its --version preflight stays untouched.
        library = str(Path(os.environ["QOO156_GANAK_PAUSE_SO"]).resolve())
        env["LD_PRELOAD"] = library + (":" + env["LD_PRELOAD"] if env.get("LD_PRELOAD") else "")
        env["QOO156_PAUSE_REAL_GANAK"] = "1"
    # Both files are intentionally nonidentical; WMC-only must reach the
    # concrete solver rather than a trivial identical-circuit shortcut.
    right = folder / "other.qasm"
    command = [
        str(cli), str(fixture), str(right),
        "--method", "wmc-only", "--tool", name,
        "--timeout", "8", "--quiet",
    ]
    process = subprocess.Popen(
        command, env=env, cwd=folder,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,
    )
    stopped_pid = None
    started = None
    observed_mode = False
    found_exe = None
    limit = time.monotonic() + 12
    stdout = stderr = ""
    try:
        while time.monotonic() < limit:
            if name == "gpmc" and pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    p = psutil.Process(pid)
                    found_exe = p.exe()
                    if p.exe() == str(real.resolve()):
                        stopped_pid, started, observed_mode = pid, p.create_time(), True
                        break
                except (ValueError, psutil.Error, FileNotFoundError):
                    pass
            if name == "ganak":
                # Never confuse Ganak's --version preflight with its actual
                # --mode=6 counting subprocess.
                for p in psutil.process_iter(["pid", "exe", "cmdline", "create_time"]):
                    try:
                        args = p.info["cmdline"] or []
                        if (
                            p.info["exe"] == str(real.resolve())
                            and "--mode=6" in args
                            and is_owned(p.pid, process.pid)
                        ):
                            os.kill(p.pid, signal.SIGSTOP)
                            stopped_pid, started, observed_mode = p.pid, p.create_time(), True
                            break
                    except (psutil.Error, ProcessLookupError, PermissionError):
                        continue
                if stopped_pid is not None:
                    break
            if process.poll() is not None:
                break
            time.sleep(0.002)
        try:
            stdout, stderr = process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            # Fail closed and kill the entire outer test group, never leave
            # a stuck experiment behind.
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=3)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)

    if stopped_pid is not None:
        for _ in range(150):
            if not alive_after_timeout(stopped_pid, started):
                break
            time.sleep(0.02)
    leaked = stopped_pid is not None and alive_after_timeout(stopped_pid, started)
    timeout_observed = (
        process.returncode == 124
        or "timeout" in (stdout + stderr).lower()
    )
    admitted = observed_mode and timeout_observed and not leaked
    return {
        "solver": name,
        "sha256": digest(real),
        "real_executable": str(real),
        "source_fixture_sha256": digest(fixture),
        "solver_pid": stopped_pid,
        "wrapper_log": wrapper_log.read_text() if wrapper_log.exists() else None,
        "pid_file_value": pid_file.read_text() if pid_file.exists() else None,
        "observed_process_exe": found_exe,
        "solver_mode_invoked": observed_mode,
        "timeout_observed": timeout_observed,
        "leftover_active_process": leaked,
        "exit_code": process.returncode,
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-2000:],
        "classification": "REAL_SOLVER_CLEANUP_PASS" if admitted else "NOT_ADMITTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="qoo156-real-solvers-") as temp, ExitStack() as stack:
        folder = Path(temp)
        left = folder / "left.qasm"
        right = folder / "other.qasm"
        # One-qubit nonidentical Clifford fixtures keep CNF generation cheap,
        # so a deadline can be attributed to the real external solver stage.
        left.write_text('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\nh q[0];\n')
        right.write_text('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\nx q[0];\n')
        solvers = {
            name: Path(stack.enter_context(WMC(name))).resolve()
            for name in ("gpmc", "ganak")
        }
        # A wrapper can select GPMC's real binary. Ganak cannot be wrapped:
        # the distribution independently validates its exact ELF identity.
        wrapper = folder / "gpmc-stop-wrapper"
        wrapper.write_text(
            "#!/bin/sh\n"
            'echo entered > "$QOO156_WRAPPER_LOG"\n'
            '"$QOO156_REAL_GPMC" "$@" &\n'
            "child=$!\n"
            'echo "child=$child" >> "$QOO156_WRAPPER_LOG"\n'
            # Command::spawn can return before the shell-background child
            # execs its real ELF. Wait for /proc/<pid>/exe to match the
            # verified actual solver, rather than SIGSTOP'ing /usr/bin/dash.
            'i=0\n'
            'while [ "$i" -lt 1000 ]; do\n'
            '  exe=$(readlink "/proc/$child/exe" 2>/dev/null || true)\n'
            '  if [ "$exe" = "$QOO156_REAL_GPMC" ]; then\n'
            '    if kill -STOP "$child" 2>/dev/null; then\n'
            '      echo "$child" > "$QOO156_PID_FILE"\n'
            '      echo "real_elf_stopped=$exe" >> "$QOO156_WRAPPER_LOG"\n'
            '    fi\n'
            '    break\n'
            '  fi\n'
            '  kill -0 "$child" 2>/dev/null || break\n'
            '  i=$((i + 1))\n'
            '  sleep 0.001\n'
            'done\n'
            'wait "$child"\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
        results = [
            run_probe(arguments.cli.resolve(), name, real, left, folder)
            for name, real in solvers.items()
        ]
        source = {"checks": results, "classification":
            "PASS" if all(row["classification"] == "REAL_SOLVER_CLEANUP_PASS"
                          for row in results) else "NOT_ADMITTED"}
        evidence = arguments.evidence / "real-solver-cleanup.json"
        evidence.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
        for row in results:
            print(f"QOO156_REAL_SOLVER_CLEANUP {row['solver']} {row['classification']}", flush=True)
        print(f"QOO156_SOLVER_CLEANUP_OVERALL {source['classification']}", flush=True)
        return 0 if source["classification"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Repeat the existing bounded resource observer on one explicitly identified host.

Run from an installed QuPRS environment on a dedicated, otherwise idle host.
This is observational data, not a CI performance gate or a strict RSS upper bound.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def command_output(*argv: str) -> str:
    result = subprocess.run(
        argv, cwd=ROOT, text=True, capture_output=True, check=False,
    )
    return (result.stdout or result.stderr).strip()[:6000]


def provenance(host_id: str) -> dict:
    return {
        "host_id": host_id,
        "git_sha": command_output("git", "rev-parse", "HEAD"),
        "git_tree": command_output("git", "rev-parse", "HEAD^{tree}"),
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": command_output("lscpu"),
        "kernel": command_output("uname", "-a"),
        "rustc": command_output("rustc", "--version"),
        "image_os": os.getenv("ImageOS"),
        "image_version": os.getenv("ImageVersion"),
        "sample_observer": "sampled live process-tree RSS, not exact instantaneous peak",
        "metric_separation": "CodSpeed heap Memory is not process-tree RSS",
    }


def _valid_solver_time(value: object) -> bool:
    """None is a valid Hybrid RR-only path; numeric values must be finite."""
    return (
        value is None or (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value >= 0
        )
    )


def summarize(trials: list[dict], expected_repeats: int, *,
              expected_case: str | None = None,
              expected_solver: str | None = None,
              expected_backend: str | None = None) -> dict:
    """Validate end-to-end Hybrid resources independently of optional WMC.

    Numeric solver_time is *not* proof of native model-counting execve.
    Solver-only claims require a separately witnessed native execution.
    """
    data = [x["report"] for x in trials if not x["warmup"]]
    if len(data) != expected_repeats:
        return {"status": "INCONCLUSIVE", "reason": "missing repetitions"}
    if any(
        not isinstance(t.get("report"), dict)
        or t.get("exit_code", 0) != 0
        or t.get("outer_timed_out") is True
        or t.get("cleanup_needed") is True
        or t.get("cleanup_error") is not None
        or t["report"].get("complete") is not True
        or t["report"].get("resource_limit_status") is not None
        or t["report"].get("exit_code") != 0
        or t["report"].get("verdict", {}).get("accepted_positive") is not True
        or not _valid_solver_time(
            t["report"].get("verdict", {}).get("solver_time", "MISSING")
        )
        for t in trials
    ):
        return {"status": "INCONCLUSIVE", "reason": "invalid solver or resource verdict"}
    if expected_case is not None or expected_solver is not None or expected_backend is not None:
        for trial in trials:
            r = trial["report"]
            verdict = r["verdict"]
            if (r.get("case", {}).get("case") != expected_case
                or r.get("tool_name") != expected_solver
                or r.get("backend") != expected_backend
                or verdict.get("tool_name") != expected_solver
                or verdict.get("backend") != expected_backend):
                return {"status": "INCONCLUSIVE", "reason": "case/solver/backend mismatch"}
            hashes = r.get("input_sha256")
            if not isinstance(hashes, dict) or any(
                not isinstance(hashes.get(which), str)
                or len(hashes[which]) != 64
                or any(ch not in "0123456789abcdef" for ch in hashes[which])
                for which in ("source", "transpiled")
            ):
                return {"status": "INCONCLUSIVE", "reason": "missing input checksum"}
        first_hashes = trials[0]["report"]["input_sha256"]
        if any(t["report"]["input_sha256"] != first_hashes for t in trials):
            return {"status": "INCONCLUSIVE", "reason": "source input changed between trials"}
    times = [r["elapsed_seconds"] for r in data]
    rss = [r["sampled_peak_tree_rss_mib"] for r in data]
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0
           for v in times + rss):
        return {"status": "INCONCLUSIVE", "reason": "invalid time or sampled RSS"}
    solver_times = [t["report"]["verdict"]["solver_time"] for t in trials]
    numeric_count = sum(v is not None for v in solver_times)
    # This is an *observed metadata* classification, not an oracle that
    # Hybrid must invoke WMC. The same case may take different valid paths.
    execution_path = (
        "RR_ONLY_REPORTED" if numeric_count == 0
        else "WMC_TIME_REPORTED" if numeric_count == len(solver_times)
        else "MIXED_HYBRID_PATHS"
    )
    return {
        "status": "COMPLETE", "n": len(data),
        "execution_path": execution_path,
        "numeric_solver_time_trials": numeric_count,
        "total_trials_including_warmups": len(solver_times),
        "native_solver_execution_verified": False,
        "solver_only_performance_certified": False,
        "walltime_median_seconds": statistics.median(times),
        "walltime_mad_seconds": statistics.median(
            abs(t - statistics.median(times)) for t in times
        ),
        "sampled_tree_rss_median_mib": statistics.median(rss),
        "sampled_tree_rss_max_observed_mib": max(rss),
        "note": "Do not compare runs from different CPUs/hosts/toolchains.",
    }


def binary_hash(solver: str) -> str:
    from QuPRS.utils import WMC

    with WMC(solver) as binary:
        return hashlib.sha256(Path(binary).read_bytes()).hexdigest()


def _enable_linux_subreaper() -> None:
    """Adopt orphaned solver descendants that escape a worker's process group."""
    if sys.platform != "linux":
        raise RuntimeError("Fixed-host process-tree containment requires Linux")
    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    # Linux prctl(PR_SET_CHILD_SUBREAPER, 1): children orphaned by nested
    # Python/Rust/solver supervisors become children of this trial harness.
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _reap_adopted_children() -> None:
    """Reap detached direct children only after Popen.wait() reaps the worker."""
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            return


def run_bounded_trial(command: list[str], timeout_seconds: float) -> dict:
    """Bound a Linux worker and clean descendants across session/PGID changes.

    Production GPMC/Ganak supervisors create their own sessions or process
    groups, so signaling only the outer worker group is insufficient.
    Linux subreaping retains adopted descendants under this supervisor.
    """
    import signal
    import tempfile
    import psutil

    if timeout_seconds <= 0:
        raise ValueError("Trial timeout must be positive")
    _enable_linux_subreaper()

    supervisor = psutil.Process(os.getpid())
    if supervisor.children(recursive=True):
        raise RuntimeError("Trial supervisor must not have pre-existing children")

    with tempfile.TemporaryFile(mode="w+t") as stdout_file, \
            tempfile.TemporaryFile(mode="w+t") as stderr_file:
        process = subprocess.Popen(
            command, cwd=ROOT, stdout=stdout_file, stderr=stderr_file,
            start_new_session=True,
        )
        timed_out = False
        cleanup_needed = False
        cleanup_error = None

        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            # Terminate the outer group, then iteratively terminate descendants
            # that moved to private sessions/groups. Subreaping keeps them
            # discoverable even when intermediate Python workers have exited.
            if timed_out:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                    cleanup_needed = True
                except ProcessLookupError:
                    pass
                except OSError as exc:
                    cleanup_error = f"outer_group_kill_failed_errno_{exc.errno}"

            settle_deadline = time.monotonic() + 5.0
            while True:
                try:
                    if process.poll() is None:
                        process.kill()
                        cleanup_needed = True
                    process.wait(timeout=max(0.01, settle_deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    cleanup_error = "worker_not_reaped"
                except ProcessLookupError:
                    pass

                _reap_adopted_children()
                survivors = []
                for child in supervisor.children(recursive=True):
                    try:
                        if child.status() != psutil.STATUS_ZOMBIE:
                            survivors.append(child)
                    except psutil.NoSuchProcess:
                        continue
                    except psutil.Error as exc:
                        cleanup_error = f"descendant_inspection_failed_{type(exc).__name__}"
                if not survivors and process.poll() is not None:
                    break

                cleanup_needed = True
                for child in survivors:
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                    except psutil.Error as exc:
                        cleanup_error = f"descendant_kill_failed_{type(exc).__name__}"
                if time.monotonic() >= settle_deadline:
                    cleanup_error = cleanup_error or "descendants_remain_after_cleanup"
                    break
                time.sleep(0.02)

            _reap_adopted_children()

        def tail(stream) -> str:
            stream.seek(0, os.SEEK_END)
            stream.seek(max(0, stream.tell() - 600))
            return stream.read()

        return {
            "exit_code": None if timed_out else process.returncode,
            "outer_timed_out": timed_out,
            "cleanup_needed": cleanup_needed,
            "cleanup_error": cleanup_error,
            "stdout_tail": tail(stdout_file),
            "stderr_tail": tail(stderr_file),
        }


def comparison_schedule(cases: tuple[str, ...], solvers: tuple[str, ...],
                        backends: tuple[str, ...], *,
                        warmups: int, repeats: int) -> list[dict]:
    """Counterbalance solver/backend/case order on one dedicated host.

    Four measured rounds use forward, reverse, reverse, forward (ABBA-like).
    An optional warmup block precedes these measured rounds. This reduces
    ordering bias but does not remove environmental drift or host contention.
    """
    if not cases or not solvers or not backends or warmups < 0:
        raise ValueError("Nonempty selectors and nonnegative warmups required")
    if repeats < 4 or repeats % 4 != 0:
        raise ValueError("Measured repeats must be a positive multiple of four")
    cells = [(case, solver, backend) for case in cases
             for solver in solvers for backend in backends]
    plan = []
    for round_id in range(warmups + repeats):
        warmup = round_id < warmups
        repetition = None if warmup else round_id - warmups
        reverse = not warmup and repetition % 4 in (1, 2)
        for case, solver, backend in (cells[::-1] if reverse else cells):
            plan.append({
                "trial_index": len(plan), "round": round_id,
                "repetition": repetition, "warmup": warmup,
                "case": case, "solver": solver, "backend": backend,
            })
    return plan


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host-id", required=True,
                   help="Stable user-defined physical host identifier, not a CI runner label")
    p.add_argument("--case", action="append",
                   choices=("grover4", "qaoa7", "qft16"), required=True)
    p.add_argument("--solver", action="append", choices=("gpmc", "ganak"),
                   required=True)
    p.add_argument("--backend", action="append", choices=("python", "rust"),
                   required=True)
    p.add_argument("--warmups", type=int, default=1)
    p.add_argument("--repeats", type=int, default=4)
    p.add_argument("--walltime", type=int, default=90)
    p.add_argument("--solver-timeout", type=int, default=45)
    p.add_argument("--rss-limit-mib", type=int, default=3072)
    p.add_argument("--sample-ms", type=int, default=50)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    if a.repeats < 4 or a.repeats % 4 != 0 or a.warmups < 0 or a.walltime <= a.solver_timeout:
        p.error("At least 4 repeats in multiples of 4, 0+ warmups; walltime > solver timeout")
    if a.output_dir.exists() and any(a.output_dir.iterdir()):
        p.error("Output directory must be absent or empty; never overwrite evidence")
    a.output_dir.mkdir(parents=True, exist_ok=True)
    evidence = {
        "provenance": provenance(a.host_id),
        "config": vars(a) | {"output_dir": str(a.output_dir)},
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "solvers": {name: binary_hash(name) for name in sorted(set(a.solver))},
        "groups": [],
    }
    cases = tuple(dict.fromkeys(a.case))
    solvers = tuple(dict.fromkeys(a.solver))
    backends = tuple(dict.fromkeys(a.backend))
    plan = comparison_schedule(
        cases, solvers, backends, warmups=a.warmups, repeats=a.repeats
    )
    evidence.update({
        "metric_scope": "same-fixed-host-hybrid-end-to-end",
        "ordering": "ABBA-like measured rounds, interleaved case/solver/backend",
        "expected_trials": len(plan), "plan": plan,
        "trials": [], "completed_trials": 0,
        "status": "RUNNING",
    })
    manifest = a.output_dir / "manifest.json"

    def checkpoint() -> None:
        temp = manifest.with_suffix(".json.tmp")
        temp.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n")
        temp.replace(manifest)

    checkpoint()
    groups = {(case, solver, backend): [] for case in cases
              for solver in solvers for backend in backends}
    stopped_reason = None
    for point in plan:
        case, solver, backend = point["case"], point["solver"], point["backend"]
        filename = (
            f"{point['trial_index']:03d}-{case}-{solver}-{backend}-"
            f"{'warmup' if point['warmup'] else 'sample'}.json"
        )
        path = a.output_dir / filename
        cmd = [
            sys.executable, str(ROOT / "scripts/profile_benchmark_resources.py"),
            "--case", case, "--tool-name", solver, "--backend", backend,
            "--walltime-seconds", str(a.walltime),
            "--solver-timeout-seconds", str(a.solver_timeout),
            "--memory-limit-mib", str(a.rss_limit_mib),
            "--sample-interval-ms", str(a.sample_ms),
            "--output", str(path.resolve()),
        ]
        try:
            outcome = run_bounded_trial(cmd, a.walltime + 30)
        except Exception as exc:
            stopped_reason = f"supervisor_error:{type(exc).__name__}:{exc}"
            outcome = {
                "exit_code": None, "outer_timed_out": False,
                "cleanup_needed": True, "cleanup_error": stopped_reason,
                "stdout_tail": "", "stderr_tail": "",
            }
        try:
            report = json.loads(path.read_text()) if path.is_file() else {}
        except (OSError, ValueError):
            report = {}
        trial = {
            **point, "exit_code": outcome["exit_code"],
            "outer_timed_out": outcome["outer_timed_out"],
            "cleanup_needed": outcome["cleanup_needed"],
            "cleanup_error": outcome["cleanup_error"],
            "report_path": filename, "report": report,
            "stdout_tail": outcome["stdout_tail"][-600:],
            "stderr_tail": outcome["stderr_tail"][-600:],
        }
        groups[(case, solver, backend)].append(trial)
        evidence["trials"].append(trial)
        evidence["completed_trials"] += 1
        checkpoint()
        print(json.dumps({
            "trial_index": point["trial_index"], "case": case,
            "solver": solver, "backend": backend,
            "warmup": point["warmup"], "complete": report.get("complete"),
            "cleanup_error": outcome["cleanup_error"],
        }, sort_keys=True), flush=True)
        if stopped_reason is not None:
            evidence["stopped_reason"] = stopped_reason
            break

    overall = evidence["completed_trials"] == len(plan)
    rows = []
    for (case, solver, backend), trials in groups.items():
        summary = summarize(
            trials, a.repeats,
            expected_case=case, expected_solver=solver,
            expected_backend=backend,
        )
        overall &= summary["status"] == "COMPLETE"
        evidence["groups"].append({
            "case": case, "solver": solver, "backend": backend,
            "summary": summary, "trials": trials,
        })
        rows.append({
            "case": case, "solver": solver, "backend": backend,
            "status": summary["status"],
            "execution_path": summary.get("execution_path"),
            "n": summary.get("n"),
            "walltime_median_seconds": summary.get("walltime_median_seconds"),
            "walltime_mad_seconds": summary.get("walltime_mad_seconds"),
            "sampled_tree_rss_median_mib": summary.get("sampled_tree_rss_median_mib"),
            "sampled_tree_rss_max_observed_mib": summary.get("sampled_tree_rss_max_observed_mib"),
            "solver_only_performance_certified": summary.get("solver_only_performance_certified"),
            "reason": summary.get("reason"),
        })
        print(json.dumps({
            "group": f"{case}-{solver}-{backend}", **summary,
        }, sort_keys=True), flush=True)
    with (a.output_dir / "summary.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    evidence["status"] = "COMPLETE" if overall else "INCONCLUSIVE"
    evidence["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    checkpoint()
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())

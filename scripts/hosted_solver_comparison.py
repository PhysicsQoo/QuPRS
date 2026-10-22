#!/usr/bin/env python3
"""One-job GPMC/Ganak comparison on a shared GitHub-hosted Linux runner.

Within-job exploratory data only, not a fixed physical-host claim and not a
regression gate. All examples, methods, strategies and QASM pairs are reused.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from fixed_host_resource_repeats import (
    ROOT, binary_hash, provenance, run_bounded_trial, summarize,
)

CASES = ("grover4", "qaoa7", "qft16", "vqe4", "graphstate16")
DEFAULT_CASES = ("grover4", "qaoa7", "qft16")
# Balanced counterpart order; reverse in middle repetitions (ABBA).
CELLS = (("gpmc", "python"), ("ganak", "python"),
         ("ganak", "rust"), ("gpmc", "rust"))


def schedule(cases: tuple[str, ...], *, warmups: int, repeats: int) -> list[dict]:
    """Interleave solvers/backends/circuits instead of running one group first."""
    if warmups < 1 or repeats < 4:
        raise ValueError("At least one warmup and four repeats are required")
    if not cases or len(cases) != len(set(cases)) or any(x not in CASES for x in cases):
        raise ValueError("Cases must be unique and drawn from the paper benchmark subset")
    out = []
    for round_id in range(warmups + repeats):
        warmup = round_id < warmups
        repetition = None if warmup else round_id - warmups
        # Within each four measured rounds: forward, reverse, reverse, forward.
        reverse = not warmup and repetition % 4 in (1, 2)
        for case in (cases[::-1] if reverse else cases):
            for solver, backend in (CELLS[::-1] if reverse else CELLS):
                out.append({
                    "trial_index": len(out),
                    "case": case, "solver": solver, "backend": backend,
                    "warmup": warmup, "repetition": repetition,
                    "round": round_id,
                })
    return out


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def environment() -> dict:
    result = provenance(os.environ.get("RUNNER_NAME", "github-hosted-unknown"))
    result.update({
        "scope": "github-hosted-within-job-exploratory",
        "runner_name": os.environ.get("RUNNER_NAME"),
        "runner_os": os.environ.get("RUNNER_OS"),
        "runner_arch": os.environ.get("RUNNER_ARCH"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "image_version": os.environ.get("ImageVersion"),
        "python_platform": platform.python_version(),
        "constraints": (
            "One runner VM per job; hardware and contention may differ in other "
            "jobs. No fixed physical host, precise peak RSS, or CodSpeed Memory claim."
        ),
    })
    try:
        import psutil
        result["cpu_affinity"] = psutil.Process().cpu_affinity()
        result["logical_cpu_count"] = psutil.cpu_count()
    except (ImportError, AttributeError, OSError):
        result["cpu_affinity"] = None
    return result


def write_json_atomic(path: Path, data: dict) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--case", action="append", choices=CASES)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=4)
    parser.add_argument("--walltime", type=int, default=90)
    parser.add_argument("--solver-timeout", type=int, default=45)
    parser.add_argument("--rss-limit-mib", type=int, default=3072)
    parser.add_argument("--sample-ms", type=int, default=50)
    parser.add_argument("--total-budget-minutes", type=int, default=130)
    args = parser.parse_args()

    if sys.platform != "linux":
        parser.error("This diagnostic uses the Linux subreaper supervisor")
    if args.walltime < 10 or args.solver_timeout < 1 or args.solver_timeout >= args.walltime:
        parser.error("Require walltime >= 10 and 0 < solver timeout < walltime")
    if args.rss_limit_mib < 64 or args.sample_ms < 10 or args.total_budget_minutes < 1:
        parser.error("Invalid resource or overall budget")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("Evidence directory must be new or empty; never overwrite trials")
    cases = tuple(args.case) if args.case is not None else DEFAULT_CASES
    try:
        plan = schedule(cases, warmups=args.warmups, repeats=args.repeats)
    except ValueError as exc:
        parser.error(str(exc))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    run = {
        "status": "RUNNING",
        "evidence_scope": "GITHUB_HOSTED_WITHIN_JOB_EXPLORATORY",
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provenance": environment(),
        "git_head": git_output("rev-parse", "HEAD"),
        "git_tree": git_output("rev-parse", "HEAD^{tree}"),
        "binary_sha256": {s: binary_hash(s) for s in ("gpmc", "ganak")},
        "config": {
            "cases": cases, "warmups": args.warmups, "repeats": args.repeats,
            "walltime_seconds": args.walltime,
            "solver_timeout_seconds": args.solver_timeout,
            "rss_limit_mib": args.rss_limit_mib,
            "sample_interval_ms": args.sample_ms,
            "total_budget_minutes": args.total_budget_minutes,
            "ordering": "ABBA-like reverse blocks over solver/backend and case",
        },
        "metric_contract": {
            "walltime": "monotonic worker/process execution including Popen; same-job only",
            "rss": "sampled live process-tree aggregate, not instantaneous physical peak",
            "codspeed_memory": "not measured or inferred",
        },
        "expected_trials": len(plan),
        "plan": plan,
        "completed_trials": 0,
        "groups": [],
        "trials": [],
    }
    manifest = args.output_dir / "manifest.json"
    write_json_atomic(manifest, run)
    groups = {(case, solver, backend): [] for case in cases
              for solver, backend in CELLS}
    started = time.monotonic()
    for point in plan:
        if time.monotonic() - started > args.total_budget_minutes * 60:
            run["stopped_reason"] = "overall_budget_exceeded"
            break
        filename = (
            f"{point['trial_index']:03d}-{point['case']}-{point['solver']}-"
            f"{point['backend']}-{'warmup' if point['warmup'] else 'sample'}.json"
        )
        path = args.output_dir / filename
        cmd = [
            sys.executable, str(ROOT / "scripts/profile_benchmark_resources.py"),
            "--case", point["case"], "--tool-name", point["solver"],
            "--backend", point["backend"],
            "--walltime-seconds", str(args.walltime),
            "--solver-timeout-seconds", str(args.solver_timeout),
            "--memory-limit-mib", str(args.rss_limit_mib),
            "--sample-interval-ms", str(args.sample_ms),
            "--output", str(path.resolve()),
        ]
        observation = {}
        failure = None
        try:
            observation = run_bounded_trial(cmd, args.walltime + 30)
        except Exception as exc:
            failure = f"supervisor_error:{type(exc).__name__}:{exc}"
        try:
            report = json.loads(path.read_text()) if path.is_file() else {}
        except (OSError, ValueError):
            report = {}
        trial = dict(point)
        trial.update({
            "exit_code": observation.get("exit_code"),
            "outer_timed_out": observation.get("outer_timed_out"),
            "cleanup_needed": observation.get("cleanup_needed"),
            "cleanup_error": observation.get("cleanup_error") or failure,
            "report_path": filename, "report": report,
            "stdout_tail": observation.get("stdout_tail", "")[-600:],
            "stderr_tail": observation.get("stderr_tail", "")[-600:],
        })
        groups[(point["case"], point["solver"], point["backend"])].append(trial)
        run["trials"].append(trial)
        run["completed_trials"] += 1
        write_json_atomic(manifest, run)
        print(json.dumps({
            "index": point["trial_index"], "case": point["case"],
            "solver": point["solver"], "backend": point["backend"],
            "warmup": point["warmup"], "accepted": report.get("complete") is True,
            "cleanup_error": trial["cleanup_error"],
        }, sort_keys=True), flush=True)
        if failure is not None:
            run["stopped_reason"] = failure
            break

    for (case, solver, backend), trials in groups.items():
        summary = summarize(
            trials, args.repeats, expected_case=case,
            expected_solver=solver, expected_backend=backend,
        )
        run["groups"].append({
            "case": case, "solver": solver, "backend": backend,
            "observed_trials": len(trials), "summary": summary,
        })
    run["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    run["status"] = (
        "COMPLETE" if run["completed_trials"] == len(plan)
        and all(g["summary"]["status"] == "COMPLETE" for g in run["groups"])
        else "INCONCLUSIVE"
    )
    write_json_atomic(manifest, run)
    rows = []
    for group in run["groups"]:
        s = group["summary"]
        rows.append({
            "case": group["case"], "solver": group["solver"],
            "backend": group["backend"], "status": s["status"],
            "n": s.get("n"), "walltime_median_seconds": s.get("walltime_median_seconds"),
            "walltime_mad_seconds": s.get("walltime_mad_seconds"),
            "sampled_tree_rss_median_mib": s.get("sampled_tree_rss_median_mib"),
            "sampled_tree_rss_max_observed_mib": s.get("sampled_tree_rss_max_observed_mib"),
            "reason": s.get("reason"),
        })
    with (args.output_dir / "summary.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({
        "scope": run["evidence_scope"], "status": run["status"],
        "complete_groups": sum(g["summary"]["status"] == "COMPLETE"
                               for g in run["groups"]),
        "expected_groups": len(run["groups"]),
        "completed_trials": run["completed_trials"],
        "expected_trials": len(plan),
    }, sort_keys=True))
    return 0 if run["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())

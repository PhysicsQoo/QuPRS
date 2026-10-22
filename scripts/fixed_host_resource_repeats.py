#!/usr/bin/env python3
"""Repeat the existing bounded resource observer on one explicitly identified host.

Run from an installed QuPRS environment on a dedicated, otherwise idle host.
This is observational data, not a CI performance gate or a strict RSS upper bound.
"""
from __future__ import annotations

import argparse
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


def summarize(trials: list[dict], expected_repeats: int) -> dict:
    """Accept complete, positive and actually WMC-invoking trials only."""
    data = [x["report"] for x in trials if not x["warmup"]]
    if len(data) != expected_repeats:
        return {"status": "INCONCLUSIVE", "reason": "missing repetitions"}
    if any(
        r.get("complete") is not True
        or r.get("resource_limit_status") is not None
        or r.get("exit_code") != 0
        or r.get("verdict", {}).get("accepted_positive") is not True
        or not isinstance(r.get("verdict", {}).get("solver_time"), (int, float))
        or not math.isfinite(r["verdict"]["solver_time"])
        or r["verdict"]["solver_time"] < 0
        for r in data
    ):
        return {"status": "INCONCLUSIVE", "reason": "invalid solver or resource verdict"}
    times = [r["elapsed_seconds"] for r in data]
    rss = [r["sampled_peak_tree_rss_mib"] for r in data]
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0
           for v in times + rss):
        return {"status": "INCONCLUSIVE", "reason": "invalid time or sampled RSS"}
    return {
        "status": "COMPLETE", "n": len(data),
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
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--walltime", type=int, default=90)
    p.add_argument("--solver-timeout", type=int, default=45)
    p.add_argument("--rss-limit-mib", type=int, default=3072)
    p.add_argument("--sample-ms", type=int, default=50)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    if a.repeats < 3 or a.warmups < 0 or a.walltime <= a.solver_timeout:
        p.error("At least 3 repeats and 0+ warmups; walltime > solver timeout")
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
    overall = True
    for case in dict.fromkeys(a.case):
        for solver in dict.fromkeys(a.solver):
            for backend in dict.fromkeys(a.backend):
                trials = []
                label = f"{case}-{solver}-{backend}"
                for index in range(a.warmups + a.repeats):
                    warmup = index < a.warmups
                    filename = f"{label}-{'warmup' if warmup else 'sample'}-{index}.json"
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
                    result = subprocess.run(cmd, cwd=ROOT, text=True,
                                            capture_output=True, check=False)
                    report = json.loads(path.read_text()) if path.is_file() else {}
                    trials.append({
                        "warmup": warmup, "exit_code": result.returncode,
                        "report_path": filename, "report": report,
                        "stdout_tail": result.stdout[-600:],
                        "stderr_tail": result.stderr[-600:],
                    })
                summary = summarize(trials, a.repeats)
                overall &= summary["status"] == "COMPLETE"
                evidence["groups"].append({
                    "case": case, "solver": solver, "backend": backend,
                    "summary": summary, "trials": trials,
                })
                print(json.dumps({"group": label, **summary}, sort_keys=True))
    evidence["status"] = "COMPLETE" if overall else "INCONCLUSIVE"
    (a.output_dir / "manifest.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n"
    )
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Actual Ganak 2.8.0 source-pinned TACAS 101-case verification (research only).

Original QuPRS v0.9.1 paper used GPMC. This tests MODERN Ganak against the
original paper binary labels, not an original Ganak reproduction or a numerical
arithmetic certificate. Solver timeout is not a verdict.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from scripts.tacas26_modern_full_101 import (
    ROOT, HISTORICAL_SHA, slice_corpus,
)
from scripts.tacas26_modern_calibration import binary, MARKER

SCHEMA = "tacas26-modern-ganak-101-binary-v1"
DISTANCE = "2e-5"
RR = "1e-10"
PHASE = "1e-8"


def execute_one(root, case, backend, solver_timeout, watchdog):
    if backend not in ("python", "rust"):
        raise ValueError("Unsupported modern Ganak backend")
    variant = "random_rotation" if case["kind"] == "negative" else "transpiled"
    command = [sys.executable, str(root / "benchmarks/codspeed/solver_case.py"),
               str(root), Path(case["a"]).name, "proportional", "ganak",
               backend, "0", variant, case["method"]]
    env = dict(os.environ)
    env.update(QUPRS_DIAGNOSTIC_DISTANCE_TOLERANCE=DISTANCE,
               QUPRS_DIAGNOSTIC_RR_TOLERANCE=RR,
               QUPRS_DIAGNOSTIC_PHASE_TOLERANCE=PHASE,
               QUPRS_CROSS_METHOD_SOLVER_TIMEOUT=str(solver_timeout))
    try:
        proc = subprocess.Popen(command, cwd=root, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
    except OSError as exc:
        return {"run_status": "PROCESS_SPAWN_ERROR", "verdict": None,
                "message": str(exc)}
    try:
        stdout, stderr = proc.communicate(timeout=watchdog)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        return {"run_status": "EXTERNAL_WATCHDOG_CENSORED",
                "verdict": None, "exit_code": None}
    output = [s[len(MARKER):] for s in stdout.splitlines() if s.startswith(MARKER)]
    if proc.returncode != 0 or len(output) != 1:
        return {"run_status": "PROCESS_OR_OUTPUT_ERROR", "verdict": None,
                "exit_code": proc.returncode,
                "stdout_tail": stdout[-1400:], "stderr_tail": stderr[-2300:]}
    try:
        value = json.loads(output[0])
    except json.JSONDecodeError:
        return {"run_status": "MALFORMED_RESULT_JSON", "verdict": None,
                "exit_code": proc.returncode}
    return {"run_status": "COMPLETED", "exit_code": proc.returncode, **value}


def classify(original, observation):
    if observation.get("run_status") != "COMPLETED":
        return "CENSORED_OR_UNCLASSIFIABLE"
    actual = binary(observation.get("verdict"))
    expected = binary(original)
    if actual is None or expected is None:
        return "CENSORED_OR_UNCLASSIFIABLE"
    return "BINARY_MATCH" if actual == expected else "BINARY_MISMATCH"


def run(root, output, sha, backend, shard, shards=24, timeout=200, watchdog=215):
    root, output = Path(root).resolve(), Path(output).resolve()
    if not (0 < timeout <= 200 < watchdog <= 240):
        raise ValueError("Unbounded science timeout")
    if backend not in ("python", "rust"):
        raise ValueError("Unsupported Ganak backend")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    if head != sha:
        raise ValueError("Refuse non-pinned modern SHA")
    subset = slice_corpus(root, shard, shards)
    if not subset or len(subset) > 5:
        raise ValueError("Invalid or oversized 101-case shard")
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = {"schema": SCHEMA + "-summary", "modern_sha": sha,
               "historical_sha": HISTORICAL_SHA,
               "solver": "ganak", "ganak_pinned_version": "2.8.0",
               "backend": backend, "distance_tolerance": DISTANCE,
               "rr_tolerance": RR, "phase_tolerance": PHASE,
               "shard": shard, "shards": shards,
               "source_ids": [c["id"] for c, *_ in subset],
               "total": len(subset), "completed": 0, "matched": 0,
               "binary_mismatches": [], "censored": [],
               "resolution_warning_cases": [],
               "arithmetically_certified": 0,
               "performance": "SCIENCE_ONLY_NOT_CODSPEED"}
    with output.open("w", encoding="utf8") as stream:
        for case, archived, first, second in subset:
            observed = execute_one(root, case, backend, timeout, watchdog)
            outcome = classify(archived["verdict"], observed)
            row = {
                "schema": SCHEMA, "modern_sha": sha, "historical_sha": HISTORICAL_SHA,
                "id": case["id"], "method": case["method"], "solver": "ganak",
                "ganak_pinned_version": "2.8.0", "backend": backend,
                "original_qasm": first, "counterpart_qasm": second,
                "historical_gpmc_sha256": archived["gpmc_sha256"],
                "historical_source_result_sha256": archived["source_result_sha256"],
                "original_verdict": archived["verdict"],
                "original_binary": binary(archived["verdict"]),
                "distance_tolerance": DISTANCE, "rr_tolerance": RR,
                "phase_tolerance": PHASE, "timeout_seconds": timeout,
                "external_watchdog_seconds": watchdog,
                "observation": observed, "binary_comparison": outcome,
                "solver_arithmetic_certification": "NOT_CERTIFIED",
                "timing": "NO_PERFORMANCE_MEASUREMENT",
            }
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()
            if observed.get("run_status") == "COMPLETED":
                summary["completed"] += 1
            if outcome == "BINARY_MATCH":
                summary["matched"] += 1
            elif outcome == "BINARY_MISMATCH":
                summary["binary_mismatches"].append({
                    "id": case["id"], "verdict": observed.get("verdict"),
                    "solver_invoked": observed.get("solver_invoked")})
            else:
                summary["censored"].append({
                    "id": case["id"], "run_status": observed.get("run_status"),
                    "verdict": observed.get("verdict")})
            if observed.get("wmc_print_resolution_distance") is not None:
                summary["resolution_warning_cases"].append({
                    "id": case["id"],
                    "wmc_print_resolution_distance": observed["wmc_print_resolution_distance"],
                    "wmc_precision_reason": observed.get("wmc_precision_reason")})
            output.with_suffix(".summary.json").write_text(
                json.dumps(summary, indent=2, sort_keys=True) + "\n")
            print("TACAS_GANAK_101 " + json.dumps({
                "id": case["id"], "method": case["method"], "backend": backend,
                "status": observed.get("run_status"),
                "verdict": observed.get("verdict"), "binary": outcome,
                "solver_invoked": observed.get("solver_invoked"),
                "wmc_print_resolution_distance": observed.get("wmc_print_resolution_distance"),
                "wmc_precision_reason": observed.get("wmc_precision_reason"),
            }, sort_keys=True), flush=True)
    summary["status"] = (
        "ALL_BINARY_MATCH" if summary["matched"] == len(subset)
        else "SCIENCE_HOLD_NOT_ALL_BINARY_MATCH")
    output.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print("TACAS_GANAK_101_SUMMARY " + json.dumps(summary, sort_keys=True), flush=True)
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--backend", choices=("python", "rust"), required=True)
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--shards", type=int, default=24)
    p.add_argument("--timeout", type=int, default=200)
    p.add_argument("--watchdog", type=int, default=215)
    a = p.parse_args()
    run(a.root, a.output, a.sha, a.backend, a.shard,
        shards=a.shards, timeout=a.timeout, watchdog=a.watchdog)


if __name__ == "__main__":
    main()

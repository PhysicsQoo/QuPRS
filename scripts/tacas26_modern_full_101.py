#!/usr/bin/env python3
"""Run every numerically comparable TACAS'26 case against CURRENT QuPRS.

This file is research-only.  It never replays historical counts as new results.
A complete binary-compatibility ledger is separate from a certified GPMC
arithmetic bound: GPMC does not currently supply the latter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from scripts import tacas26_modern_calibration as prior

ROOT = Path(__file__).resolve().parents[1]
N_CASES = 101
HISTORICAL_SHA = prior.SOURCE_SHA
MARKER = prior.MARKER
SCHEMA = "tacas26-modern-101-source-pinned-v1"
DEFAULT_SHARDS = 24


def comparable_source_records(root: Path):
    archive = prior.archive_labels(root)
    cases = {x["id"]: x for x in prior.matrix(root)}
    numerics = {case_id: archive[case_id] for case_id in archive if
                archive[case_id]["wmc_evidence_status"] == "WMC_PRINTED_VALUE_AVAILABLE"}
    if len(numerics) != N_CASES:
        raise ValueError(f"Refusing changed 101 original GPMC observations: {len(numerics)}")
    if len(set(numerics)) != N_CASES:
        raise ValueError("Duplicate historical ID")
    counts = {"EQUIVALENT": 0, "NOT_EQUIVALENT": 0}
    methods = {"hybrid": 0, "wmc_only": 0}
    corpus = []
    for case_id in sorted(numerics):
        saved = numerics[case_id]
        source = cases.get(case_id)
        if source is None:
            raise ValueError("Archived source no longer in canonical table: " + case_id)
        reference = prior.binary(saved["verdict"])
        if reference not in counts or source["method"] not in methods:
            raise ValueError("Unqualified source verdict/method: " + case_id)
        if saved["status"] != "RETURNED" or saved["source_sha"] != HISTORICAL_SHA:
            raise ValueError("Historical source provenance/status mismatch: " + case_id)
        if saved["method"] != source["method"] or saved["kind"] != source["kind"]:
            raise ValueError("Historical source experiment method changed: " + case_id)
        if saved.get("solver_returncode") != 0 or saved.get("solver_invoked") is not True:
            raise ValueError("Missing successful source GPMC call: " + case_id)
        case, original, counterpart = prior.get_pinned_case(root, case_id, cases)
        if (original["sha256"] != saved["original_qasm_sha256"] or
                counterpart["sha256"] != saved["counterpart_qasm_sha256"]):
            raise ValueError("QASM SHA256 disagrees with archived ORIGINAL GPMC evidence: " + case_id)
        counts[reference] += 1
        methods[source["method"]] += 1
        corpus.append((case, saved, original, counterpart))
    if counts != {"EQUIVALENT": 45, "NOT_EQUIVALENT": 56} or methods != {
        "hybrid": 44, "wmc_only": 57
    }:
        raise ValueError("Original 101 science cohort composition changed")
    return corpus


def slice_corpus(root: Path, shard: int, shards: int):
    if shards < 1 or not 0 <= shard < shards:
        raise ValueError("Invalid shard specification")
    corpus = comparable_source_records(root)
    return [item for i, item in enumerate(corpus) if i % shards == shard]


def launch(root, source, backend, digits, distance, rr, phase, solver_timeout, watchdog):
    if backend not in ("python", "rust") or digits not in (30, 90):
        raise ValueError("Unregistered backend or GPMC precision")
    variant = "random_rotation" if source["kind"] == "negative" else "transpiled"
    argv = [sys.executable, str(root / "scripts/tacas26_modern_101_worker.py"),
            str(root), Path(source["a"]).name, "proportional", "gpmc", backend,
            "0", variant, source["method"]]
    env = dict(os.environ)
    env.update(QUPRS_DIAGNOSTIC_DISTANCE_TOLERANCE=distance,
               QUPRS_DIAGNOSTIC_RR_TOLERANCE=rr,
               QUPRS_DIAGNOSTIC_PHASE_TOLERANCE=phase,
               QUPRS_DIAGNOSTIC_GPMC_DIGITS=str(digits),
               QUPRS_CROSS_METHOD_SOLVER_TIMEOUT=str(solver_timeout))
    try:
        child = subprocess.Popen(argv, env=env, cwd=root, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 start_new_session=True)
    except Exception as exc:
        return {"run_status": "PROCESS_SPAWN_ERROR", "verdict": None,
                "error": f"{type(exc).__name__}: {exc}"}
    try:
        stdout, stderr = child.communicate(timeout=watchdog)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.communicate()
        return {"run_status": "EXTERNAL_WATCHDOG_CENSORED", "verdict": None,
                "exit_code": None}
    observed = [line[len(MARKER):] for line in stdout.splitlines()
                if line.startswith(MARKER)]
    if child.returncode != 0 or len(observed) != 1:
        return {"run_status": "PROCESS_OR_OUTPUT_ERROR", "verdict": None,
                "exit_code": child.returncode, "stderr_tail": stderr[-1800:],
                "stdout_tail": stdout[-1000:]}
    try:
        record = json.loads(observed[0])
        if not isinstance(record, dict):
            raise ValueError("Expected output object")
    except (ValueError, TypeError) as exc:
        return {"run_status": "SOLVER_OUTPUT_PARSE_ERROR", "verdict": None,
                "error": str(exc), "exit_code": child.returncode}
    return {"run_status": "COMPLETED", "exit_code": child.returncode, **record}


def classification(old, observation):
    if observation.get("run_status") != "COMPLETED":
        return "NOT_MEASURED_OR_CENSORED"
    new = prior.binary(observation.get("verdict"))
    if new is None:
        return "NOT_MEASURED_OR_CENSORED"
    return "BINARY_MATCH" if new == prior.binary(old) else "BINARY_MISMATCH"


def run(root, output, sha, backend, digits, shard, shards,
        distance="2e-5", rr="1e-10", phase="1e-8",
        solver_timeout=200, watchdog=215):
    root, output = Path(root).resolve(), Path(output).resolve()
    if not (0 < solver_timeout < watchdog) or solver_timeout > 200 or watchdog > 240:
        raise ValueError("Solver timeout or watchdog out of bounded range")
    if (distance, rr, phase) != ("2e-5", "1e-10", "1e-8"):
        raise ValueError("101-case formal comparison must use frozen candidate and controls")
    if backend not in ("python", "rust") or digits not in (30, 90):
        raise ValueError("Unsupported research backend/precision")
    observed_sha = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        text=True, capture_output=True, check=True
    ).stdout.strip()
    if sha != observed_sha:
        raise ValueError("Source SHA mismatch; refuse cross-SHA science claims")
    subset = slice_corpus(root, shard, shards)
    if not subset or len(subset) > 5:
        raise ValueError("Refuse empty or oversized 101-case CI shard")
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = {"schema": SCHEMA + "-summary", "head_sha": sha,
               "reference_sha": HISTORICAL_SHA, "backend": backend, "digits": digits,
               "shard": shard, "shards": shards, "distance_tolerance": distance,
               "rr_tolerance": rr, "phase_tolerance": phase,
               "expected_ids": [x[0]["id"] for x in subset],
               "all_101_preflight_qualified": True,
               "probes_completed": 0, "binary_matched": 0,
               "binary_mismatched": [], "censored_or_invalid": [],
               "arithmetically_certified": 0,
               "precision_qualification": "SOLVER_ROUNDING_NOT_CERTIFIED",
               "performance": "SCIENCE_ONLY_NOT_CODSPEED"}
    with output.open("w", encoding="utf-8") as stream:
        for index, (case, saved, original, counterpart) in enumerate(subset):
            observation = launch(root, case, backend, digits, distance, rr,
                                 phase, solver_timeout, watchdog)
            label = classification(saved["verdict"], observation)
            solver_used = observation.get("solver_invoked")
            state = "NOT_CERTIFIED_SOLVER_ERROR_BOUND_ABSENT" if solver_used else (
                "NO_SOLVER_ARITHMETIC_TO_CERTIFY" if solver_used is False
                else "UNKNOWN_UNEXECUTED_OR_CENSORED")
            row = {
                "schema": SCHEMA, "head_sha": sha,
                "historical_sha": HISTORICAL_SHA,
                "id": case["id"], "sequence": index,
                "source_historical_verdict": saved["verdict"],
                "source_binary_verdict": prior.binary(saved["verdict"]),
                "historical_output_sha256": saved["source_result_sha256"],
                "historical_gpmc_sha256": saved["gpmc_sha256"],
                "backend": backend, "method": case["method"], "solver": "gpmc",
                "gpmc_precision_digits": digits,
                "source_original": original, "source_counterpart": counterpart,
                "source_variant": ("random_rotation" if case["kind"] == "negative"
                                   else "transpiled"),
                "distance_tolerance": distance, "rr_tolerance": rr,
                "phase_tolerance": phase, "timeout_seconds": solver_timeout,
                "external_watchdog_seconds": watchdog,
                "observation": observation, "binary_comparison": label,
                "solver_arithmetic_certification": state,
                "timing": "NO_PERFORMANCE_MEASUREMENT",
            }
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()
            if observation.get("run_status") == "COMPLETED":
                summary["probes_completed"] += 1
            if label == "BINARY_MATCH":
                summary["binary_matched"] += 1
            elif label == "BINARY_MISMATCH":
                summary["binary_mismatched"].append(case["id"])
            else:
                summary["censored_or_invalid"].append({
                    "id": case["id"], "status": observation.get("run_status"),
                    "verdict": observation.get("verdict")})
            summary["collection_status"] = (
                "ALL_BINARY_MATCH" if summary["binary_matched"] == len(subset)
                else "SCIENCE_HOLD_BINARY_INCOMPLETE_OR_MISMATCH")
            output.with_suffix(".summary.json").write_text(
                json.dumps(summary, sort_keys=True, indent=2) + "\n")
            print(json.dumps({
                "id": case["id"], "backend": backend, "digits": digits,
                "run_status": observation.get("run_status"),
                "verdict": observation.get("verdict"), "binary": label,
                "solver_invoked": solver_used,
                "wmc_precision_reason": observation.get("wmc_precision_reason"),
                "solver_arithmetic_certification": state,
            }, sort_keys=True), flush=True)
    print("TACAS26_MODERN_101_SUMMARY " + json.dumps(summary, sort_keys=True), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--backend", choices=("rust", "python"), required=True)
    parser.add_argument("--digits", type=int, choices=(30, 90), default=30)
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--shards", type=int, default=DEFAULT_SHARDS)
    parser.add_argument("--solver-timeout", type=int, default=200)
    parser.add_argument("--watchdog", type=int, default=215)
    args = parser.parse_args()
    run(args.root, args.output, args.sha, args.backend, args.digits,
        args.shard, args.shards, solver_timeout=args.solver_timeout,
        watchdog=args.watchdog)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Bounded, source-pinned *modern* QuPRS TACAS binary-verdict calibration.

Research branch only. No standalone wallclock performance numbers are collected.
Historical v0.9.1 GPMC printed counts are NEVER substituted for modern calls.
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

from scripts.tacas26_quprs_only import matrix
from scripts.tacas26_paper_matrix import pinned

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs/development/tacas26-results/wmc-evidence.json"
MARKER = "QUPRS_WALLTIME_RESULT "
SOURCE_SHA = "e928abc47dd15926364ec77905eb0d5dc92ce8cc"
DEFAULTS = {"distance": "1e-8", "rr": "1e-10", "phase": "1e-8", "digits": 30}
CANDIDATE = "2e-5"
# Four shards, 6 distinct source QASM pairs. Never use these as production defaults.
SHARDS = (
    ("table2:qpeinexact24:positive:hybrid",),
    ("table2:qpeinexact20:positive:hybrid",),
    ("table2:qpeinexact16:positive:hybrid",
     "table3_negative:qaoa11:negative:hybrid"),
    ("table3_negative:qwalk4:negative:hybrid",
     "table3_negative:qpeinexact20:negative:hybrid"),
)
EDGE_CASES = {"qpeinexact24", "qpeinexact20"}
CONTROL_RR0 = {"table2:qpeinexact24:positive:hybrid",
               "table2:qpeinexact20:positive:hybrid",
               "table3_negative:qaoa11:negative:hybrid"}
CONTROL_MPFR90 = {"table2:qpeinexact24:positive:hybrid",
                  "table3_negative:qaoa11:negative:hybrid"}
CONTROL_WMC_ONLY = {"table3_negative:qaoa11:negative:hybrid",
                    "table3_negative:qwalk4:negative:hybrid"}


def binary(verdict):
    if verdict in ("equivalent", "equivalent*"):
        return "EQUIVALENT"
    if verdict == "not_equivalent":
        return "NOT_EQUIVALENT"
    return None


def experiment_plan(shard):
    if shard not in range(len(SHARDS)):
        raise ValueError("Invalid shard")
    plan = []
    for case_id in SHARDS[shard]:
        # Default versus proposed paper-reproduction policy.
        for eps in ("1e-8", CANDIDATE):
            plan.append((case_id, "rust", "hybrid", eps, "1e-10", "1e-8", 30))
        # Precisely bracket the positive decision transition.
        if case_id.startswith("table2:") and any(
            token in case_id for token in ("qpeinexact24:", "qpeinexact20:")
        ):
            for eps in ("1e-5", "1.4e-5", "3e-5"):
                plan.append((case_id, "rust", "hybrid", eps, "1e-10", "1e-8", 30))
        # Python/Rust parity at one and the same candidate policy.
        plan.append((case_id, "python", "hybrid", CANDIDATE, "1e-10", "1e-8", 30))
        # Vary ONE extra parameter at a time with all others pinned.
        if case_id in CONTROL_RR0:
            plan.append((case_id, "rust", "hybrid", CANDIDATE, "0", "1e-8", 30))
        if case_id in CONTROL_MPFR90:
            plan.append((case_id, "rust", "hybrid", CANDIDATE, "1e-10", "1e-8", 90))
        if case_id in CONTROL_WMC_ONLY:
            plan.append((case_id, "rust", "wmc_only", CANDIDATE, "1e-10", "1e-8", 30))
    if len(set(plan)) != len(plan):
        raise ValueError("Duplicate experiment plan entries")
    return plan


def archive_labels(root):
    data = json.loads((root / "docs/development/tacas26-results/wmc-evidence.json").read_text())
    if data.get("historical_source_sha") != SOURCE_SHA:
        raise ValueError("Historical source identity mismatch")
    by_id = {}
    for record in data["records"]:
        row = record["numeric_summary"]
        if row["id"] in by_id:
            raise ValueError("Duplicate historical case identity")
        by_id[row["id"]] = row
    if len(by_id) != 184:
        raise ValueError("Expected 184 original QuPRS calls")
    return by_id


def get_pinned_case(root, case_id, cases):
    case = cases[case_id]
    if case["suite"] not in ("table2", "table3_negative"):
        raise ValueError("Non-MQT experiment case")
    a = pinned(root, case["a"], case.get("sha_a"))
    b = pinned(root, case["b"], case.get("sha_b"))
    if Path(case["a"]).name != Path(case["b"]).name:
        raise ValueError("QASM pair filename differs")
    return case, a, b


def run_probe(root, case, spec, solver_timeout, watchdog):
    case_id, backend, method, eps, rr, phase, digits = spec
    variant = "random_rotation" if case["kind"] == "negative" else "transpiled"
    filename = Path(case["a"]).name
    cmd = [sys.executable, str(root / "benchmarks/codspeed/solver_case.py"),
           str(root), filename, "proportional", "gpmc", backend, "0", variant, method]
    env = dict(os.environ)
    env.update(QUPRS_DIAGNOSTIC_DISTANCE_TOLERANCE=eps,
               QUPRS_DIAGNOSTIC_RR_TOLERANCE=rr,
               QUPRS_DIAGNOSTIC_PHASE_TOLERANCE=phase,
               QUPRS_DIAGNOSTIC_GPMC_DIGITS=str(digits),
               QUPRS_CROSS_METHOD_SOLVER_TIMEOUT=str(solver_timeout))
    proc = subprocess.Popen(cmd, cwd=root, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=watchdog)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        return {"run_status": "WATCHDOG_CENSORED", "exit_code": None,
                "verdict": None, "solver_invoked": None}
    lines = [line[len(MARKER):] for line in stdout.splitlines()
             if line.startswith(MARKER)]
    if proc.returncode or len(lines) != 1:
        return {"run_status": "PROCESS_ERROR", "exit_code": proc.returncode,
                "verdict": None, "solver_invoked": None,
                "stderr_tail": stderr[-2500:], "stdout_tail": stdout[-1500:]}
    try:
        value = json.loads(lines[0])
    except json.JSONDecodeError:
        return {"run_status": "UNPARSEABLE_OUTPUT", "exit_code": proc.returncode,
                "verdict": None, "solver_invoked": None}
    return {"run_status": "COMPLETED", "exit_code": proc.returncode,
            **value}


def classify(historical, result):
    old = binary(historical)
    new = binary(result.get("verdict"))
    if old is None:
        return "HISTORICAL_ORACLE_UNQUALIFIED"
    if new is None:
        return "CENSORED_OR_UNCLASSIFIABLE"
    return "BINARY_MATCH" if new == old else "BINARY_MISMATCH"


def execute(root, shard, output, source_sha, solver_timeout=30, watchdog=48):
    root, output = Path(root).resolve(), Path(output)
    if solver_timeout <= 0 or watchdog <= solver_timeout:
        raise ValueError("The external watchdog must exceed the solver limit")
    canonical = {x["id"]: x for x in matrix(root)}
    historical = archive_labels(root)
    plan = experiment_plan(shard)
    output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with output.open("w", encoding="utf-8") as handle:
        for index, spec in enumerate(plan):
            case_id, backend, method, distance, rr, phase, digits = spec
            lookup_id = case_id if method == "hybrid" else case_id.replace(":hybrid", ":wmc_only")
            old = historical[lookup_id]["verdict"]
            source, original, target = get_pinned_case(root, case_id, canonical)
            observation = run_probe(root, source, spec, solver_timeout, watchdog)
            row = {"schema": "tacas26-modern-binary-science-v1",
                   "research_head_sha": source_sha,
                   "original_quprs_sha": SOURCE_SHA,
                   "id": lookup_id, "reference_case_id": case_id,
                   "sequence": index, "historical_verdict": old,
                   "historical_binary": binary(old),
                   "backend": backend, "method": method, "solver": "gpmc",
                   "strategy": "proportional",
                   "pair_variant": ("random_rotation" if source["kind"] == "negative"
                                    else "transpiled"),
                   "distance_tolerance": distance, "rr_tolerance": rr,
                   "phase_tolerance": phase, "gpmc_digits": digits,
                   "solver_timeout_seconds": solver_timeout,
                   "watchdog_seconds": watchdog,
                   "qasm_original": original, "qasm_counterpart": target,
                   "observation": observation,
                   "classification": classify(old, observation),
                   "timing": "NO_PERFORMANCE_MEASUREMENT_SCIENCE_ONLY"}
            records.append(row)
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()  # retain partial result if a later scientific case is censored
            print(json.dumps({"case": lookup_id, "backend": backend, "method": method,
                              "eps": distance, "rr": rr, "digits": digits,
                              "status": observation["run_status"],
                              "verdict": observation.get("verdict"),
                              "binary_comparison": row["classification"]}), flush=True)
    candidate = [r for r in records if r["distance_tolerance"] == CANDIDATE
                 and r["rr_tolerance"] == DEFAULTS["rr"]
                 and r["phase_tolerance"] == DEFAULTS["phase"]
                 and r["gpmc_digits"] == DEFAULTS["digits"]
                 and r["method"] == "hybrid"]
    mismatches = [r for r in candidate if r["classification"] == "BINARY_MISMATCH"]
    incomplete = [r for r in candidate if r["classification"] != "BINARY_MATCH"]
    summary = {"schema": "tacas26-modern-binary-science-summary-v1",
               "head_sha": source_sha, "historical_source_sha": SOURCE_SHA,
               "shard": shard, "cases": list(SHARDS[shard]),
               "all_probes": len(records), "candidate_probes": len(candidate),
               "candidate_matches": len(candidate)-len(incomplete),
               "candidate_mismatch_ids": [r["id"] + ":" + r["backend"] for r in mismatches],
               "candidate_incomplete": [
                   {"id": r["id"], "backend": r["backend"],
                    "classification": r["classification"],
                    "run_status": r["observation"]["run_status"]}
                   for r in incomplete],
               "status": ("BINARY_MATCH_ON_OBSERVED_CASES" if not incomplete else
                          "SCIENCE_HOLD_NOT_ALL_CANDIDATE_PROBES_MATCH"),
               "limitations": [
                   "Not a full 20q unitary equivalence oracle",
                   "Source v0.9.1 verdicts were obtained using old rounded magnitude",
                   "No certified GPMC arithmetic error budget",
                   "Any timeout is censored, not not_equivalent",
                   "CodSpeed alone may support performance comparisons"]}
    output.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("MODERN_TACAS26_CALIBRATION " + json.dumps(summary, sort_keys=True), flush=True)
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--solver-timeout", type=int, default=30)
    p.add_argument("--watchdog", type=int, default=48)
    args = p.parse_args()
    execute(args.root, args.shard, args.output, args.sha,
            solver_timeout=args.solver_timeout, watchdog=args.watchdog)


if __name__ == "__main__":
    main()

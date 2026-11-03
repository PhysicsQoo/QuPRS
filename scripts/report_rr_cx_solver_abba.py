#!/usr/bin/env python3
"""Exact Bra-CX solver-inclusive ABBA block consistency and same-host drift.

No timer here. Only the official CodSpeed walltime export supplies durations.
This is diagnostic only: hosted GitHub runner != qualified CodSpeed Macro.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.codspeed.case_registry import WALLTIME_CASE_IDS

ID = re.compile(r"test_codspeed_rr_cx_solver_abba\[([a-z0-9_]+)-block([012])-(A1|B1|B2|A2)\]$")
POSITIONS = {"A1": "base", "B1": "head", "B2": "head", "A2": "base"}
SELECTED = frozenset(("qft16_gpmc", "vqe4_gpmc", "vqe4_gpmc_python"))
BLOCKS = range(3)


def produce(measurements: dict, provenance: list[dict], base_sha: str,
            head_sha: str) -> dict:
    if SELECTED - WALLTIME_CASE_IDS:
        raise ValueError("invalid case registry for Bra-CX targeted E2E")
    if measurements.get("instrument", {}).get("type") != "walltime":
        raise ValueError("CodSpeed WallTime is required")
    needed = {(case, block, pos) for case in SELECTED
              for block in BLOCKS for pos in POSITIONS}
    metrics = {}
    for entry in measurements.get("benchmarks", []):
        uri = entry.get("uri", "")
        match = ID.search(uri)
        if not match:
            raise ValueError(f"unknown measured benchmark {uri}")
        case, block, pos = match[1], int(match[2]), match[3]
        key = (case, block, pos)
        if key in metrics:
            raise ValueError(f"duplicate benchmark {key}")
        stats = entry.get("stats", {})
        if stats.get("rounds", 0) < 5 or stats.get("iter_per_round", 0) < 1:
            raise ValueError(f"missing 5 CodSpeed measured rounds: {key}")
        for field in ("min_ns", "median_ns", "mean_ns", "stdev_ns"):
            value = stats.get(field)
            if (not isinstance(value, (float, int)) or isinstance(value, bool)
                    or not math.isfinite(value) or value < 0):
                raise ValueError(f"invalid CodSpeed {field}: {key}")
        if stats["median_ns"] <= 0 or stats["mean_ns"] <= 0:
            raise ValueError(f"nonpositive measured time: {key}")
        metrics[key] = stats
    if set(metrics) != needed:
        raise ValueError(f"incomplete ABBA metric identities: {needed-set(metrics)}")

    science = {}
    for row in provenance:
        key = row.get("case"), row.get("block"), row.get("position")
        if key in science:
            raise ValueError(f"duplicate scientific provenance: {key}")
        science[key] = row
    if set(science) != needed:
        raise ValueError(f"incomplete ABBA scientific identities: {needed-set(science)}")

    report = {
        "schema": "quprs-rr-cx-solver-abba-three-block-v1",
        "base_sha": base_sha, "head_sha": head_sha,
        "instrument": "CodSpeed WallTime",
        "block_protocol": "three repetitions of A1-B1-B2-A2 on same hosted runner",
        "performance_status": "NOT_CERTIFIED",
        "observation_policy": "OBSERVATION_ONLY_NO_FIXED_THRESHOLD",
        "release_gate_enabled": False,
        "default_regression_threshold": None,
        "solver_arithmetic_certified": False,
        "case_selection": "qft16-gpmc-rust/vqe4-gpmc-rust/vqe4-gpmc-python-control",
        "comparison": "previous-guarded-xor-versus-exact-bra-cx",
        "qpe_exact8_scope": "RR native only; not solver forced",
        "cases": [],
    }
    for case in sorted(SELECTED):
        measures = []
        baseline_drift = []
        case_signature = None
        for block in BLOCKS:
            b = [science[case, block, pos] for pos in POSITIONS]
            ref = b[0]
            for witness in b:
                if (witness.get("case") != case
                        or witness.get("position") not in POSITIONS
                        or witness.get("revision") != POSITIONS[witness["position"]]
                        or witness.get("sha") != (
                            base_sha if witness["revision"] == "base" else head_sha)
                        or witness.get("fixture_sha") != head_sha
                        or witness.get("science_status") != "CONSISTENT_WITHIN_POSITION"
                        or witness.get("invocations", 0) < 5
                        or len(witness.get("observations", [])) != witness["invocations"]
                        or any(x.get("solver_invoked") is not True for x in witness["observations"])
                        or any(x.get("verdict") not in ("equivalent", "equivalent*")
                               for x in witness["observations"])):
                    raise ValueError(f"{case}/{block}: invalid Solver/science/sha")
                if any(witness.get(x) != ref.get(x)
                       for x in ("method", "backend", "solver", "strategy", "reverse",
                                 "fixture_sha", "qasm_sha256")):
                    raise ValueError(f"{case}/{block}: changed workload settings")
            verdicts = {x["verdict"] for w in b for x in w["observations"]}
            if len(verdicts) != 1:
                raise ValueError(f"{case}/{block}: changed verdict inside ABBA")
            # An ABBA block cannot silently switch fixture, settings or
            # scientific verdict relative to another block for this case.
            signature = (
                ref.get("method"), ref.get("backend"), ref.get("solver"),
                ref.get("strategy"), ref.get("reverse"),
                ref.get("fixture_sha"), tuple(ref.get("qasm_sha256", [])),
                next(iter(verdicts)),
            )
            if case_signature is None:
                case_signature = signature
            elif signature != case_signature:
                raise ValueError(f"{case}/{block}: changed source/settings/verdict across ABBA blocks")
            a1 = metrics[case, block, "A1"]["median_ns"]
            b1 = metrics[case, block, "B1"]["median_ns"]
            b2 = metrics[case, block, "B2"]["median_ns"]
            a2 = metrics[case, block, "A2"]["median_ns"]
            base_median = (a1 + a2) / 2
            head_median = (b1 + b2) / 2
            drift = abs(a2 / a1 - 1)
            median_change = 100 * (head_median / base_median - 1)
            measures.append(median_change)
            baseline_drift.append(100 * drift)
        # Preserve every real Solver arithmetic output as evidence.
        # Printed numerical estimates are not required to be exactly equal.
        solver_observations = []
        for block in BLOCKS:
            for pos in POSITIONS:
                row = science[case, block, pos]
                solver_observations.append({
                    "block": block, "position": pos,
                    "revision": row["revision"],
                    "observations": row["observations"],
                })
        tol_sets = {
            key: {str(obs.get(key)) for w in solver_observations
                  for obs in w["observations"]}
            for key in ("effective_rr_tolerance",
                        "effective_distance_tolerance",
                        "effective_phase_tolerance",
                        "effective_gpmc_digits")
        }
        if any(len(v) != 1 for v in tol_sets.values()):
            raise ValueError(f"{case}: inconsistent effective precision/tolerances")
        if (tol_sets["effective_rr_tolerance"] != {"1e-10"}
                or tol_sets["effective_distance_tolerance"] != {"1e-08"}
                or tol_sets["effective_phase_tolerance"] != {"1e-08"}
                or tol_sets["effective_gpmc_digits"] != {"30"}):
            raise ValueError(f"{case}: unintended effective tolerance settings {tol_sets}")
        # One source-pinned verifier and Solver invocation per position sample.
        # Observed A/A drift is a lower bound on potential noise, not
        # a confidence interval or an arbitrary permanent pass threshold.
        report["cases"].append({
            "case": case, "blocks": len(BLOCKS),
            "median_head_base_change_percent": statistics.median(measures),
            "block_changes_percent": measures,
            "baseline_a1_a2_drift_percent": baseline_drift,
            "max_observed_baseline_drift_percent": max(baseline_drift),
            "within_run_a1_a2_drift_is_independent_aa_cohort": False,
            "independent_aa_cohort_count": 0,
            "decision": "CONDITIONAL_DIAGNOSTIC_ONLY",
            "observation_status": "OBSERVED_DIRECTION_ONLY",
            "release_gate_effect": "NONE",
            "solver_observations": solver_observations,
            "effective_configuration": {key: next(iter(value)) for key, value in tol_sets.items()},
            "warning": "Non-Macro hosted runner; intervals and stable hardware "
                       "qualification absent; cannot claim 1% regression GO.",
        })
    report["provenance_complete"] = True
    report["optional_only_if_formal_gate_reconsidered"] = [
        "Stable CodSpeed Macro Runner or independently validated same-cohort environment",
        "Independent A/A blocks spanning separate executions and several days",
        "Confidence interval on paired block ratio and predeclared per-case noise threshold",
        "Source/circuit/method/tolerance/solver stage and verdict identity",
        "Solver precision limitations tracked separately from runtime",
    ]
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--measurements", type=Path, required=True)
    p.add_argument("--provenance", type=Path, required=True)
    p.add_argument("--base-sha", required=True)
    p.add_argument("--head-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    report = produce(
        json.loads(a.measurements.read_text()),
        [json.loads(x) for x in a.provenance.read_text().splitlines() if x],
        a.base_sha, a.head_sha,
    )
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for item in report["cases"]:
        print(f"{item['case']}: block changes={item['block_changes_percent']}, "
              f"baseline A/A drift={item['baseline_a1_a2_drift_percent']}")
    print("RR-CX ABBA SCIENCE/STAGE PASS; PERFORMANCE_NOT_CERTIFIED (non-Macro)")


if __name__ == "__main__":
    main()

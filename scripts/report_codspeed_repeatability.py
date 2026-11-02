#!/usr/bin/env python3
"""Verify 4-case CodSpeed five-round repeatability without faking timing.

Cross-case walltime values include Python subprocess startup, must never be
interpreted as isolated Solver speedups, and are not a base/HEAD comparison.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.codspeed.case_registry import REPEATABILITY_EXPECTATIONS

ID = re.compile(r"test_bounded_same_sha_repeatability\[([^\]]+)\]$")


def produce(measurements: dict, records: list[dict], oracle: dict, sha: str) -> dict:
    if measurements.get("instrument", {}).get("type") != "walltime":
        raise ValueError("repeatability must use real CodSpeed WallTime instrument")
    if oracle.get("fixture_sha") != sha or oracle.get("schema") != "source-qasm-global-phase-double-v1":
        raise ValueError("independent Qiskit oracle has wrong SHA or schema")
    expected = set(REPEATABILITY_EXPECTATIONS)
    observed = {}
    for entry in measurements.get("benchmarks", []):
        match = ID.search(entry.get("uri", ""))
        if not match or match.group(1) in observed:
            raise ValueError("unrecognized or duplicate measured benchmark URI")
        stats = entry["stats"]
        if stats.get("rounds", 0) < 5 or stats.get("iter_per_round", 0) < 1:
            raise ValueError(f"insufficient CodSpeed WallTime rounds: {match.group(1)}")
        for value_name in ("min_ns", "median_ns", "mean_ns", "stdev_ns"):
            val = stats.get(value_name)
            if not isinstance(val, (int, float)) or not math.isfinite(val) or val < 0:
                raise ValueError(f"invalid metric {match.group(1)}/{value_name}")
        observed[match.group(1)] = stats
    science = {}
    for record in records:
        case = record.get("case")
        if case not in expected or case in science or record.get("sha") != sha:
            raise ValueError("extra, duplicate or cross-SHA science record")
        science[case] = record
    if set(observed) != expected or set(science) != expected:
        raise ValueError("CodSpeed metrics and iteration provenance must both cover exact 4 cases")
    report = {"schema": "quprs-codspeed-v3-stage-repeatability-v1",
              "sha": sha,
              "instrument": "CodSpeed WallTime, same-runner five-round descriptive",
              "performance_certified": False,
              "solver_arithmetic_certified": False,
              "cases": []}
    for case in sorted(expected):
        record = science[case]
        source = oracle.get("cases", {}).get(case)
        want_verdict, want_solver = REPEATABILITY_EXPECTATIONS[case]
        if source is None or source.get("qasm_sha256") != record.get("qasm_sha256"):
            raise ValueError(f"{case}: QASM SHA256 disagrees with independent oracle")
        if (source.get("numerically_consistent_up_to_global_phase") is not True
                or source.get("phase_corrected_frobenius_normalized", 1) >= 1e-10):
            raise ValueError(f"{case}: independent Qiskit source-pair oracle did not pass")
        calls = record.get("observations", [])
        if (record.get("all_invocations_scientifically_consistent") is not True
                or not calls or record.get("observed_invocations_including_instrument_warmup") != len(calls)
                or record.get("expected_verdict") != want_verdict
                or record.get("expected_solver_invoked") is not want_solver):
            raise ValueError(f"{case}: per-invocation verdict/stage mismatch")
        if not all(call.get("status") == "COMPLETED"
                   and call.get("verdict") == want_verdict
                   and call.get("solver_invoked") is want_solver
                   and call.get("exit_code") == 0 for call in calls):
            raise ValueError(f"{case}: timeout or semantic mismatch")
        stats = observed[case]
        report["cases"].append({
            "case": case,
            "category": "Solver-inclusive Hybrid" if want_solver else "RR-terminated Hybrid",
            "verdict": want_verdict, "qasm_sha256": record["qasm_sha256"],
            "matrix_residual": source["phase_corrected_frobenius_normalized"],
            "global_phase_rad": source["relative_global_phase_rad"],
            "measurement_rounds": stats["rounds"],
            "warmup_and_measure_invocations": len(calls),
            "min_ms": stats["min_ns"] / 1e6, "median_ms": stats["median_ns"] / 1e6,
            "mean_ms": stats["mean_ns"] / 1e6, "stdev_ms": stats["stdev_ns"] / 1e6,
            "coefficient_of_variation": (
                stats["stdev_ns"] / stats["mean_ns"] if stats["mean_ns"] else None),
            "solver_precision_reasons": record.get("precision_reasons", []),
            "qualified_source_numerically": True,
            "qualified_solver_arithmetic": False if want_solver else None,
            "benchmark_scope": "fresh subprocess Python+Rust+Solver+I/O, not solver-only",
        })
    report["all_cases_qualified_source_and_stage"] = True
    report["warning"] = ("Hosted non-Macro Runner variance and one five-round experiment "
                         "do not certify production performance; precision warnings preserved.")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--measurements", type=Path, required=True)
    p.add_argument("--provenance", type=Path, required=True)
    p.add_argument("--source-oracle", type=Path, required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    measurements = json.loads(a.measurements.read_text())
    records = [json.loads(line) for line in a.provenance.read_text().splitlines() if line.strip()]
    oracle = json.loads(a.source_oracle.read_text())
    report = produce(measurements, records, oracle, a.sha)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for case in report["cases"]:
        print(f"{case['case']:12s} {case['category']:26s} "
              f"median={case['median_ms']:.3f}ms "
              f"cv={case['coefficient_of_variation']:.3%}")
    print("REPORT: SCIENCE_PHASED_PASS; PERFORMANCE_NOT_CERTIFIED")


if __name__ == "__main__":
    main()

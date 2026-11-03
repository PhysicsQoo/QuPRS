#!/usr/bin/env python3
"""Validate and pair source-pinned CodSpeed WallTime base/HEAD samples.

Input numbers come ONLY from pytest-codspeed's WallTime instrument report.
The test writes semantic provenance AFTER the measured operation.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path

ID = re.compile(r"test_pr_solver_inclusive_walltime\[([^\]]+)-(base|head)\]$")
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.codspeed.case_registry import (
    ALL_WALLTIME_CASE_IDS as EXPECTED,
    QASM261_WALLTIME_CASE_IDS,
    GANAK_PRECISION_LIMIT_CASES as PRECISION_LIMITED_FIXTURES,
)
EQ = {"equivalent", "equivalent*"}


def classify(verdict: str) -> str:
    return "equivalent" if verdict in EQ else verdict



def evidenced_ganak_print_limitation(case: str, base: dict, head: dict,
                                   source_oracle: dict | None, head_sha: str) -> bool:
    if case not in PRECISION_LIMITED_FIXTURES or source_oracle is None:
        return False
    if (source_oracle.get("schema") != "source-qasm-global-phase-double-v1"
            or source_oracle.get("fixture_sha") != head_sha
            or source_oracle.get("certified_epsilon_distance") is not False):
        return False
    witness = source_oracle.get("cases", {}).get(PRECISION_LIMITED_FIXTURES[case], {})
    residual = witness.get("phase_corrected_frobenius_normalized")
    if not (witness.get("numerically_consistent_up_to_global_phase") is True
            and isinstance(residual, (int, float)) and math.isfinite(residual)
            and 0 <= residual < 1e-10 and len(witness.get("qasm_sha256", [])) == 2):
        return False
    if not (base.get("verdict") == "equivalent*"
            and head.get("verdict") == "not_equivalent"
            and head.get("solver") == "ganak"
            and head.get("solver_invoked") is True
            and head.get("wmc_printed_verdict") == "unknown"
            and head.get("wmc_precision_reason") == "ganak_point_estimate_resolution_limited"
            and head.get("wmc_numerical_verdict") == "not_equivalent"):
        return False
    width, distance = (head.get("wmc_print_resolution_distance"),
                       head.get("approximate_distance_tolerance"))
    return (isinstance(width, (int, float)) and math.isfinite(width)
            and isinstance(distance, (int, float)) and math.isfinite(distance)
            and 0 < distance < width)


def format_change(percent: float | None) -> str:
    return "N/A (verdict changed)" if percent is None else f"{percent:+.2f}%"


def produce(measurements: dict, records: list[dict], base_sha: str,
            head_sha: str, source_oracle: dict | None = None, required_cases=None):
    if measurements.get("instrument", {}).get("type") != "walltime":
        raise ValueError("Not a CodSpeed WallTime measurement")
    expected = frozenset(EXPECTED if required_cases is None else required_cases)
    if not expected or not expected.issubset(EXPECTED):
        raise ValueError('paired case selection must be nonempty subset of registry')
    times = {}
    for entry in measurements.get("benchmarks", []):
        match = ID.search(entry.get("uri", ""))
        if match is None:
            raise ValueError(f"Unexpected CodSpeed benchmark identity: {entry.get('uri')}")
        key = (match.group(1), match.group(2))
        if key in times:
            raise ValueError(f"Duplicate CodSpeed measurement: {key}")
        stats = entry["stats"]
        if stats.get("rounds", 0) < 2 or stats.get("iter_per_round", 0) < 1:
            raise ValueError(f"Incomplete CodSpeed rounds: {key}: {stats}")
        if not all(math.isfinite(stats[field]) and stats[field] > 0
                   for field in ("min_ns", "median_ns", "mean_ns")):
            raise ValueError(f"Invalid CodSpeed measured duration: {key}")
        times[key] = stats

    provenance = {}
    for record in records:
        key = record["case"], record["revision"]
        if key in provenance:
            raise ValueError(f"Duplicated semantic record: {key}")
        provenance[key] = record
    keys = {(case, rev) for case in expected for rev in ("base", "head")}
    if set(times) != keys or set(provenance) != keys:
        raise ValueError(
            f"Incomplete/extra paired coverage: missing_times={keys - set(times)} "
            f"extra_times={set(times) - keys}; missing_provenance={keys - set(provenance)} "
            f"extra_provenance={set(provenance) - keys}"
        )

    outcome = []
    errors = []
    precision_incomparable = []
    for case in sorted(expected):
        b, h = provenance[case, "base"], provenance[case, "head"]
        bt, ht = times[case, "base"], times[case, "head"]
        for revision, record, sha in (("base", b, base_sha), ("head", h, head_sha)):
            if record["sha"] != sha or record["fixture_sha"] != head_sha:
                errors.append(f"{case}/{revision}: incorrect source/fixture SHA")
            if not record["solver_invoked"]:
                errors.append(f"{case}/{revision}: Solver was not actually invoked")
            if record["verdict"] not in EQ | {"not_equivalent"}:
                errors.append(f"{case}/{revision}: inconclusive verdict {record['verdict']}")
            if record["method"] != "hybrid":
                errors.append(f"{case}/{revision}: expected Hybrid")
            versioned_negative = case in QASM261_WALLTIME_CASE_IDS
            if versioned_negative:
                if (record["verdict"] != "not_equivalent"
                        or record["verification_status"] != "EXPECTED_SOURCE_NEGATIVE"
                        or record.get("pair_variant") != "random_rotation"
                        or record.get("qasm_corpus") != "qiskit-2.6.1-opt0"
                        or not isinstance(record.get("fixture_sha256"), list)
                        or len(record["fixture_sha256"]) != 2
                        or any(not re.fullmatch(r"[0-9a-f]{64}", v)
                               for v in record["fixture_sha256"])
                        or record.get("effective_rr_tolerance") != 1e-10
                        or record.get("effective_distance_tolerance") != 1e-8
                        or record.get("effective_phase_tolerance") != 1e-8
                        or record.get("effective_gpmc_digits") != 30):
                    errors.append(f"{case}/{revision}: wrong QASM261 NEQ source/stage/fixture")
            elif (record["verdict"] == "not_equivalent"
                  and record["verification_status"] != "EXTERNAL_GANAK_PRINT_LIMITATION"):
                errors.append(f"{case}/{revision}: negative without known Solver limitation")

        for field in ("method", "backend", "solver", "strategy", "reverse", "fixture_sha",
                      "pair_variant", "qasm_corpus", "fixture_sha256",
                      "effective_rr_tolerance", "effective_distance_tolerance",
                      "effective_phase_tolerance", "effective_gpmc_digits"):
            if b.get(field) != h.get(field):
                errors.append(f"{case}: unequal {field}: {b[field]} != {h[field]}")
        expected_precision_limit = evidenced_ganak_print_limitation(
            case, b, h, source_oracle, head_sha
        )
        if b["verdict"] != h["verdict"]:
            if expected_precision_limit:
                precision_incomparable.append(case)
            else:
                errors.append(
                    f"{case}: semantic category changed (including phase label): "
                    f"{b['verdict']} -> {h['verdict']}"
                )
        warning = []
        if expected_precision_limit:
            warning.append(
                "PRECISION_LIMITED: independent complex128 source witness and "
                "insufficient Ganak printed resolution; no equivalence certificate "
                "but the same-source Solver workload retains a conditional "
                "CodSpeed WallTime comparison (not a scientific PASS)"
            )
        if b["verdict"] != h["verdict"]:
            warning.append("verdict labeling changed")
        if b["rr_approximate"] != h["rr_approximate"]:
            warning.append("RR approximate provenance changed")
        if case in QASM261_WALLTIME_CASE_IDS:
            warning.append("source-pinned QASM261 Random_Rotation expected NEQ; GPMC invoked")
        elif classify(b["verdict"]) == "not_equivalent":
            warning.append("known external Ganak precision limitation; NOT a scientific PASS")
        b_ms, h_ms = bt["min_ns"] / 1e6, ht["min_ns"] / 1e6
        # Do not merge equivalent and equivalent*: global-phase labels are
        # scientifically distinct and must be compared explicitly.
        same_semantics = b["verdict"] == h["verdict"]
        # A changed verdict does not, by itself, change the measured workload.
        # Independent source-operator evidence + Ganak printed-resolution
        # limitation allow a CONDITIONAL same-source performance comparison.
        # The scientific verdict remains different and is not certified.
        same_workload = (
            b.get("solver_invoked") is True
            and h.get("solver_invoked") is True
            and all(b.get(field) == h.get(field) for field in
                    ("method", "backend", "solver", "strategy", "reverse",
                     "fixture_sha", "pair_variant", "qasm_corpus", "fixture_sha256"))
        )
        workload_comparable = same_workload and (same_semantics or expected_precision_limit)
        delta = 100 * (h_ms / b_ms - 1) if workload_comparable else None
        if not same_semantics:
            warning.append(
                "CONDITIONAL_SAME_WORKLOAD_TIMING: independent source oracle "
                "and Ganak printed-resolution limitation; scientific verdict "
                "differs, performance data retained for diagnostics"
                if expected_precision_limit else
                "INCOMPARABLE_UNEXPLAINED_VERDICT: retain durations, no ratio"
            )
        # Base lacked an explicit distance tolerance and may have used a
        # different classifier policy. Never claim a controlled precision
        # comparison solely from a successful source-pair matrix reference.
        if expected_precision_limit and (
            b.get("approximate_distance_tolerance") is None
            or b.get("approximate_distance_tolerance") !=
               h.get("approximate_distance_tolerance")
        ):
            warning.append("TOLERANCE_PROVENANCE_DIFFERS: historical base "
                           "policy is not proven identical to HEAD")
        # Provenance from the final CodSpeed repetition only. A quantitative
        # limit for *printed* Solver resolution is not an arithmetic error
        # proof; never convert a negative observation to equivalence here.
        for revision, record in (("base", b), ("head", h)):
            reason = record.get("wmc_precision_reason")
            printed = record.get("wmc_printed_verdict")
            if reason or printed:
                warning.append(
                    f"{revision} WMC diagnostics: printed={printed}, reason={reason}"
                )
            resolution = record.get("wmc_print_resolution_distance")
            threshold = record.get("approximate_distance_tolerance")
            if resolution is not None and threshold is not None:
                if not isinstance(resolution, (int, float)) or not math.isfinite(resolution):
                    errors.append(f"{case}/{revision}: invalid printed resolution metadata")
                elif not isinstance(threshold, (int, float)) or not math.isfinite(threshold):
                    errors.append(f"{case}/{revision}: invalid distance tolerance metadata")
                elif resolution > threshold:
                    warning.append(
                        f"{revision} Ganak printed resolution {resolution:.4g} "
                        f"exceeds distance tolerance {threshold:.4g}"
                    )
        for kind, s in (("base", bt), ("head", ht)):
            if s["stdev_ns"] / s["mean_ns"] > .05:
                warning.append(f"{kind} relative stdev exceeds 5%")
        outcome.append({
            "case": case, "base_min_ms": b_ms, "head_min_ms": h_ms,
            "base_mean_ms": bt["mean_ns"] / 1e6,
            "head_mean_ms": ht["mean_ns"] / 1e6,
            "base_std_ms": bt["stdev_ns"] / 1e6,
            "head_std_ms": ht["stdev_ns"] / 1e6,
            "base_cv": bt["stdev_ns"] / bt["mean_ns"],
            "head_cv": ht["stdev_ns"] / ht["mean_ns"],
            "base_rounds": bt["rounds"], "head_rounds": ht["rounds"],
            "median_change_percent": (
                100 * (ht["median_ns"] / bt["median_ns"] - 1)
                if workload_comparable else None
            ),
            "sampling_scope": (
                "same-runner CodSpeed WallTime summary, no per-round paired samples"
            ),

            "change_percent": delta,
            "performance_comparable": workload_comparable,
            "verdict_comparable": same_semantics,
            "performance_comparison_tier": (
                "BLOCKED_WORKLOAD_MISMATCH" if not same_workload else
                "SAME_VERDICT" if same_semantics else
                "CONDITIONAL_GANAK_PRINT_LIMIT" if expected_precision_limit else
                "BLOCKED_UNEXPLAINED_VERDICT"
            ),
            "numeric_tolerance_evidence": (
                {"head_print_resolution_distance": h.get("wmc_print_resolution_distance"),
                 "head_distance_tolerance": h.get("approximate_distance_tolerance"),
                 "independent_source_operator_numerically_consistent": True,
                 "solver_arithmetic_certified": False}
                if expected_precision_limit else None
            ),
            "base_median_ms": bt["median_ns"] / 1e6,
            "head_median_ms": ht["median_ns"] / 1e6,
            "verdict_base": b["verdict"], "verdict_head": h["verdict"],
            "wmc_diagnostics_base": {
                key: b.get(key) for key in (
                    "wmc_precision_reason", "wmc_printed_verdict",
                    "wmc_print_resolution_distance", "approximate_distance_tolerance",
                    "wmc_numerical_verdict",
                )
            },
            "wmc_diagnostics_head": {
                key: h.get(key) for key in (
                    "wmc_precision_reason", "wmc_printed_verdict",
                    "wmc_print_resolution_distance", "approximate_distance_tolerance",
                    "wmc_numerical_verdict",
                )
            },
            "solver_invoked_base": b["solver_invoked"],
            "solver_invoked_head": h["solver_invoked"],
            "warning": warning,
        })

    header = [
        "## Paired Solver-inclusive CodSpeed WallTime",
        f"Base: \x60{base_sha}\x60; HEAD: \x60{head_sha}\x60.",
        "Source: pytest-codspeed WallTime (minimum across instrumented rounds). "
        "Same shared GitHub hosted runner, **not** a qualified CodSpeed Macro runner; "
        "these percent deltas are exploratory, not certified regressions.",
        "",
        "| Case | Base (ms) | HEAD (ms) | Time change | Verdict (base -> HEAD) | Notes |",
        "|---|---:|---:|---:|---|---|",
    ]
    for x in outcome:
        notes = "; ".join(x["warning"]) or "solver invoked in both"
        header.append(
            f"| {x['case']} | {x['base_min_ms']:.2f} | {x['head_min_ms']:.2f} "
            f"| {format_change(x['change_percent'])} | "
            f"{x['verdict_base']} -> {x['verdict_head']} | {notes} |"
        )
    evidence_status = ("FAIL" if errors else "PRECISION_LIMITED"
                       if precision_incomparable else "PASS")
    header += ["", f"Coverage: {len(outcome)} exact case pairs, {len(times)} instrumented samples.",
               "**Semantic/stage evidence:** " + evidence_status,
               f"Precision-limited verdict-mismatch pairs with conditional timing: {len(precision_incomparable)}.",
               "PRECISION_LIMITED is not a scientific equivalence PASS.", ""]
    if errors:
        header.extend(["Errors:"] + [f"- {error}" for error in errors])
    return {"base_sha": base_sha, "head_sha": head_sha, "cases": outcome,
            "errors": errors, "precision_incomparable": precision_incomparable,
            "conditional_timing_cases": list(precision_incomparable),
            "status": evidence_status}, "\n".join(header) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--measurements", type=Path, required=True)
    p.add_argument("--provenance", type=Path, required=True)
    p.add_argument("--source-oracle", type=Path, required=True)
    p.add_argument("--base-sha", required=True)
    p.add_argument("--head-sha", required=True)
    p.add_argument("--markdown", type=Path, required=True)
    p.add_argument("--json", type=Path, required=True)
    p.add_argument("--summary", type=Path)
    p.add_argument("--required-cases", nargs='+', choices=sorted(EXPECTED))
    a = p.parse_args()
    report, markdown = produce(
        json.loads(a.measurements.read_text(encoding="utf-8")),
        [json.loads(line) for line in a.provenance.read_text(encoding="utf-8").splitlines() if line.strip()],
        a.base_sha, a.head_sha,
        json.loads(a.source_oracle.read_text(encoding="utf-8")),
        required_cases=a.required_cases,
    )
    a.markdown.write_text(markdown, encoding="utf-8")
    a.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if a.summary is not None:
        with a.summary.open("a", encoding="utf-8") as f:
            f.write(markdown)
    print(markdown)
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

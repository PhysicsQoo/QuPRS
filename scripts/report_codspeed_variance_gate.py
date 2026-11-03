#!/usr/bin/env python3
"""P5: source-verified CodSpeed A/B sampling diagnostics, NEVER a GO gate.

The input report is from the official paired WallTime instrument on the same
GitHub runner. Rounded summaries cannot recover paired rounds/correlation or
characterize Macro Runner noise. A confidence/variance-controlled regression
decision requires a separately executed, counterbalanced experiment.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

# Only missing or unverified measurement/workload evidence blocks a timing
# comparison. Runner noise and printed-count precision remain nonblocking
# interpretation caveats; no statistical regression gate is installed.


def produce(report: dict, *, expected_count=9) -> dict:
    if not report.get("head_sha") or not report.get("base_sha"):
        raise ValueError("missing verified base/head source SHA")
    cases = report.get("cases")
    if not isinstance(cases, list) or len(cases) != expected_count:
        raise ValueError(f"expected {expected_count} same-case WallTime base/HEAD pairs")
    if len({row.get("case") for row in cases}) != expected_count:
        raise ValueError("duplicate paired case identity")
    checked = []
    for row in cases:
        key = row["case"]
        reasons = []
        caveats = []
        changed_verdict = row.get("verdict_base") != row.get("verdict_head")
        category = row.get("performance_comparison_tier")
        proven_print_limit = category == "CONDITIONAL_GANAK_PRINT_LIMIT"
        numeric = row.get("numeric_tolerance_evidence") or {}
        print_width, distance_tol = (
            numeric.get("head_print_resolution_distance"),
            numeric.get("head_distance_tolerance"),
        )
        precision_witness_ok = (
            proven_print_limit
            and numeric.get("independent_source_operator_numerically_consistent") is True
            and numeric.get("solver_arithmetic_certified") is False
            and isinstance(print_width, (int, float)) and math.isfinite(print_width)
            and isinstance(distance_tol, (int, float)) and math.isfinite(distance_tol)
            and 0 < distance_tol < print_width
        )
        comparable = row.get("performance_comparable") is True
        # Do not let a caller mark an unexplained verdict change comparable.
        if changed_verdict and not precision_witness_ok:
            comparable = False
            reasons.append("INCOMPARABLE_VERDICT")
        elif changed_verdict:
            caveats.extend(("PRECISION_LIMITED", "VERDICT_CHANGED_NUMERICAL_LIMIT"))
            if any("TOLERANCE_PROVENANCE_DIFFERS" in str(w)
                   for w in row.get("warning", [])):
                caveats.append("TOLERANCE_PROVENANCE_DIFFERS")
        if not comparable and "INCOMPARABLE_VERDICT" not in reasons:
            reasons.append("INCOMPARABLE_VERDICT")
        if not row.get("solver_invoked_base") or not row.get("solver_invoked_head"):
            reasons.append("MISSING_SOLVER_STAGE")
            comparable = False
        if any("NOT a scientific PASS" in str(w) or "PRECISION_LIMITED" in str(w)
               for w in row.get("warning", [])):
            caveats.append("PRECISION_LIMITED")
        for rev in ("base", "head"):
            if rev+"_rounds" not in row or rev+"_cv" not in row or rev+"_median_ms" not in row:
                reasons.append("MISSING_ROUND_DISTRIBUTION")
                break
            n, cv, median = row[rev+"_rounds"], row[rev+"_cv"], row[rev+"_median_ms"]
            if (not isinstance(n, int) or n < 2
                or not isinstance(cv, (float, int)) or not math.isfinite(cv) or cv < 0
                or not isinstance(median, (float, int)) or not math.isfinite(median) or median <= 0):
                raise ValueError(f"{key}: invalid CodSpeed sample metadata for {rev}")
        caveats.append("UNKNOWN_RUNNER_STABILITY")  # Not a comparison veto.
        change = None
        cv = None
        if "MISSING_ROUND_DISTRIBUTION" not in reasons and comparable:
            change = 100 * (row["head_median_ms"] / row["base_median_ms"] - 1)
            # Diagnostic *only*: an unpaired approximation to relative
            # standard error, NOT a confidence interval on true speedup.
            cv = 100 * math.sqrt(row["base_cv"]**2 / row["base_rounds"]
                                 + row["head_cv"]**2 / row["head_rounds"])
        observation_status = (
            "NOT_COMPARABLE" if change is None
            else "CONDITIONAL_PRECISION_LIMIT" if changed_verdict
            else "OBSERVED_DIRECTION_ONLY"
        )
        checked.append({
            "case": key, "verdict_base": row.get("verdict_base"),
            "verdict_head": row.get("verdict_head"),
            "verdict_comparable": not changed_verdict,
            "conditional_timing_comparable": bool(
                changed_verdict and precision_witness_ok and comparable
            ),
            "performance_comparison_tier": (
                "CONDITIONAL_GANAK_PRINT_LIMIT" if (
                    changed_verdict and precision_witness_ok and comparable
                )
                else "BLOCKED_UNEXPLAINED_VERDICT" if changed_verdict
                else "SAME_VERDICT"
            ),
            "category": "EXTERNAL_SOLVER_PRINT_LIMITED" if "PRECISION_LIMITED" in caveats
                        else "SAME_CASE_SOLVER_INCLUSIVE",
            "base_rounds": row.get("base_rounds"), "head_rounds": row.get("head_rounds"),
            "base_cv": row.get("base_cv"), "head_cv": row.get("head_cv"),
            "exploratory_median_change_percent": change,
            "unpaired_relative_se_percent_diagnostic_only": cv,
            "blocking_reasons": sorted(set(reasons)),
            "nonblocking_interpretation_caveats": sorted(set(caveats)),
            "observation_status": observation_status,
            "release_gate_effect": "NONE",
            "performance_decision": "NOT_CERTIFIED",
        })
    return {
        "schema": "quprs-codspeed-p5-variance-gate-v1",
        "base_sha": report["base_sha"], "head_sha": report["head_sha"],
        "input_science_status": report.get("status"),
        "case_count": len(checked), "cases": checked,
        "collection_status": "PAIRED_ROUND_SUMMARIES_AVAILABLE" if all(
            "MISSING_ROUND_DISTRIBUTION" not in row["blocking_reasons"]
            for row in checked) else "INCOMPLETE_SAMPLE_SUMMARIES",
        "scientific_status": report.get("status", "UNKNOWN"),
        "performance_status": "NOT_CERTIFIED",
        "observation_policy": "OBSERVATION_ONLY_NO_FIXED_THRESHOLD",
        "release_gate_enabled": False,
        "default_regression_threshold": None,
        "optional_only_if_formal_gate_reconsidered": [
            "Raw same-case per-round values with counterbalanced base/HEAD order",
            "Stable CodSpeed Macro Runner or independently qualified same-cohort noise",
            "Enough rounds to resolve each case's empirical variance",
            "Identical source QASM, method and Solver stage; a changed verdict needs "
            "independent source witness and quantified precision limitation, with "
            "conditional timing only and NOT a scientific PASS",
            "Timeout censoring: never use timeout bound as measured duration",
        ],
        "scope": "CodSpeed same-runner WallTime only; no mixed CPU/WallTime ratios",
        "interpretation_policy": (
            "Source-matched measured deltas remain readable; runner noise and "
            "precision caveats do not suppress valid timing observations or "
            "alter scientific verdicts. No performance gate blocks release."
        ),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--paired-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--summary", type=Path)
    p.add_argument("--expected-count", type=int, default=9)
    a = p.parse_args()
    report = produce(json.loads(a.paired_report.read_text(encoding="utf-8")), expected_count=a.expected_count)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    rows = [
        "## P5 CodSpeed WallTime observations (no automatic performance gate)",
        "Source: same runner, nine source-pinned base/HEAD Solver-inclusive WallTime pairs (seven original + two QASM261 negative).",
        "Median changes show observed direction, not statistical significance; "
        "runner noise is a nonblocking caveat.",
        "Ganak near-equal source cases may retain CONDITIONAL timing deltas "
        "without certifying the mismatched numerical verdict.",
        "",
        "| Circuit | base/head rounds | CV base/head | Median change | Interpretation |",
        "|---|---:|---:|---:|---|",
    ]
    for x in report["cases"]:
        cv1, cv2 = x["base_cv"], x["head_cv"]
        cvs = f"{cv1:.2%}/{cv2:.2%}" if cv1 is not None and cv2 is not None else "MISSING"
        change = x["exploratory_median_change_percent"]
        rows.append(
            f"| {x['case']} | {x['base_rounds']}/{x['head_rounds']} | "
            f"{cvs} | {f'{change:+.2f}%' if change is not None else 'N/A'} "
            f"| {x['observation_status']} |"
        )
    if a.summary:
        with a.summary.open("a", encoding="utf-8") as stream:
            stream.write("\n".join(rows)+"\n")
    print("\n".join(rows))


if __name__ == "__main__":
    main()

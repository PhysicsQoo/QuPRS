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

BLOCKS = ("INCOMPARABLE_VERDICT", "MISSING_ROUND_DISTRIBUTION",
          "UNKNOWN_RUNNER_STABILITY", "PRECISION_LIMITED")


def produce(report: dict, *, expected_count=7) -> dict:
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
        comparable = row.get("performance_comparable") is True
        if not comparable:
            reasons.append("INCOMPARABLE_VERDICT")
        if not row.get("solver_invoked_base") or not row.get("solver_invoked_head"):
            reasons.append("MISSING_SOLVER_STAGE")
        if any("NOT a scientific PASS" in str(w) or "PRECISION_LIMITED" in str(w)
               for w in row.get("warning", [])):
            reasons.append("PRECISION_LIMITED")
        for rev in ("base", "head"):
            if rev+"_rounds" not in row or rev+"_cv" not in row or rev+"_median_ms" not in row:
                reasons.append("MISSING_ROUND_DISTRIBUTION")
                break
            n, cv, median = row[rev+"_rounds"], row[rev+"_cv"], row[rev+"_median_ms"]
            if (not isinstance(n, int) or n < 2
                or not isinstance(cv, (float, int)) or not math.isfinite(cv) or cv < 0
                or not isinstance(median, (float, int)) or not math.isfinite(median) or median <= 0):
                raise ValueError(f"{key}: invalid CodSpeed sample metadata for {rev}")
        reasons.append("UNKNOWN_RUNNER_STABILITY")  # CI is not Macro Runner.
        change = None
        cv = None
        if "MISSING_ROUND_DISTRIBUTION" not in reasons and comparable:
            change = 100 * (row["head_median_ms"] / row["base_median_ms"] - 1)
            # Diagnostic *only*: an unpaired approximation to relative
            # standard error, NOT a confidence interval on true speedup.
            cv = 100 * math.sqrt(row["base_cv"]**2 / row["base_rounds"]
                                 + row["head_cv"]**2 / row["head_rounds"])
        checked.append({
            "case": key, "verdict_base": row.get("verdict_base"),
            "verdict_head": row.get("verdict_head"),
            "category": "EXTERNAL_SOLVER_PRINT_LIMITED" if "PRECISION_LIMITED" in reasons
                        else "SAME_CASE_SOLVER_INCLUSIVE",
            "base_rounds": row.get("base_rounds"), "head_rounds": row.get("head_rounds"),
            "base_cv": row.get("base_cv"), "head_cv": row.get("head_cv"),
            "exploratory_median_change_percent": change,
            "unpaired_relative_se_percent_diagnostic_only": cv,
            "blocking_reasons": sorted(set(reasons)),
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
        "default_regression_threshold": None,
        "required_next_evidence": [
            "Raw same-case per-round values with counterbalanced base/HEAD order",
            "Stable CodSpeed Macro Runner or independently qualified same-cohort noise",
            "Enough rounds to resolve each case's empirical variance",
            "Identical QASM, method, Solver stage, tolerance and precision verdict",
            "Timeout censoring: never use timeout bound as measured duration",
        ],
        "scope": "CodSpeed same-runner WallTime only; no mixed CPU/WallTime ratios",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--paired-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--summary", type=Path)
    p.add_argument("--expected-count", type=int, default=7)
    a = p.parse_args()
    report = produce(json.loads(a.paired_report.read_text(encoding="utf-8")), expected_count=a.expected_count)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    rows = [
        "## P5 CodSpeed paired variance diagnostics (not performance GO)",
        "Source: same runner, seven source-pinned base/HEAD Solver-inclusive WallTime pairs.",
        "No statistically calibrated 1% threshold; raw counterbalanced rounds missing.",
        "",
        "| Circuit | base/head rounds | CV base/head | Median change | Status |",
        "|---|---:|---:|---:|---|",
    ]
    for x in report["cases"]:
        cv1, cv2 = x["base_cv"], x["head_cv"]
        cvs = f"{cv1:.2%}/{cv2:.2%}" if cv1 is not None and cv2 is not None else "MISSING"
        change = x["exploratory_median_change_percent"]
        rows.append(
            f"| {x['case']} | {x['base_rounds']}/{x['head_rounds']} | "
            f"{cvs} | {f'{change:+.2f}%' if change is not None else 'N/A'} "
            "| NOT_CERTIFIED |"
        )
    if a.summary:
        with a.summary.open("a", encoding="utf-8") as stream:
            stream.write("\n".join(rows)+"\n")
    print("\n".join(rows))


if __name__ == "__main__":
    main()

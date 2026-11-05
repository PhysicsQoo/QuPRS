"""Unit tests for CodSpeed's paired, SHA-specific WallTime report classifier.

All durations here are synthetic parser fixtures, NOT performance timings.
"""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "report_codspeed_paired_walltime.py"
spec = importlib.util.spec_from_file_location("paired_report", SCRIPT)
report_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report_module)


def sample():
    measurement = {"instrument": {"type": "walltime"}, "benchmarks": []}
    records = []
    for case in sorted(report_module.EXPECTED):
        for revision in ("base", "head"):
            measurement["benchmarks"].append({
                "uri": "benchmarks/codspeed/test_pr_solver_walltime.py::"
                       f"test_pr_solver_inclusive_walltime[{case}-{revision}]",
                "stats": {
                    "min_ns": 1_000_000_000.0 if revision == "base" else 1_050_000_000.0,
                    "median_ns": 1_010_000_000.0,
                    "mean_ns": 1_010_000_000.0,
                    "stdev_ns": 10_000_000.0,
                    "rounds": 3, "iter_per_round": 1,
                },
            })
            solver = "ganak" if "ganak" in case else "gpmc"
            versioned_negative = case.startswith("q261_")
            records.append({
                "case": case, "revision": revision,
                "sha": "base-sha" if revision == "base" else "head-sha",
                "fixture_sha": "head-sha",
                "method": "wmc_only" if case == "q261_qaoa7_negative_wmconly" else "hybrid",
                "backend": "python" if "python" in case else "rust",
                "solver": solver, "strategy": "proportional",
                "reverse": False, "solver_invoked": True,
                "verdict": "not_equivalent" if versioned_negative else "equivalent",
                "rr_approximate": False,
                "verification_status": "EXPECTED_SOURCE_NEGATIVE" if versioned_negative else "PASS",
                "pair_variant": "random_rotation" if versioned_negative else "transpiled",
                "qasm_corpus": "qiskit-2.6.1-opt0" if versioned_negative else "historical",
                "fixture_sha256": ["a" * 64, "b" * 64] if versioned_negative else None,
                "effective_rr_tolerance": 1e-10,
                "effective_distance_tolerance": 1e-8,
                "effective_phase_tolerance": 1e-8,
                "effective_gpmc_digits": 90,
            })
    return measurement, records


def test_exact_ten_pairs_keep_original_nine_and_new_wmc_only_separate():
    instrument, records = sample()
    report, markdown = report_module.produce(instrument, records, "base-sha", "head-sha")
    assert report["status"] == "PASS"
    assert len(report["cases"]) == 10
    assert {x["case"] for x in report["cases"] if x["case"].startswith("q261_")} == {
        "q261_qaoa7_negative", "q261_qft16_negative", "q261_qaoa7_negative_wmconly",
    }
    assert all(abs(x["change_percent"] - 5) < 1e-10 for x in report["cases"])
    assert "shared" in markdown.lower()


def test_mismatched_verdict_blocks_semantic_parity():
    instrument, records = sample()
    next(x for x in records if x["case"] == "vqe4_gpmc" and x["revision"] == "head")["verdict"] = "not_equivalent"
    report, _ = report_module.produce(instrument, records, "base-sha", "head-sha")
    assert report["status"] == "FAIL"
    assert any("semantic category changed" in err for err in report["errors"])


def test_unknown_solver_stage_and_sha_are_blocking():
    instrument, records = sample()
    row = next(x for x in records if x["case"] == "qft16_gpmc" and x["revision"] == "head")
    row["solver_invoked"] = False
    row["sha"] = "old-head"
    report, _ = report_module.produce(instrument, records, "base-sha", "head-sha")
    assert report["status"] == "FAIL"
    assert any("Solver was not actually invoked" in e for e in report["errors"])
    assert any("SHA" in e for e in report["errors"])


def test_missing_measurement_rejected():
    instrument, records = sample()
    instrument["benchmarks"].pop()
    with pytest.raises(ValueError, match="Incomplete/extra paired coverage"):
        report_module.produce(instrument, records, "base-sha", "head-sha")


def test_known_ganak_negative_is_timing_only():
    instrument, records = sample()
    for row in records:
        if row["case"] == "vqe4_ganak":
            row["verdict"] = "not_equivalent"
            row["verification_status"] = "EXTERNAL_GANAK_PRINT_LIMITATION"
    report, _ = report_module.produce(instrument, records, "base-sha", "head-sha")
    assert report["status"] == "PASS"
    row = next(x for x in report["cases"] if x["case"] == "vqe4_ganak")
    assert any("NOT a scientific PASS" in warning for warning in row["warning"])


def test_ganak_verdict_change_never_publishes_a_performance_delta():
    instrument, records = sample()
    row = next(x for x in records if x["case"] == "vqe4_ganak"
               and x["revision"] == "head")
    row["verdict"] = "not_equivalent"
    row["verification_status"] = "EXTERNAL_GANAK_PRINT_LIMITATION"
    result, markdown = report_module.produce(instrument, records, "base-sha", "head-sha")
    assert result["status"] == "FAIL"  # Scientific/stage gate stays strict.
    candidate = next(x for x in result["cases"] if x["case"] == "vqe4_ganak")
    assert candidate["change_percent"] is None
    assert candidate["performance_comparable"] is False
    assert candidate["base_min_ms"] > 0 and candidate["head_min_ms"] > 0
    assert "N/A (verdict changed)" in markdown


def test_phase_label_changes_are_incomparable():
    instrument, records = sample()
    row = next(x for x in records
               if x["case"] == "vqe4_gpmc" and x["revision"] == "head")
    row["verdict"] = "equivalent*"
    result, markdown = report_module.produce(instrument, records, "base-sha", "head-sha")
    candidate = next(x for x in result["cases"] if x["case"] == "vqe4_gpmc")
    assert result["status"] == "FAIL"
    assert candidate["change_percent"] is None
    assert candidate["performance_comparable"] is False
    assert "N/A (verdict changed)" in markdown


def test_precision_provenance_survives_without_changing_scientific_result():
    instrument, records = sample()
    row = next(x for x in records
               if x["case"] == "vqe4_ganak" and x["revision"] == "head")
    row.update(wmc_precision_reason="ganak_point_estimate_resolution_limited",
               wmc_printed_verdict="unknown_resolution",
               wmc_print_resolution_distance=0.00014,
               approximate_distance_tolerance=1e-8,
               wmc_numerical_verdict="not_equivalent",
               verdict="not_equivalent",
               verification_status="EXTERNAL_GANAK_PRINT_LIMITATION")
    result, markdown = report_module.produce(instrument, records, "base-sha", "head-sha")
    candidate = next(x for x in result["cases"] if x["case"] == "vqe4_ganak")
    assert result["status"] == "FAIL"
    assert candidate["performance_comparable"] is False
    assert candidate["wmc_diagnostics_head"]["wmc_printed_verdict"] == "unknown_resolution"
    assert "Ganak printed resolution" in markdown


def test_known_ganak_coarse_print_retains_conditional_timing_not_science_go():
    measurement, records = sample()
    # The real compared Ganak source baseline is equivalent* (global phase).
    # Keep the production classifier strict; correct the synthetic fixture.
    base = next(x for x in records if x["case"] == "vqe4_ganak" and x["revision"] == "base")
    base["verdict"] = "equivalent*"
    head = next(x for x in records if x["case"] == "vqe4_ganak" and x["revision"] == "head")
    head.update(verdict="not_equivalent",
                verification_status="EXTERNAL_GANAK_PRINT_LIMITATION",
                wmc_printed_verdict="unknown",
                wmc_precision_reason="ganak_point_estimate_resolution_limited",
                wmc_numerical_verdict="not_equivalent",
                wmc_print_resolution_distance=0.0001161,
                approximate_distance_tolerance=1e-8)
    source = {"schema": "source-qasm-global-phase-double-v1",
              "fixture_sha": "head-sha", "certified_epsilon_distance": False,
              "cases": {"vqe4": {
                  "numerically_consistent_up_to_global_phase": True,
                  "phase_corrected_frobenius_normalized": 2e-15,
                  "qasm_sha256": ["a" * 64, "b" * 64],
              }}}
    result, markdown = report_module.produce(
        measurement, records, "base-sha", "head-sha", source)
    assert result["status"] == "PRECISION_LIMITED"
    assert result["errors"] == []
    assert result["precision_incomparable"] == ["vqe4_ganak"]
    case = next(x for x in result["cases"] if x["case"] == "vqe4_ganak")
    assert case["change_percent"] is not None
    assert case["median_change_percent"] is not None
    assert case["verdict_comparable"] is False
    assert case["performance_comparable"] is True
    assert case["performance_comparison_tier"] == "CONDITIONAL_GANAK_PRINT_LIMIT"
    assert result["conditional_timing_cases"] == ["vqe4_ganak"]
    assert case["numeric_tolerance_evidence"]["solver_arithmetic_certified"] is False
    assert "CONDITIONAL_SAME_WORKLOAD_TIMING" in markdown
    assert "PRECISION_LIMITED is not a scientific equivalence PASS" in markdown
    assert report_module.produce(measurement, records, "base-sha", "head-sha",
                                 dict(source, fixture_sha="wrong"))[0]["status"] == "FAIL"
    head["wmc_print_resolution_distance"] = 1e-9
    assert report_module.produce(measurement, records, "base-sha", "head-sha",
                                 source)[0]["status"] == "FAIL"


def make_legacy_base_unavailable(measurement, records, cases=None):
    """Synthetic unavailable BASE source; NOT measured zero or a Solver failure."""
    cases = cases or report_module.QASM261_WALLTIME_CASE_IDS
    measurement["benchmarks"] = [
        row for row in measurement["benchmarks"]
        if not any(row["uri"].endswith(f"[{case}-base]") for case in cases)
    ]
    for case in cases:
        row = next(x for x in records if x["case"] == case and x["revision"] == "base")
        row.update(
            verdict=None, solver_invoked=None,
            verification_status="NOT_COMPARABLE_LEGACY_BASE",
            capability_reason="Legacy dev GPMC distance precision not proven to be 90",
            requested_contract={
                "rr_tolerance": 1e-10, "approximate_distance_tolerance": 1e-8,
                "wmc_phase_tolerance": 1e-8, "gpmc_precision_digits": 90,
            },
        )


def test_legacy_unavailable_base_preserves_seven_pairs_and_three_real_head_samples():
    measurement, records = sample()
    make_legacy_base_unavailable(measurement, records)
    result, markdown = report_module.produce(measurement, records, "base-sha", "head-sha")
    assert result["status"] == "BASE_CAPABILITY_LIMITED"
    assert result["errors"] == []
    assert result["paired_measured_cases"] == 7
    assert result["head_only_cases"] == 3
    assert len(result["cases"]) == 10
    assert len(measurement["benchmarks"]) == 17
    for row in result["cases"]:
        if row["case"].startswith("q261_"):
            assert row["base_median_ms"] is None
            assert row["change_percent"] is None
            assert row["head_median_ms"] > 0
            assert row["performance_comparison_tier"] == "NOT_COMPARABLE_LEGACY_BASE"
        else:
            assert row["base_median_ms"] > 0
            assert row["change_percent"] is not None
    assert "7 exact case pairs" in markdown
    assert "N/A (legacy capability)" in markdown


def test_unexplained_missing_base_remains_fatal():
    measurement, records = sample()
    measurement["benchmarks"] = [
        row for row in measurement["benchmarks"]
        if not row["uri"].endswith("[q261_qft16_negative-base]")
    ]
    with pytest.raises(ValueError, match="Incomplete/extra paired coverage"):
        report_module.produce(measurement, records, "base-sha", "head-sha")


def test_legacy_capability_forgery_or_missing_head_stays_fatal():
    measurement, records = sample()
    make_legacy_base_unavailable(measurement, records,
                                 {"q261_qft16_negative"})
    base = next(x for x in records if x["case"] == "q261_qft16_negative"
                and x["revision"] == "base")
    base["sha"] = "forged-base"
    report, _ = report_module.produce(measurement, records, "base-sha", "head-sha")
    assert report["status"] == "FAIL"
    assert any("incorrect source/fixture SHA" in e for e in report["errors"])
    base["sha"] = "base-sha"
    base["requested_contract"]["gpmc_precision_digits"] = 30
    report, _ = report_module.produce(measurement, records, "base-sha", "head-sha")
    assert report["status"] == "FAIL"
    assert any("invalid source-capability evidence" in e for e in report["errors"])
    base["requested_contract"]["gpmc_precision_digits"] = 90
    measurement["benchmarks"] = [
        row for row in measurement["benchmarks"]
        if not row["uri"].endswith("[q261_qft16_negative-head]")
    ]
    with pytest.raises(ValueError, match="Incomplete/extra paired coverage"):
        report_module.produce(measurement, records, "base-sha", "head-sha")


def test_legacy_classification_not_allowed_for_historical_or_head_case():
    measurement, records = sample()
    make_legacy_base_unavailable(measurement, records, {"vqe4_gpmc"})
    with pytest.raises(ValueError, match="only allowed on QASM261 base"):
        report_module.produce(measurement, records, "base-sha", "head-sha")

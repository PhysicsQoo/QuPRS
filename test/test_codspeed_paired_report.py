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
                "fixture_sha": "head-sha", "method": "hybrid",
                "backend": "python" if "python" in case else "rust",
                "solver": solver, "strategy": "proportional",
                "reverse": False, "solver_invoked": True,
                "verdict": "not_equivalent" if versioned_negative else "equivalent",
                "rr_approximate": False,
                "verification_status": "EXPECTED_SOURCE_NEGATIVE" if versioned_negative else "PASS",
                "pair_variant": "random_rotation" if versioned_negative else "transpiled",
                "qasm_corpus": "qiskit-2.6.1-opt0" if versioned_negative else "historical",
                "fixture_sha256": ["a" * 64, "b" * 64] if versioned_negative else None,
            })
    return measurement, records


def test_exact_nine_pairs_keep_legacy_and_qasm261_separate():
    instrument, records = sample()
    report, markdown = report_module.produce(instrument, records, "base-sha", "head-sha")
    assert report["status"] == "PASS"
    assert len(report["cases"]) == 9
    assert {x["case"] for x in report["cases"] if x["case"].startswith("q261_")} == {
        "q261_qaoa7_negative", "q261_qft16_negative",
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

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
            records.append({
                "case": case, "revision": revision,
                "sha": "base-sha" if revision == "base" else "head-sha",
                "fixture_sha": "head-sha", "method": "hybrid",
                "backend": "python" if "python" in case else "rust",
                "solver": solver, "strategy": "proportional",
                "reverse": False, "solver_invoked": True,
                "verdict": "equivalent", "rr_approximate": False,
                "verification_status": "PASS",
            })
    return measurement, records


def test_exact_seven_pairs_emit_codspeed_percentages():
    instrument, records = sample()
    report, markdown = report_module.produce(instrument, records, "base-sha", "head-sha")
    assert report["status"] == "PASS"
    assert len(report["cases"]) == 7
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

"""Controlled repeatability report: exact four sources, five real CodSpeed rounds."""
import copy
import importlib.util
from pathlib import Path

import pytest

from benchmarks.codspeed.case_registry import REPEATABILITY_EXPECTATIONS

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "repeatability_report", ROOT / "scripts" / "report_codspeed_repeatability.py")
SCRIPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCRIPT)
SHA = "a" * 40


def fixtures():
    measurements = {"instrument": {"type": "walltime"}, "benchmarks": []}
    science = []
    oracle = {"schema": "source-qasm-global-phase-double-v1",
              "fixture_sha": SHA, "cases": {}}
    for case, (verdict, invoked) in REPEATABILITY_EXPECTATIONS.items():
        measurements["benchmarks"].append({
            "uri": (
                "benchmarks/codspeed/test_codspeed_repeatability.py::"
                f"test_bounded_same_sha_repeatability[{case}]"
            ),
            "stats": {
                "rounds": 5, "iter_per_round": 1,
                "min_ns": 760_000_000, "median_ns": 800_000_000,
                "mean_ns": 810_000_000, "stdev_ns": 10_000_000,
            },
        })
        calls = [{
            "status": "COMPLETED", "verdict": verdict,
            "solver_invoked": invoked, "exit_code": 0,
        } for _ in range(6)]
        science.append({
            "case": case, "sha": SHA,
            "qasm_sha256": ["a" * 64, "b" * 64],
            "all_invocations_scientifically_consistent": True,
            "observed_invocations_including_instrument_warmup": 6,
            "expected_verdict": verdict, "expected_solver_invoked": invoked,
            "observations": calls, "precision_reasons": [],
        })
        oracle["cases"][case] = {
            "qasm_sha256": ["a" * 64, "b" * 64],
            "numerically_consistent_up_to_global_phase": True,
            "phase_corrected_frobenius_normalized": 1e-14,
            "relative_global_phase_rad": 0.0,
        }
    return measurements, science, oracle


def test_four_cases_have_real_rounds_and_no_composite_speedup():
    a, b, c = fixtures()
    report = SCRIPT.produce(a, b, c, SHA)
    assert len(report["cases"]) == 4
    assert report["all_cases_qualified_source_and_stage"]
    assert not report["performance_certified"]
    assert not report["solver_arithmetic_certified"]
    assert sum(x["category"] == "Solver-inclusive Hybrid"
               for x in report["cases"]) == 2
    assert all(x["measurement_rounds"] == 5 for x in report["cases"])


def test_missing_round_is_rejected():
    a, b, c = fixtures()
    a["benchmarks"][0]["stats"]["rounds"] = 4
    with pytest.raises(ValueError, match="insufficient"):
        SCRIPT.produce(a, b, c, SHA)


def test_unverified_qasm_source_is_rejected():
    a, b, c = fixtures()
    c["cases"]["qnn4"]["qasm_sha256"][1] = "c" * 64
    with pytest.raises(ValueError, match="SHA256"):
        SCRIPT.produce(a, b, c, SHA)


def test_verdict_or_solver_stage_mismatch_is_rejected():
    a, b, c = fixtures()
    b[0]["observations"][2]["solver_invoked"] = not b[0]["observations"][2]["solver_invoked"]
    with pytest.raises(ValueError, match="timeout or semantic mismatch"):
        SCRIPT.produce(a, b, c, SHA)


def test_missing_benchmark_measurement_is_rejected():
    a, b, c = fixtures()
    a["benchmarks"].pop()
    with pytest.raises(ValueError, match="exact 4 cases"):
        SCRIPT.produce(a, b, c, SHA)

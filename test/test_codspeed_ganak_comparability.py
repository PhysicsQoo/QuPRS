"""Cross-version Ganak printed-resolution disagreements keep conditional timings.

These cases have an independent operator witness but NOT a certified Ganak
arithmetic error bound. A different verdict alone is not an automatic ban on
measuring an otherwise matching Solver-inclusive workload.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


paired = load("paired_precision_timing", "scripts/report_codspeed_paired_walltime.py")
p5 = load("p5_precision_timing", "scripts/report_codspeed_variance_gate.py")
BASE, HEAD = "b" * 40, "a" * 40


def fixture(*, width=0.00011613350730964658, oracle_valid=True,
            head_verdict="not_equivalent", head_solver_invoked=True):
    case = "vqe4_ganak"
    stats = {"rounds": 3, "iter_per_round": 1,
             "min_ns": 1_050_000_000, "median_ns": 1_078_500_000,
             "mean_ns": 1_080_000_000, "stdev_ns": 8_000_000}
    times = {"instrument": {"type": "walltime"}, "benchmarks": []}
    provenance = []
    for revision, sha in (("base", BASE), ("head", HEAD)):
        times["benchmarks"].append({
            "uri": (f"benchmarks/codspeed/test_pr_solver_walltime.py::"
                    f"test_pr_solver_inclusive_walltime[{case}-{revision}]"),
            "stats": dict(stats, median_ns=(1_055_800_000 if revision == "head"
                                            else 1_078_500_000)),
        })
        base = revision == "base"
        provenance.append({
            "case": case, "revision": revision, "sha": sha,
            "fixture_sha": HEAD, "solver_invoked": True if base else head_solver_invoked,
            "method": "hybrid", "backend": "rust", "solver": "ganak",
            "strategy": "proportional", "reverse": False,
            "verdict": "equivalent*" if base else head_verdict,
            "verification_status": ("PASS" if base else
                                    "EXTERNAL_GANAK_PRINT_LIMITATION"),
            "rr_approximate": None if base else False,
            "wmc_printed_verdict": None if base else "unknown",
            "wmc_numerical_verdict": "equivalent*" if base else "not_equivalent",
            "wmc_precision_reason": (None if base else
                                      "ganak_point_estimate_resolution_limited"),
            "wmc_print_resolution_distance": None if base else width,
            "approximate_distance_tolerance": None if base else 1e-8,
        })
    witness = {
        "schema": "source-qasm-global-phase-double-v1",
        "fixture_sha": HEAD, "certified_epsilon_distance": False,
        "cases": {"vqe4": {
            "phase_corrected_frobenius_normalized": 2.5e-15,
            "numerically_consistent_up_to_global_phase": oracle_valid,
            "qasm_sha256": ["a" * 64, "b" * 64]
        }},
    }
    return times, provenance, witness


def test_ganak_verdict_mismatch_is_conditional_timing_not_science_pass():
    times, provenance, witness = fixture()
    report, md = paired.produce(times, provenance, BASE, HEAD, witness,
                                required_cases=["vqe4_ganak"])
    row = report["cases"][0]
    assert report["status"] == "PRECISION_LIMITED"
    assert report["conditional_timing_cases"] == ["vqe4_ganak"]
    assert row["verdict_comparable"] is False
    assert row["performance_comparable"] is True
    assert row["performance_comparison_tier"] == "CONDITIONAL_GANAK_PRINT_LIMIT"
    assert row["median_change_percent"] is not None
    assert row["median_change_percent"] < 0
    assert row["numeric_tolerance_evidence"]["solver_arithmetic_certified"] is False
    assert "TOLERANCE_PROVENANCE_DIFFERS" in " ".join(row["warning"])
    assert "CONDITIONAL_SAME_WORKLOAD_TIMING" in md
    audit = p5.produce(report, expected_count=1)
    audited = audit["cases"][0]
    assert audited["conditional_timing_comparable"] is True
    assert audited["exploratory_median_change_percent"] < 0
    # Printed-count limits affect numerical interpretation, not the
    # comparability of source-matched CodSpeed WallTime measurements.
    assert "PRECISION_LIMITED" in audited["nonblocking_interpretation_caveats"]
    assert "TOLERANCE_PROVENANCE_DIFFERS" in audited["nonblocking_interpretation_caveats"]
    assert "PRECISION_LIMITED" not in audited["blocking_reasons"]
    assert "INCOMPARABLE_VERDICT" not in audited["blocking_reasons"]
    assert audited["observation_status"] == "CONDITIONAL_PRECISION_LIMIT"
    assert audited["release_gate_effect"] == "NONE"
    assert audit["performance_status"] == "NOT_CERTIFIED"
    assert audit["default_regression_threshold"] is None


def test_changed_verdict_without_numerical_oracle_is_not_comparable():
    times, provenance, witness = fixture(oracle_valid=False)
    report, _ = paired.produce(times, provenance, BASE, HEAD,
                               witness, required_cases=["vqe4_ganak"])
    row = report["cases"][0]
    assert report["errors"]
    assert row["performance_comparable"] is False
    assert row["median_change_percent"] is None
    audit = p5.produce(report, expected_count=1)
    assert "INCOMPARABLE_VERDICT" in audit["cases"][0]["blocking_reasons"]


def test_precision_width_inside_tolerance_is_not_automatic_exception():
    times, provenance, witness = fixture(width=1e-9)
    report, _ = paired.produce(times, provenance, BASE, HEAD, witness,
                               required_cases=["vqe4_ganak"])
    assert report["errors"]
    assert report["cases"][0]["median_change_percent"] is None


def test_solver_stage_change_disallows_scientific_acceptance():
    times, provenance, witness = fixture(head_solver_invoked=False)
    report, _ = paired.produce(times, provenance, BASE, HEAD, witness,
                               required_cases=["vqe4_ganak"])
    assert report["errors"]
    assert report["cases"][0]["performance_comparable"] is False
    assert report["cases"][0]["median_change_percent"] is None
    assert "Solver was not actually invoked" in " ".join(report["errors"])

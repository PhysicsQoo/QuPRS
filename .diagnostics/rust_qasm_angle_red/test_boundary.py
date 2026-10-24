"""Source-semantic RED, outside normal pytest testpaths, without xfail/skip."""
import json
from fractions import Fraction
from pathlib import Path
import pytest

CASES = {
    "tiny_positive_1e12", "tiny_negative_1e12",
    "tiny_positive_1e10", "above_epsilon_below_denom",
    "denominator_boundary",
}


@pytest.fixture(scope="module")
def report():
    path = Path(__file__).resolve().parent / "results" / "angle-boundary.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def by_name(report):
    return {row["case"]: row for row in report["cases"]}


def test_independent_exact_source_oracles(report):
    """Source truth is rational, not close-to-one floating-point testing."""
    assert report["native_solver_called"] is False
    assert report["wmc_tolerance_used"] is False
    assert len(report["cases"]) == 8
    for case in report["cases"]:
        source = Fraction(case["exact_source_radians"])
        assert bool(source) == case["exact_source_nonzero"]
        gap = Fraction(case["lower_bound_on_strict_magnitude_defect"])
        if source:
            assert abs(source) < 1
            assert 0 < gap < 1
            assert case["certified_non_equivalent_up_to_global_phase"] is True
            assert Fraction(case["normalized_trace_upper"]) < 1
        else:
            assert gap == 0
            assert case["certified_non_equivalent_up_to_global_phase"] is False


def test_true_zero_and_retained_angle_controls(by_name):
    assert by_name["zero"]["rust_angle_zero"] is True
    assert by_name["zero"]["pathsum_identity_after_rust_parse"] is True
    for name in ("retained_small", "retained_reference"):
        row = by_name[name]
        assert row["exact_source_nonzero"] is True
        assert row["rust_angle_zero"] is False
        assert row["pathsum_identity_after_rust_parse"] is False


def test_stage_attribution_controls(by_name):
    """A pre-WMC observation cannot be attributed to WMC tolerance."""
    assert by_name["zero"]["stage_classification"] == "ZERO_REFERENCE_CONTROL"
    for name in ("tiny_positive_1e12", "tiny_negative_1e12"):
        row = by_name[name]
        if row["rust_angle_zero"]:
            assert row["stage_classification"] == "ANGLE_CONVERSION_LOSS_BEFORE_WMC"
            assert row["pathsum_identity_after_rust_parse"] is True


@pytest.mark.parametrize("name", sorted(CASES))
def test_nonzero_qasm_rotation_must_survive_rust_angle_conversion_red(by_name, name):
    """A nonzero rotation must never silently become an identity operation."""
    row = by_name[name]
    assert row["certified_non_equivalent_up_to_global_phase"]
    assert row["rust_angle_zero"] is False, (
        f"PRE-WMC SOURCE SEMANTIC LOSS for {name}: exact source angle "
        f"{row['exact_source_radians']} radians != 0, but actual Rust QASM "
        f"Angle is {row['rust_angle_numerator']}/{row['rust_angle_denominator']} "
        f"(PathSum identity={row['pathsum_identity_after_rust_parse']}). "
        "This is a parser/representation RED, not a weighted-model-count "
        "solver error and not a numerical WMC acceptance-band error."
    )
    assert row["pathsum_identity_after_rust_parse"] is False

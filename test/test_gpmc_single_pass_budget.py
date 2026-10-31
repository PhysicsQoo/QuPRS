"""Single-run GPMC conditional classification and solver boundaries."""
from fractions import Fraction

from QuPRS.utils.precision_count import (
    parse_printed_count_line, classify_observed_distance,
)
from QuPRS.utils.gpmc_distance_budget import classify_gpmc_single_count


def printed(real, imag="0.00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"):
    return parse_printed_count_line(
        "c s exact double prec-sci " + real + " + " + imag + "e+00i"
    )


def classify(real, *, epsilon=1e-8):
    return classify_gpmc_single_count(
        printed(real), expected_twice_log2=0,
        distance_tolerance=epsilon, phase_tolerance=1e-8,
        cnf_vars=2, number_of_weights=1,
        maximum_weight_magnitude_squared=Fraction(1),
        precision_digits=90,
    )


def test_single_pass_detects_count_below_distance_threshold():
    observed = classify("9.9999999999995065197799455360500000000000000000000000000000000000000000000000000000000000000000000e-01")
    assert observed.status == "not_equivalent"
    assert observed.printed_status == "not_equivalent"
    assert observed.component_error is not None
    assert not observed.solver_arithmetic_certified


def test_single_pass_positive_is_conditional_not_certified():
    observed = classify("1.00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e+00")
    assert observed.status == "equivalent"
    assert observed.reason.startswith("single_pass_uncertified_")
    assert not observed.source_weight_certified


def test_single_pass_unresolved_native_printing_stays_unknown():
    count = parse_printed_count_line(
        "c s exact quadruple float 1.00000000e+00 + 0.00000000e+00i"
    )
    observed = classify_gpmc_single_count(
        count, expected_twice_log2=0, distance_tolerance=1e-8,
        phase_tolerance=1e-8, cnf_vars=2, number_of_weights=1,
        maximum_weight_magnitude_squared=Fraction(1), precision_digits=90,
    )
    # Public numerical observation uses the single printed midpoint. The
    # unresolved printed interval must remain visible and uncertified.
    assert observed.status == "equivalent"
    assert observed.printed_status == "unknown"
    assert observed.reason.startswith("single_pass_uncertified_")
    assert not observed.solver_arithmetic_certified
    assert not observed.source_weight_certified


def test_single_pass_rejects_unsupported_weight_budget():
    count = printed("1.00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e+00")
    result = classify_gpmc_single_count(
        count, expected_twice_log2=0, distance_tolerance=1e-8,
        phase_tolerance=1e-8, cnf_vars=900, number_of_weights=1,
        maximum_weight_magnitude_squared=Fraction(1), precision_digits=90,
    )
    assert result.status == "unknown"
    assert result.model_status == "unknown"
    # No supported error *certificate* does not veto the public distance.
    assert result.numerical_verdict == "equivalent"


def test_single_pass_positive_phase_uses_common_contract():
    count = parse_printed_count_line(
        "c s exact double prec-sci 0.00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e+00 + 1.00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e+00i"
    )
    result = classify_gpmc_single_count(
        count, expected_twice_log2=0, distance_tolerance=1e-8,
        phase_tolerance=1e-8, cnf_vars=2, number_of_weights=1,
        maximum_weight_magnitude_squared=Fraction(1), precision_digits=90,
    )
    comparable, _ = classify_observed_distance(
        count, 0, 1e-8, 1e-8,
        component_error=Fraction(result.component_error),
    )
    assert result.status == comparable == "equivalent*"

"""Tiny printed magnitude overshoots respect the requested projective distance."""
from QuPRS.utils.precision_count import (
    classify_printed_distance,
    classify_observed_distance,
    parse_printed_solver_output,
)


def _gpmc(value: str):
    return parse_printed_solver_output(
        "c o precision 30\n"
        f"c s exact double prec-sci 0 + {value}i"
    )


def test_tiny_overshoot_returns_equivalent_up_to_phase():
    count = _gpmc("1.00000000000000000000000000001")
    printed = classify_printed_distance(count, 0, 1e-8)
    assert printed.status == "equivalent"
    assert printed.reason == "printed_distance_within_threshold"
    verdict, evidence = classify_observed_distance(count, 0, 1e-8, 1e-8)
    assert verdict == "equivalent*"
    assert evidence == printed


def test_large_overshoot_warns_without_vetoing_distance():
    count = _gpmc("1.000000000001")
    verdict, evidence = classify_observed_distance(count, 0, 1e-8, 1e-8)
    assert verdict == "equivalent*"
    assert evidence.status == "unknown"
    assert evidence.reason == "distance_interval_outside_tolerance"


def test_tight_precision_and_distinct_circuit():
    tiny = _gpmc("1.00000000000000000000000000001")
    assert classify_observed_distance(tiny, 0, 1e-16, 1e-8)[0] == "equivalent*"
    distinct = _gpmc("0.999999999999")
    assert classify_observed_distance(distinct, 0, 1e-8, 1e-8)[0] == "not_equivalent"

def test_wide_interval_crossing_upper_distance_bound_is_unknown():
    from fractions import Fraction
    from QuPRS.utils.precision_count import PrintedCount
    sample = PrintedCount(
        real=Fraction(0), imag=Fraction(1),
        real_print_half_unit=Fraction(0),
        imag_print_half_unit=Fraction(1, 10**8),
        format_name="c s exact double prec-sci",
    )
    observed = classify_printed_distance(sample, 0, 1e-8)
    assert observed.status == "unknown"
    assert observed.reason == "insufficient_printed_resolution"
    verdict, evidence = classify_observed_distance(sample, 0, 1e-8, 1e-8)
    # A purely imaginary unit count has global phase pi/2; the public
    # point estimate is equivalent*, while the printed interval stays unknown.
    assert verdict == "equivalent*"
    assert evidence == observed

def test_ganak_print_resolution_does_not_change_numeric_distance():
    count = parse_printed_solver_output(
        "c s exact octuple float 0 + 1.00000000e+00i"
    )
    status, evidence = classify_observed_distance(count, 0, 1e-8, 1e-8)
    assert status == "equivalent*"
    assert evidence.status == "unknown"
    assert evidence.reason == "insufficient_printed_resolution"


def test_count_just_below_distance_cutoff_is_not_equivalent():
    count = _gpmc("0.99999999999999994")
    status, _ = classify_observed_distance(count, 0, 1e-8, 1e-8)
    assert status == "not_equivalent"

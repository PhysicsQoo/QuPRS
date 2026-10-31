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
    assert printed.reason == "printed_magnitude_within_distance_tolerance"
    verdict, evidence = classify_observed_distance(count, 0, 1e-8, 1e-8)
    assert verdict == "equivalent*"
    assert evidence == printed


def test_large_overshoot_remains_unknown():
    count = _gpmc("1.000000000001")
    evidence = classify_printed_distance(count, 0, 1e-8)
    assert evidence.status == "unknown"
    assert evidence.reason == "nonphysical_magnitude_overshoot"


def test_tight_precision_and_distinct_circuit():
    tiny = _gpmc("1.00000000000000000000000000001")
    assert classify_observed_distance(tiny, 0, 1e-16, 1e-8)[0] == "unknown"
    distinct = _gpmc("0.999999999999")
    assert classify_observed_distance(distinct, 0, 1e-8, 1e-8)[0] == "not_equivalent"

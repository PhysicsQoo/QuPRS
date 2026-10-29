"""Numerical source/solver-output precision contracts for the Python backend."""
from decimal import Decimal
from fractions import Fraction
import pytest
from pathlib import Path

from QuPRS.utils.precision_count import (
    PrintedCount, classify_printed_distance, parse_printed_count_line,
    parse_printed_solver_output,
)


def count(value, prefix="c s exact octuple float"):
    return parse_printed_count_line(prefix + " " + value)


@pytest.mark.parametrize("format_name", [
    "c s exact double prec-sci", "c s exact arb cpx",
    "c s exact half float", "c s exact single float",
    "c s exact double float", "c s exact quadruple float",
    "c s exact octuple float",
])
def test_printed_complex_decimal_retained_before_f64(format_name):
    observed = count("9.9999999999999994746875000000000000000117e-01 + 0.000000e+00i", format_name)
    assert observed.real < 1
    assert float(observed.real) == 1.0
    assert observed.imag == 0
    assert not classify_printed_distance(observed, 0, 1e-8).certified_solver_bound


@pytest.mark.parametrize("bits,printed", [
    (128, "9.9999999999999994746875000000000000000117e-01"),
    (256, "9.9999999999999994746875000000000000000000000000000000000000000000000000000000181e-01"),
])
def test_print_resolution_changes_distance_verdict(bits, printed):
    _ = bits
    baseline = count("1.00000000e+00 + 0.00000000e+00i", "c s exact quadruple float")
    candidate = count(printed + " + 0.00000000e+00i")
    assert classify_printed_distance(baseline, 0, 1e-8).status == "unknown"
    assert classify_printed_distance(candidate, 0, 1e-8).status == "not_equivalent"
    assert classify_printed_distance(candidate, 0, 2e-8).status == "equivalent"
    # No binary64 reduction at a 2^2 count normalization.
    scaled = PrintedCount(candidate.real * 4, candidate.imag * 4,
                          candidate.real_print_half_unit * 4,
                          candidate.imag_print_half_unit * 4, candidate.format_name)
    assert classify_printed_distance(scaled, 4, 1e-8).status == "not_equivalent"


def test_nonphysical_overshoot_and_malformed_fail_closed():
    over = count("1.0000000000000000525312499999999999999988e+00 + 0e+00i")
    assert classify_printed_distance(over, 0, 1e-8).reason == "nonphysical_magnitude_overshoot"
    with pytest.raises(ValueError, match="conflicting"):
        parse_printed_solver_output(
            "c s exact octuple float 1e0 + 0e0i\n"
            "c s exact quadruple float 2e0 + 0e0i\n"
        )
    for invalid in ("nan", "inf", "1e9999", "1/0", "1e-2-3e+i"):
        with pytest.raises(ValueError):
            count(invalid)


def test_fraction_count_and_precision_dont_claim_solver_certification():
    fraction = count("3/2 - 1/4i", "c s exact arb frac")
    assert fraction.real == Fraction(3, 2)
    assert fraction.imag == Fraction(-1, 4)
    assert fraction.real_print_half_unit == 0
    assert fraction.imag_print_half_unit == 0
    assert not classify_printed_distance(fraction, 0, 1e-8).certified_solver_bound


def test_adapter_native_transport_uses_decimal_before_legacy_float():
    from contextlib import contextmanager
    from types import SimpleNamespace
    from QuPRS.utils.solver_adapter import execute_solver, get_solver_adapter

    @contextmanager
    def solver(name):
        assert name == "gpmc"
        yield "/fixtures/gpmc"

    stdout = (
        "c s exact double prec-sci "
        "9.9999999999999994746875000000000000000117e-01 + 0e+00i"
    )

    def execute(command, *, timeout):
        assert command == ["/fixtures/gpmc", "-mode=1", "fixture.cnf"]
        assert timeout > 0
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    adapter = get_solver_adapter("gpmc")
    precise = execute_solver(adapter, "fixture.cnf", 5, resource_resolver=solver,
                             process_runner=execute, capture_decimal=True)
    legacy = execute_solver(adapter, "fixture.cnf", 5, resource_resolver=solver,
                            process_runner=execute)
    assert precise.count.real < Fraction(1)
    assert legacy.count == complex(1.0, 0.0)
    assert classify_printed_distance(precise.count, 0, 1e-8).status == "not_equivalent"


@pytest.mark.parametrize("row", [
    line for line in (
        Path(__file__).resolve().parents[1]
        / "test/fixtures/printed_distance_parity.tsv"
    ).read_text().splitlines()
    if line and not line.startswith("#")
])
def test_python_rust_printed_distance_contract(row):
    name, stdout, exponent, epsilon, component_error, expected = row.split("\t")
    verdict = classify_printed_distance(
        parse_printed_solver_output(stdout), int(exponent), float(epsilon),
        component_error=Fraction(Decimal(component_error)),
    )
    assert (
        ("unknown_overshoot" if verdict.reason == "nonphysical_magnitude_overshoot"
         else "unknown_resolution" if verdict.status == "unknown"
         else verdict.status)
    ) == expected, name


def test_printed_distance_rejects_invalid_component_error():
    observed = count("1/1", "c s exact arb frac")
    with pytest.raises(ValueError, match="Component error"):
        classify_printed_distance(observed, 0, 1e-8, component_error=Fraction(-1))


def test_printed_log_diagnostic_handles_counts_beyond_f64_range():
    from QuPRS.utils.precision_count import approximate_printed_log2
    enormous = PrintedCount(
        Fraction(1 << 1300), Fraction(0), Fraction(0), Fraction(0),
        "c s exact arb frac",
    )
    assert approximate_printed_log2(enormous) == 1300.0
    complex_count = PrintedCount(
        Fraction(3), Fraction(4), Fraction(0), Fraction(0),
        "c s exact arb frac",
    )
    assert abs(approximate_printed_log2(complex_count) -
               2.321928094887362) < 1e-13

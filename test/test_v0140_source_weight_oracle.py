"""v0.14.0 source-to-printed-CNF arithmetic controls.

An exact oracle of a printed weighted CNF is deliberately not a proof of the
original quantum circuit or of general solver internal numerical arithmetic.
"""
from fractions import Fraction

import pytest

from QuPRS import check_equivalence
from _v0140_exact_printed_gpmc_oracle import (
    count_printed_cnf_exact, exact_count_distance_classification,
)

HEADER = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'


@pytest.mark.parametrize(
    "operation,expected",
    [
        ("rz(0.00032) q[0];", "equivalent"),
        ("rz(0.00048) q[0];", "not_equivalent"),
        ("s q[0]; x q[0]; s q[0]; x q[0];", "equivalent*"),
    ],
)
def test_real_gpmc_count_agrees_with_exact_printed_cnf(
    operation, expected, monkeypatch, record_property
):
    """One real GPMC solve, independent exact rational count of same CNF."""
    from QuPRS.interface import ps2wmc

    recorded = {"cnf": None, "count": None, "calls": 0}
    real_encode = ps2wmc.to_DIMACS
    real_run = ps2wmc.run_wmc

    def capture_cnf(*args, **kwargs):
        value = real_encode(*args, **kwargs)
        recorded["cnf"] = value
        return value

    def capture_solver(*args, **kwargs):
        recorded["calls"] += 1
        assert recorded["calls"] == 1, "Production distance mode must not replay GPMC"
        assert kwargs.get("preserve_count") is True
        assert kwargs.get("precision_digits") == 90
        observed = real_run(*args, **kwargs)
        recorded["count"] = observed
        return observed

    monkeypatch.setattr(ps2wmc, "to_DIMACS", capture_cnf)
    monkeypatch.setattr(ps2wmc, "run_wmc", capture_solver)

    result = check_equivalence(
        HEADER, HEADER + operation + "\n",
        method="wmc_only", backend="python", strategy="Naive",
        tool_name="gpmc", timeout=45, approximate_distance_tolerance=2e-4,
    )
    assert recorded["calls"] == 1
    assert result.wmc_solver_invoked is True
    # An ideal global phase is physically inside the distance threshold,
    # but the *uncertified* input/solver uncertainty model may report unknown.
    # That is an inconclusive limitation, not a failed physics oracle.
    if expected == "equivalent*":
        assert result.equivalent in ("equivalent*", "unknown"), (
            operation, result.equivalent, result.wmc_precision_reason,
            result.wmc_printed_verdict,
        )
        if result.equivalent == "unknown":
            assert result.wmc_precision_reason is not None
    else:
        assert result.equivalent == expected, (
            operation, result.equivalent, result.wmc_precision_reason,
            result.wmc_printed_verdict,
        )
    assert recorded["cnf"] and recorded["count"] is not None
    exact = count_printed_cnf_exact(recorded["cnf"])
    assert exact["status"] == "observed"
    assert exact["variables"] <= 12

    count = recorded["count"]
    # The two counts have the same *printed decimal CNF weights* as input.
    # Do not interpret this empirical gap as a source or generic solver bound.
    max_scale = max(Fraction(1), abs(exact["real"]), abs(exact["imag"]))
    empirical_gap = max(
        abs(exact["real"] - count.real),
        abs(exact["imag"] - count.imag),
    )
    assert empirical_gap < Fraction(1, 10**48) * max_scale, empirical_gap
    expected_twice = int(round(2 * result.expect))
    exact_direction = exact_count_distance_classification(
        exact["real"], exact["imag"], expected_twice, 2e-4,
    )
    if expected == "not_equivalent":
        assert exact_direction == "not_equivalent", (operation, exact_direction)
    else:
        # Printed decimal trigonometric weights can yield a tiny arithmetic
        # overshoot even for a truly unitary global phase; not a proof.
        assert exact_direction in (
            "inside_threshold", "unknown_overshoot"
        ), (operation, exact_direction)
    record_property("source_weight_oracle", "exact_printed_cnf_only")
    record_property("cnf_variables", str(exact["variables"]))
    record_property("solver_invocations", "1")
    record_property("printed_count_empirical_max_component_error", str(empirical_gap))
    record_property("observed_numerical_verdict", result.equivalent)
    record_property("printed_verdict", str(result.wmc_printed_verdict))
    record_property("precision_reason", str(result.wmc_precision_reason))
    record_property(
        "evidence_category",
        "INCONCLUSIVE_NUMERIC" if result.equivalent == "unknown"
        else "OBSERVED_NUMERIC",
    )


def test_rust_binary64_weight_is_a_distinct_precision_boundary():
    """A source difference can be exact while native f64 values alias."""
    from decimal import Decimal
    left = Decimal("0.000000020000000000000000000000")
    right = Decimal("0.000000020000000000000000000001")
    assert left != right
    assert float(left) == float(right)
    # This demonstrates representation loss only, not a native verifier bug
    # and not a statement that the two circuits are distinguishable at eps_D.

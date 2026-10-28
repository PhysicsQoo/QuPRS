"""Regression: source phase preservation and tolerance-dependent cache invalidation.

These controls intentionally use distinct representations of the same Rz
rotation. Solver verdicts are numerical policies, not exact certificates.
"""
import math

import pytest
import symengine as se
from qiskit import QuantumCircuit

from QuPRS import check_equivalence, config
from QuPRS.utils.util import reduce_expression


@pytest.fixture
def restore_reduction_tolerance():
    original = config.get_tolerance()
    try:
        yield
    finally:
        config.set_tolerance(original)


def test_reduction_cache_tracks_tolerance_switch_both_directions(
    restore_reduction_tolerance,
):
    # 5e-7 cycles: nonzero at 1e-10, deleted at 1e-6.
    x = se.Symbol("tolerance_cache_probe")
    term = se.Rational(1, 2_000_000) * x

    config.set_tolerance(1e-10)
    retained = reduce_expression(term)
    assert retained != se.S.Zero

    config.set_tolerance(1e-6)
    assert reduce_expression(term) == se.S.Zero

    config.set_tolerance(1e-10)
    assert reduce_expression(term) == retained


@pytest.mark.parametrize(
    "invalid",
    [True, False, None, "", "1e-8", 0, -1, math.nan, math.inf, -math.inf],
)
def test_invalid_symbolic_tolerance_does_not_change_configuration(
    invalid, restore_reduction_tolerance,
):
    before = config.get_tolerance()
    with pytest.raises(ValueError, match="Tolerance"):
        config.set_tolerance(invalid)
    assert config.get_tolerance() == before


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        ("reduction_rules", "unknown"),
        ("hybrid", "not_equivalent"),
        ("wmc_only", "not_equivalent"),
    ],
)
@pytest.mark.parametrize("tolerance", [1e-10, 1e-6])
def test_nonzero_gate_phase_survives_construction_for_all_methods(
    method, expected, tolerance, restore_reduction_tolerance,
):
    # 200 * 3e-6 = 6e-4 radians; ideal normalized trace magnitude
    # defect is about 4.5e-8, greater than the 1e-8 WMC threshold.
    lhs = QuantumCircuit(1)
    repeated = QuantumCircuit(1)
    combined = QuantumCircuit(1)
    for _ in range(200):
        repeated.rz(3e-6, 0)
    combined.rz(0.0006, 0)

    config.set_tolerance(tolerance)
    verdicts = []
    counts = []
    for target in (repeated, combined):
        result = check_equivalence(
            lhs,
            target,
            backend="python",
            method=method,
            strategy="Naive",
            tool_name="gpmc",
            timeout=30,
            wmc_magnitude_tolerance=1e-8,
            wmc_phase_tolerance=1e-8,
        )
        assert result.equivalent == expected
        verdicts.append(result.equivalent)
        if method != "reduction_rules":
            assert result.tool_time is not None
            counts.append(result.log_wmc)
        else:
            assert result.tool_time is None

    assert verdicts == [expected, expected]
    if method != "reduction_rules":
        assert len(counts) == 2
        assert math.isclose(counts[0], counts[1], rel_tol=0, abs_tol=1e-12)

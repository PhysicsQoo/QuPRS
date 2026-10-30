"""Regression: source phase preservation and tolerance-dependent cache invalidation.

These controls intentionally use distinct representations of the same Rz
rotation. Solver verdicts are numerical policies, not exact certificates.
"""
import math

import pytest
import symengine as se
from qiskit import QuantumCircuit

from QuPRS import check_equivalence
from QuPRS.utils.verification_tolerances import current_rr_tolerance, DEFAULT_RR_TOLERANCE
from QuPRS.utils.util import reduce_expression


def test_reduction_cache_tracks_tolerance_switch_both_directions():
    # 5e-7 cycles: nonzero at 1e-10, deleted at 1e-6.
    x = se.Symbol("tolerance_cache_probe")
    term = se.Rational(1, 2_000_000) * x

    retained = reduce_expression(term, rr_tolerance=1e-10)
    assert retained != se.S.Zero

    assert reduce_expression(term, rr_tolerance=1e-6) == se.S.Zero
    assert reduce_expression(term, rr_tolerance=1e-10) == retained
    assert current_rr_tolerance() == DEFAULT_RR_TOLERANCE


@pytest.mark.parametrize(
    "invalid",
    [True, False, "", "1e-8", 0, -1, math.nan, math.inf, -math.inf],
)
def test_invalid_per_call_rr_tolerance_rejected(invalid):
    before = current_rr_tolerance()
    with pytest.raises(ValueError, match="rr_tolerance"):
        check_equivalence(QuantumCircuit(1), QuantumCircuit(1), rr_tolerance=invalid)
    assert current_rr_tolerance() == before


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
    method, expected, tolerance,
):
    # 200 * 3e-6 = 6e-4 radians; ideal normalized trace magnitude
    # defect is about 4.5e-8, greater than the 1e-8 WMC threshold.
    lhs = QuantumCircuit(1)
    repeated = QuantumCircuit(1)
    combined = QuantumCircuit(1)
    for _ in range(200):
        repeated.rz(3e-6, 0)
    combined.rz(0.0006, 0)

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
            phase_tolerance=1e-8,
            rr_tolerance=tolerance,
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

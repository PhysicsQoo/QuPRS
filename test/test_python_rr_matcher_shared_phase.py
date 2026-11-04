"""RR matcher phase sharing matches standalone behavior without a solver."""
import pytest
import symengine as se

from QuPRS.pathsum.pattern_match import match_HH, match_omega
from QuPRS.utils.util import reduce_expression
from QuPRS.utils.verification_tolerances import (
    begin_rr_approximation_tracking, finish_rr_approximation_tracking,
    rr_approximation_used, scoped_rr_tolerance,
)


@pytest.mark.parametrize("tolerance", [0.0, 1e-8])
def test_omega_reuses_expanded_normalized_phase_and_provenance(tolerance):
    y, z = se.symbols("shared_omega_y shared_omega_z")
    with scoped_rr_tolerance(tolerance):
        phase = reduce_expression(
            y * (se.Rational(1, 4) + z / 2) + se.Rational(1, 10**11),
            preserve_scalar=True,
        )
        assert phase == phase.expand()
        args = (phase, (y,), (y, z), ())
        token = begin_rr_approximation_tracking()
        try:
            baseline = match_omega(*args)
            base_approximate = rr_approximation_used()
        finally:
            finish_rr_approximation_tracking(token)
        token = begin_rr_approximation_tracking()
        try:
            optimized = match_omega(
                *args, coeff_cache={}, expanded_phase=phase,
                valid_symbols={str(y), str(z)},
            )
            new_approximate = rr_approximation_used()
        finally:
            finish_rr_approximation_tracking(token)
    # The current Omega matcher accepts the approximate branch at 1e-8,
    # while strict RR (tolerance=0) leaves this particular coefficient
    # unmatched. This test asserts the observed eligibility separately
    # from the optimization's requirement of identical matcher results.
    assert baseline[0] == (y if tolerance > 0 else None)
    assert baseline == optimized
    assert base_approximate == new_approximate


@pytest.mark.parametrize("tolerance", [0.0, 1e-8])
def test_hh_reuses_failed_omega_coefficients(tolerance):
    y, z = se.symbols("shared_hh_y shared_hh_z")
    with scoped_rr_tolerance(tolerance):
        phase = reduce_expression(
            y * z / 2 + z / 8 + se.Rational(1, 10**11),
            preserve_scalar=True,
        )
        assert phase == phase.expand()
        args = (phase, (y,), (y, z), ())
        cache = {}
        omega = match_omega(
            *args, coeff_cache=cache, expanded_phase=phase,
            valid_symbols={str(y), str(z)},
        )
        assert omega[0] is None
        assert y in cache
        baseline = match_HH(*args)
        optimized = match_HH(
            *args, coeff_cache=cache, expanded_phase=phase,
            valid_symbols={str(y), str(z)},
        )
    assert baseline[:2] == (y, z)
    assert baseline == optimized


def test_standalone_matcher_still_expands_unexpanded_expression():
    y, z = se.symbols("standalone_match_y standalone_match_z")
    source = y * (se.Rational(1, 4) + z / 2)
    with scoped_rr_tolerance(0):
        assert match_omega(source, (y,), (y, z), ()) == match_omega(
            source.expand(), (y,), (y, z), (),
        )

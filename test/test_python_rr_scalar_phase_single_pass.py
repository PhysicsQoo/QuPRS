"""Python RR phase-normalization regression, independent of external solvers."""
import symengine as se

from QuPRS.pathsum.core import PathSum
from QuPRS.pathsum.pattern_match import HH_reduction, omega_reduction
from QuPRS.utils.util import reduce_expression
from QuPRS.utils.verification_tolerances import (
    begin_rr_approximation_tracking, finish_rr_approximation_tracking,
    rr_approximation_used, scoped_rr_tolerance,
)

_TINY = se.Rational(1, 10**11)


def _initial(*variables):
    identity = PathSum.QuantumCircuit(1)
    return PathSum(se.S.Zero, identity.f, frozenset(variables))


def test_phase_scalar_survives_rr_tolerance_and_wraps_modulo_one():
    with scoped_rr_tolerance(1e-8):
        assert reduce_expression(_TINY) == se.S.Zero  # coefficient match default
        assert reduce_expression(_TINY, preserve_scalar=True) == _TINY
        assert reduce_expression(-_TINY, preserve_scalar=True) == se.S.One - _TINY
        x = se.Symbol("scalar_phase_test_x")
        assert reduce_expression(_TINY * x + _TINY, preserve_scalar=True) == _TINY


def test_omega_preserves_tiny_global_phase_before_recursive_rr():
    y = se.Symbol("scalar_phase_omega_y")
    initial = _initial(y)
    with scoped_rr_tolerance(1e-8):
        token = begin_rr_approximation_tracking()
        try:
            reduced = omega_reduction(
                initial, y, se.S.Zero, -se.Rational(1, 8) + _TINY, True
            )
            assert reduced.P == _TINY
            assert not rr_approximation_used()
        finally:
            finish_rr_approximation_tracking(token)


def test_hh_preserves_tiny_global_phase_after_substitution():
    y = se.Symbol("scalar_phase_hh_y")
    z = se.Symbol("scalar_phase_hh_z")
    initial = _initial(y, z)
    with scoped_rr_tolerance(1e-8):
        reduced = HH_reduction(initial, y, z, se.S.Zero, z + _TINY)
        assert reduced.P == _TINY


def test_cache_hits_preserve_approximation_provenance_and_tolerance():
    x = se.Symbol("scalar_phase_cache_x")
    expr = _TINY + _TINY * x
    with scoped_rr_tolerance(1e-8):
        for _ in range(2):
            token = begin_rr_approximation_tracking()
            try:
                assert reduce_expression(expr, preserve_scalar=True) == _TINY
                assert rr_approximation_used() is True
            finally:
                finish_rr_approximation_tracking(token)
    with scoped_rr_tolerance(0):
        token = begin_rr_approximation_tracking()
        try:
            assert reduce_expression(expr, preserve_scalar=True) == expr
            assert rr_approximation_used() is False
        finally:
            finish_rr_approximation_tracking(token)

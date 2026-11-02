"""HH matcher fast-path preserves exact and approximate matching outcomes."""
import pytest
import symengine as se

from QuPRS.pathsum.pattern_match import match_HH
from QuPRS.utils.verification_tolerances import (
    scoped_rr_tolerance, begin_rr_approximation_tracking,
    finish_rr_approximation_tracking, rr_approximation_used,
)


@pytest.mark.parametrize("tol", [0.0, 1e-10, 1e-8])
def test_hh_exact_zero_path_does_not_mark_rr_approximation(tol):
    y, z = se.symbols("hh_fast_yo hh_fast_yi")
    phase = y*z/2 + z/8
    with scoped_rr_tolerance(tol):
        token = begin_rr_approximation_tracking()
        try:
            got = match_HH(phase, (y,), (y, z), ())
            approximated = rr_approximation_used()
        finally:
            finish_rr_approximation_tracking(token)
    assert got[0:2] == (y, z)
    assert got[2].is_zero
    assert approximated is False


@pytest.mark.parametrize("tol", [0.0, 1e-8])
def test_hh_tuple_set_frozenset_membership_identical(tol):
    y,z,w = se.symbols("hh_fast_y hh_fast_z hh_fast_w")
    phase = y*z/2 + w/8
    with scoped_rr_tolerance(tol):
        by_tuple = match_HH(phase, (y,), (y,z,w), ())
        by_set = match_HH(phase, (y,), {y,z,w}, ())
        by_frozenset = match_HH(phase, (y,), frozenset({y,z,w}), ())
    assert by_tuple == by_set == by_frozenset


def test_hh_approximate_threshold_and_exact_boundary_separate():
    y, z = se.symbols("hh_approx_y hh_approx_z")
    delta = se.Rational(1,10**11)
    phase = y*(z/2 + delta)
    with scoped_rr_tolerance(0):
        strict = match_HH(phase,(y,),(y,z),())
    with scoped_rr_tolerance(1e-8):
        approximate = match_HH(phase,(y,),(y,z),())
    assert strict[0] is None
    assert approximate[0] == y

"""Semantics gates for same-attempt Omega/HH expanded-phase reuse.

The candidate may only reuse an immutable expansion inside a single reduction
attempt. Independently tested public Operator cases are in test_backend_semantics.
"""
import symengine as se
import pytest

from QuPRS.pathsum.pattern_match import match_HH, match_omega


@pytest.mark.parametrize("phase", [
    lambda y, z: (y + z) * (y + 2 * z),
    lambda y, z: y * z / 2,
    lambda y, z: y * (se.Rational(1, 4) + z / 2),
    lambda y, z: (y + 1) * (z + se.Rational(3, 4)),
])
def test_matchers_return_identical_result_with_shared_expansion(phase):
    y, z = se.symbols("qoo112_expand_y qoo112_expand_z")
    P = phase(y, z)
    pathvar = (y, z)
    for matcher in (match_omega, match_HH):
        baseline = matcher(P, pathvar, pathvar, ())
        shared = matcher(P, pathvar, pathvar, (), expanded_P=P.expand())
        assert shared == baseline, (matcher.__name__, P, baseline, shared)


@pytest.mark.parametrize("matcher", [match_omega, match_HH])
def test_expanded_phase_does_not_call_original_expand(matcher):
    y, z = se.symbols("qoo112_expand_y qoo112_expand_z")
    P = y * z / 2

    class NeverExpand:
        def expand(self):
            pytest.fail("A pre-expanded immutable phase must not be expanded again")

    expected = matcher(P, (y, z), (y, z), ())
    actual = matcher(NeverExpand(), (y, z), (y, z), (), expanded_P=P.expand())
    assert actual == expected

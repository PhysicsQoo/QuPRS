"""Targeted contracts for same-attempt Omega->HH coefficient reuse.

The full independent dense Qiskit Operator oracle is already provided by
`test_backend_semantics.py` and is executed in the isolated same-host job.
"""
import pytest
import symengine as se

import QuPRS.pathsum.reduction as reduction
from QuPRS.pathsum.core import PathSum
from QuPRS.pathsum.pattern_match import match_HH, match_omega


@pytest.mark.parametrize("phase", [
    lambda y, z: (y + z) * (y + 2 * z),
    lambda y, z: y * z / 2,
    lambda y, z: y * (se.Rational(1, 4) + z / 2),
    lambda y, z: (y + 1) * (z + se.Rational(3, 4)),
])
def test_shared_coefficient_cache_preserves_matcher_results(phase):
    y, z = se.symbols("phase_coeff_yo phase_coeff_yi")
    P = phase(y, z)
    reducible = (y, z)
    omega_plain = match_omega(P, reducible, reducible, ())
    hh_plain = match_HH(P, reducible, reducible, ())

    shared = {}
    omega_cached = match_omega(P, reducible, reducible, (), coeff_cache=shared)
    hh_cached = match_HH(P, reducible, reducible, (), coeff_cache=shared)

    assert omega_cached == omega_plain
    assert hh_cached == hh_plain
    assert shared
    for variable, value in shared.items():
        assert value == P.expand().coeff(variable)


def test_hh_full_cache_skips_expensive_coefficient_lookups():
    y, z = se.symbols("phase_coeff_yo phase_coeff_yi")

    class NoCoeffCalls:
        def expand(self):
            return self

        def coeff(self, variable):
            pytest.fail("Same-attempt cached coefficients must bypass coeff()")

    # The value zero guarantees no HH reduction is found, avoiding any other
    # polynomial operation on this deliberately strict test double.
    empty_coefficient = se.S.Zero
    result = match_HH(NoCoeffCalls(), (y, z), (y, z), (),
                      coeff_cache={y: empty_coefficient, z: empty_coefficient})
    assert result == (None, None, None, None)


def test_fresh_cache_per_reduction_attempt(monkeypatch):
    y, z = se.symbols("phase_coeff_yo phase_coeff_yi")
    base = PathSum.QuantumCircuit(1)
    ps = PathSum(y * z / 2, base.f, frozenset({y, z}))
    seen = []

    def stub_omega(P, reducible, pathvar, bits, *, coeff_cache=None):
        assert coeff_cache == {}
        coeff_cache[y] = se.S.Zero
        seen.append(coeff_cache)
        return None, None, None, None

    def stub_hh(P, reducible, pathvar, bits, *, coeff_cache=None):
        assert coeff_cache is seen[-1]
        return None, None, None, None

    monkeypatch.setattr(reduction, "match_omega", stub_omega)
    monkeypatch.setattr(reduction, "match_HH", stub_hh)
    reduction.apply_reduction(ps)
    reduction.apply_reduction(ps)
    assert len(seen) == 2
    assert seen[0] is not seen[1]

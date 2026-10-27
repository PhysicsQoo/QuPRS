"""Small independent operator/algebra reference controls.

These reference-oracle checks are intentionally *not* tests of QuPRS'
currently unsound WMC/reduction verdicts. See docs/development/
equivalence-semantics.md for the difference between diagnostics and proof.
"""
from decimal import Decimal
from fractions import Fraction
from math import cos, pi

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator


def _matrix(*ops):
    circuit = QuantumCircuit(1)
    for op, value in ops:
        if value is None:
            getattr(circuit, op)(0)
        else:
            getattr(circuit, op)(value, 0)
    return Operator(circuit).data


def _phase_adjusted_max_entry_error(left, right):
    overlap = np.vdot(right.ravel(), left.ravel())
    phase = overlap / abs(overlap) if abs(overlap) > 1e-14 else (1 + 0j)
    return float(np.max(np.abs(left - phase * right)))


def test_exact_identity_and_nonzero_global_phase_are_distinct():
    identity = _matrix()
    minus_identity = _matrix(("x", None), ("z", None),
                             ("x", None), ("z", None))
    assert np.allclose(identity, _matrix(), atol=1e-14)
    assert not np.allclose(identity, minus_identity, atol=1e-14)
    assert _phase_adjusted_max_entry_error(identity, minus_identity) < 1e-14
    assert np.allclose(minus_identity, -identity, atol=1e-14)


@pytest.mark.parametrize("delta", [0.000001, 0.0001, 0.001, 0.01, 0.2])
def test_nonzero_rz_difference_is_never_global_phase(delta):
    identity = _matrix()
    rz = _matrix(("rz", delta))
    residual = _phase_adjusted_max_entry_error(identity, rz)
    expected_normalized_trace = abs(cos(delta / 2))
    actual_normalized_trace = abs(np.trace(identity.conj().T @ rz)) / 2
    assert residual > 0
    assert np.isclose(actual_normalized_trace, expected_normalized_trace,
                      rtol=0, atol=1e-14)
    assert expected_normalized_trace < 1


def test_current_magnitude_band_is_not_equivalence_certificate():
    # This is a mathematical counterexample, not an assertion that the
    # installed backend implements a repaired classification.
    delta = 0.001
    defect = 1 - abs(cos(delta / 2))
    assert 0 < defect < 1e-6
    assert _phase_adjusted_max_entry_error(
        _matrix(), _matrix(("rz", delta))) > 1e-4


def test_basis_action_inequality_survives_phase_optimization():
    assert _phase_adjusted_max_entry_error(
        _matrix(), _matrix(("x", None))) > 0.5


@pytest.mark.parametrize("a,b,combined", [
    ("-2.5802058126763807", "-2.5802058126763807",
     "-5.1604116253527614"),
    ("1.6198837120072371", "-2.5802058126763807",
     "-0.9603221006691436"),
])
def test_exact_decimal_radian_reference_is_additive(a, b, combined):
    left = Fraction(Decimal(a))
    right = Fraction(Decimal(b))
    total = Fraction(Decimal(combined))
    assert left + right == total
    assert total - left - right == 0
    assert total.denominator > 1_000_000_000


def test_symbolic_pi_and_decimal_approximation_are_distinct():
    symbolic_pi_fraction = (Fraction(1, 8), Fraction(0))
    decimal_radians = (Fraction(0), Fraction(Decimal("0.39269908169872414")))
    assert symbolic_pi_fraction != decimal_radians
    assert symbolic_pi_fraction[0] + symbolic_pi_fraction[0] == Fraction(1, 4)


def test_one_parameter_point_does_not_prove_universal_equivalence():
    # RZ(theta) and RZ(2 theta) agree at theta=0, but not at theta=0.2.
    assert _phase_adjusted_max_entry_error(
        _matrix(("rz", 0.0)), _matrix(("rz", 0.0))) < 1e-14
    assert _phase_adjusted_max_entry_error(
        _matrix(("rz", 0.2)), _matrix(("rz", 0.4))) > 1e-4


def test_full_turn_rz_is_global_phase_only():
    identity = _matrix()
    full_turn = _matrix(("rz", 2 * pi))
    assert _phase_adjusted_max_entry_error(identity, full_turn) < 1e-14
    assert not np.allclose(identity, full_turn, atol=1e-14)

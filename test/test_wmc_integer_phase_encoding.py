"""Integer-cycle PathSum phase must never enter GPMC as symbolic weights."""
import math

import symengine as se
from qiskit import QuantumCircuit

from QuPRS import check_equivalence
from QuPRS.interface.ps2wmc import P_to_wlogi


def test_integer_phase_monomials_have_unit_weight():
    y, q = se.symbols("y q")
    for coefficient in (-3, -1, 1, 2, 5):
        assert P_to_wlogi(coefficient * y * q) == []
    result = P_to_wlogi(y * q + se.Rational(1, 4) * y)
    assert len(result) == 1
    assert result[0][0] == se.Rational(1, 4)


def test_exact_qft_style_identity_emits_only_numeric_complex_weights():
    c = QuantumCircuit(2)
    c.h(0)
    c.rz(math.pi / 8, 1)
    c.cx(0, 1)
    c.rz(-math.pi / 8, 1)
    c.cx(0, 1)
    c.h(1)
    result = check_equivalence(
        c, c.copy(), method="wmc_only", backend="python",
        strategy="Naive", tool_name="gpmc", timeout=20,
        approximate_distance_tolerance=2e-4,
    )
    assert result.CNF is not None
    assert "cos(" not in result.CNF
    assert "sin(" not in result.CNF
    assert result.wmc_solver_invoked
    assert result.equivalent in ("equivalent", "equivalent*"), result

def test_scalar_global_phase_is_not_discarded():
    import sympy as sp

    quarter = P_to_wlogi(se.Rational(1, 4))
    assert len(quarter) == 1
    assert quarter[0][0] == se.Rational(1, 4)
    assert quarter[0][1] == sp.true

    y = se.Symbol("y")
    mixed = P_to_wlogi(se.Rational(1, 4) + y)
    assert len(mixed) == 1
    assert mixed[0][0] == se.Rational(1, 4)
    assert mixed[0][1] == sp.true

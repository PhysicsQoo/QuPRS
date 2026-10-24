"""Reduction-only exact global-phase label audit on the genuine Rust FFI.

These assert a strict mathematical distinction that the native verifier
previously blurred using a float phase tolerance of 1e-6.
No solver, benchmark, or numeric WMC classification is involved.
"""
import math

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence


def verify(lhs, rhs):
    return check_equivalence(
        lhs, rhs, backend="rust", method="reduction_rules",
        strategy="Naive", tool_name="gpmc", timeout=30,
    )


@pytest.mark.parametrize("denominator", [1000, 10_000_000])
@pytest.mark.parametrize("reverse", [False, True])
def test_rz_versus_p_tiny_exact_global_phase_not_exact_equality(denominator, reverse):
    # Exact source spelling is a rational pi multiplier, not a decimal
    # approximation of pi. The induced scalar is exp(-i*pi/(2*denom)).
    qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    left = qasm + f'rz(pi/{denominator}) q[0];'
    right = qasm + f'p(pi/{denominator}) q[0];'
    result = verify(right, left) if reverse else verify(left, right)
    assert result.equivalent == "equivalent*", (denominator, reverse, result.equivalent)
    assert result.tool_time is None


@pytest.mark.parametrize("angle", [math.pi / 4, math.pi / 2])
def test_rz_p_scalar_relation_dense_matrix_oracle(angle):
    left, right = QuantumCircuit(1), QuantumCircuit(1)
    left.rz(angle, 0)
    right.p(angle, 0)
    phase = np.exp(-1j * angle / 2)
    np.testing.assert_allclose(
        Operator(left).data,
        phase * Operator(right).data,
        atol=2e-14,
        rtol=0,
    )
    assert verify(left, right).equivalent == "equivalent*"


def test_equal_gate_controls_do_not_invent_phase_or_solver_use():
    a, b = QuantumCircuit(1), QuantumCircuit(1)
    a.p(math.pi / 8, 0)
    b.p(math.pi / 8, 0)
    result = verify(a, b)
    assert result.equivalent == "equivalent"
    assert result.tool_time is None

"""Algebraic CP(phi) lowering and real Rust/Qiskit source checks.

Mathematical identity:
 CP(theta) = P(theta/2)_control · CX · P(-theta/2)_target ·
             CX · P(theta/2)_target
where factors are listed in circuit execution order.
All gate-angle arithmetic within this decomposition is exact relative to
the input Angle representation. Native QASM decimal→Angle approximation
remains an independent, unresolved input precision boundary.
"""
import math
import numpy as np
import pytest

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from QuPRS import check_equivalence


def decompose_cp(theta):
    c = QuantumCircuit(2)
    c.p(theta/2, 0)
    c.cx(0, 1)
    c.p(-theta/2, 1)
    c.cx(0, 1)
    c.p(theta/2, 1)
    return c


@pytest.mark.parametrize("theta", [0.0, math.pi, math.pi/2, 0.125, -0.125])
def test_independent_dense_operator_cp_identity_including_global_phase(theta):
    source = QuantumCircuit(2)
    source.cp(theta, 0, 1)
    expected = decompose_cp(theta)
    # Exact algebraic expression, numerical Qiskit operator is only a
    # float implementation diagnostic, not a rigorous source theorem.
    np.testing.assert_allclose(
        Operator(source).data, Operator(expected).data,
        atol=2e-14, rtol=0,
    )
    np.testing.assert_allclose(
        Operator(source).data,
        np.diag([1, 1, 1, np.exp(1j * theta)]),
        atol=2e-14, rtol=0,
    )


@pytest.mark.parametrize("theta,spelling", [
    ("pi", "cp(pi)"),
    ("pi/2", "cp(pi/2)"),
    ("0.125", "cp(0.125)"),
    ("-0.125", "cp(-0.125)"),
])
def test_real_native_parser_does_not_drop_cp(theta, spelling):
    source = ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\n'
              + f'{spelling} q[0],q[1];')
    empty = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\n'
    result = check_equivalence(
        empty, source, backend="rust", method="reduction_rules",
        strategy="Naive", timeout=30,
    )
    assert result.gate_num == 0
    assert result.gate_num2 == 5
    assert result.equivalent in ("not_equivalent", "unknown"), result.equivalent
    assert result.tool_time is None


def test_cp_pi_and_cz_exact_clifford_parity():
    left = QuantumCircuit(2)
    left.cp(math.pi, 0, 1)
    right = QuantumCircuit(2)
    right.cz(0, 1)
    np.testing.assert_allclose(Operator(left).data, Operator(right).data,
                               atol=2e-14, rtol=0)
    result = check_equivalence(
        left, right, backend="rust", method="hybrid",
        strategy="Naive", timeout=60, tool_name="gpmc",
    )
    assert result.equivalent == "equivalent", result.equivalent


@pytest.mark.parametrize("operation", [
    "cp(pi) q[0];",
    "cp(pi) q[0],q[0];",
    "cp(pi,0.1) q[0],q[1];",
    "cp(pi) q[0],q[2];",
])
def test_malformed_cp_fail_closed(operation):
    source = f'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\n{operation}'
    with pytest.raises(ValueError):
        check_equivalence(
            source, source, backend="rust", method="reduction_rules",
            timeout=30,
        )

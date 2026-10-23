"""Qiskit-to-native U2/U3 exact-angle semantics, RED/Green control.

U2(phi, lam) = U3(pi/2, phi, lam), independent of optimization level.
The critical native structural regression is in gates.rs. These public
tests ensure QASM and actual compiled Rust FFI use the same semantics.
"""
import math
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from QuPRS import check_equivalence

QASM_HEAD = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'


def verify(a, b, method="reduction_rules"):
    return check_equivalence(
        a, b, backend="rust", method=method,
        strategy="Naive", tool_name="gpmc", timeout=35
    )


@pytest.mark.parametrize("phi,lam", [
    ("0", "0"),
    ("pi/4", "3*pi/4"),
    ("pi/2", "pi/4"),
])
def test_public_u2_matches_u3_pi_half(phi, lam):
    left = QASM_HEAD + f'u2({phi},{lam}) q[0];'
    right = QASM_HEAD + f'u3(pi/2,{phi},{lam}) q[0];'
    result = verify(left, right)
    assert result.equivalent == "equivalent", (phi, lam, result.equivalent)


@pytest.mark.parametrize("phi,lam", [
    (0.0, 0.0),
    (math.pi/4, 3*math.pi/4),
])
def test_qiskit_u2_definition_is_pi_half_rotation(phi, lam):
    reference=QuantumCircuit(1)
    reference.u(math.pi/2,phi,lam,0)
    # Independently evaluate Qiskit's documented U(theta,phi,lam)
    # matrix definition at theta=pi/2, not two copies of the same API.
    expected=np.array([
        [1, -np.exp(1j*lam)],
        [np.exp(1j*phi), np.exp(1j*(phi+lam))],
    ],dtype=complex)/math.sqrt(2)
    np.testing.assert_allclose(
        Operator(reference).data, expected,
        atol=2e-14, rtol=0
    )


def test_u2_differs_from_u3_pi_quarter():
    # This independent mathematical reference prevents a factor-two
    # theta bug from being mislabeled an alternative U2 convention.
    u2 = QuantumCircuit(1)
    u2.u(math.pi/2,0,0,0)
    wrong = QuantumCircuit(1)
    wrong.u(math.pi/4,0,0,0)
    matrix_distance = np.linalg.norm(
        Operator(u2).data - Operator(wrong).data, ord="fro"
    )
    assert matrix_distance > 0.1
    wrong_source = QASM_HEAD + 'u3(pi/4,0,0) q[0];'
    u2_source = QASM_HEAD + 'u2(0,0) q[0];'
    verdict = verify(u2_source, wrong_source)
    assert verdict.equivalent in ("not_equivalent","unknown"), verdict.equivalent

"""Native P/U1 angle normalization semantic regression, independent from CP.

Rust Angle is theta/pi, whereas the phase polynomial uses theta/(2*pi).
These tests verify the public compiled Rust backend, not a mocked parser.
"""
import math
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence


def verify(a,b,method="reduction_rules"):
    return check_equivalence(
        a,b,backend="rust",method=method,
        strategy="Naive",tool_name="gpmc",timeout=40,
    )


@pytest.mark.parametrize("kind,angle,reference",[
    ("p",math.pi/2,"s"),
    ("p",math.pi,"z"),
    ("p",-math.pi/2,"sdg"),
])
def test_qiskit_p_matches_exact_clifford_reference(kind,angle,reference):
    left = QuantumCircuit(1)
    left.p(angle,0)
    right = QuantumCircuit(1)
    getattr(right,reference)(0)
    np.testing.assert_allclose(Operator(left).data,Operator(right).data,
                               atol=2e-14,rtol=0)
    result=verify(left,right)
    assert result.equivalent=="equivalent", result.equivalent
    assert result.tool_time is None


def test_openqasm_u1_pi_over_two_exact_s_reference():
    left='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\nu1(pi/2) q[0];'
    right='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\ns q[0];'
    result=verify(left,right)
    assert result.equivalent=="equivalent", result.equivalent
    assert result.tool_time is None


@pytest.mark.parametrize("qasm,expected",[
    ("p(pi)", "not_equivalent"),
    ("u1(pi)", "not_equivalent"),
    ("p(pi/2)", "not_equivalent"),
])
def test_nonzero_diagonal_phase_is_not_exact_identity(qasm,expected):
    identity='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    circuit=identity+f'{qasm} q[0];'
    result=verify(identity,circuit)
    assert result.equivalent==expected, (qasm,result.equivalent)


def test_p_zero_and_u1_zero_are_identity():
    identity='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    for gate in ("p(0)", "u1(0)"):
        result=verify(identity,identity+gate+' q[0];')
        assert result.equivalent=="equivalent", (gate,result.equivalent)

"""Numeric Qiskit global-phase provenance through the native IR.

Explicit finite scalars are carried independently of QASM; unbound scalars
still fail closed. Preserve gate counts and original circuit objects.
"""
import math
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

from QuPRS import check_equivalence


def verify(a,b):
    return check_equivalence(
        a,b,backend="rust",method="reduction_rules",
        strategy="Naive",tool_name="gpmc",timeout=30
    )


@pytest.mark.parametrize("first,second",[
    (0.0,0.05),
    (0.05,0.0),
    (0.05,0.1),
    (-math.pi/2,math.pi/2),
])
def test_unequal_explicit_scalar_phase_is_preserved(first,second):
    a,b=QuantumCircuit(1),QuantumCircuit(1)
    a.global_phase=first
    b.global_phase=second
    result=verify(a,b)
    assert result.equivalent=="equivalent*"
    assert result.tool_time is None
    assert (result.gate_num, result.gate_num2)==(0,0)
    assert float(a.global_phase)!=float(b.global_phase)


def test_scalar_cancellation_with_numeric_pi_is_preserved():
    left=QuantumCircuit(1)
    for gate in ("x","z","x","z"):
        getattr(left,gate)(0)
    right=QuantumCircuit(1)
    right.global_phase=math.pi
    result=verify(left,right)
    assert result.equivalent=="equivalent"
    assert (result.gate_num,result.gate_num2)==(4,0)
    assert float(right.global_phase)==math.pi


@pytest.mark.parametrize("same_phase",[0.0,0.125,-math.pi/2])
def test_identical_source_phases_cancel_without_changing_verdict(same_phase):
    left=QuantumCircuit(1)
    right=QuantumCircuit(1)
    for qc in (left,right):
        qc.global_phase=same_phase
        qc.h(0)
        qc.h(0)
    result=verify(left,right)
    assert result.equivalent=="equivalent"
    assert result.tool_time is None


def test_mixed_qasm_and_circuit_with_explicit_phase_preserved():
    qasm='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    circuit=QuantumCircuit(1)
    circuit.global_phase=0.125
    assert verify(qasm,circuit).equivalent=="equivalent*"
    assert float(circuit.global_phase)==0.125


def test_unbound_symbolic_global_phase_rejected():
    a=QuantumCircuit(1)
    a.global_phase=Parameter("phi")
    with pytest.raises(ValueError,match="bound numeric"):
        verify(a,QuantumCircuit(1))


def test_equal_explicit_phases_do_not_mask_nonphase_difference():
    left,right=QuantumCircuit(1),QuantumCircuit(1)
    for circuit in (left,right):
        circuit.global_phase=0.125
    right.x(0)
    outcome=verify(left,right)
    assert outcome.equivalent=="not_equivalent"


def test_equal_source_phase_does_not_hide_native_gate_scalar():
    # XZXZ = -I; equal explicit input scalars cancel, but the gate-derived
    # nonzero global phase must still be reported as equivalent*.
    left, right = QuantumCircuit(1), QuantumCircuit(1)
    left.global_phase = 0.125
    right.global_phase = 0.125
    for gate in ("x", "z", "x", "z"):
        getattr(left, gate)(0)
    result = verify(left, right)
    assert result.equivalent == "equivalent*"
    assert result.tool_time is None


def test_equal_unbound_symbolic_source_phase_still_fails_closed():
    phi = Parameter("phi")
    left, right = QuantumCircuit(1), QuantumCircuit(1)
    left.global_phase = phi
    right.global_phase = phi
    with pytest.raises(ValueError, match="bound numeric"):
        verify(left, right)

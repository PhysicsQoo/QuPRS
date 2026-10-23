"""Conservative source global-phase provenance contract for Rust QASM2.

The bridge cannot encode a standalone QuantumCircuit.global_phase as QASM2.
Reject unequal explicit phases before launching the native engine, rather
than silently classifying exact equality from phase-stripped circuits.
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
def test_unequal_explicit_scalar_phase_must_fail_closed(first,second):
    a,b=QuantumCircuit(1),QuantumCircuit(1)
    a.global_phase=first
    b.global_phase=second
    with pytest.raises(ValueError,match="global_phase"):
        verify(a,b)


def test_scalar_cancellation_that_is_exact_but_untransportable_is_rejected():
    left=QuantumCircuit(1)
    for gate in ("x","z","x","z"):
        getattr(left,gate)(0)
    right=QuantumCircuit(1)
    right.global_phase=math.pi
    # XZXZ = -I, so exact source equality is possible here, but sending
    # right through QASM2 loses its standalone -I scalar. No false verdict.
    with pytest.raises(ValueError,match="global_phase"):
        verify(left,right)


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


def test_mixed_qasm_and_circuit_with_explicit_phase_rejected():
    qasm='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    circuit=QuantumCircuit(1)
    circuit.global_phase=0.125
    with pytest.raises(ValueError,match="global_phase"):
        verify(qasm,circuit)


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

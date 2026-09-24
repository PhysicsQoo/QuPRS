import pytest
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Qubit

from QuPRS import check_equivalence


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_issue21_reproducer(backend):
    """
    Test that different register partitions do not cause KeyError or crashes.
    From Issue #21: left uses (q[1], ancilla[1]), right uses (q[2]).
    """
    q = QuantumRegister(1, "q")
    ancilla = QuantumRegister(1, "ancilla")
    left = QuantumCircuit(q, ancilla)

    right = QuantumCircuit(2)
    right.cx(1, 0)
    right.sx(0)

    res = check_equivalence(left, right, method="hybrid", timeout=5, backend=backend)
    assert res.equivalent == "not_equivalent"


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_different_register_partitions_equivalent(backend):
    """
    Two circuits performing the exact same logic with different register partitionings
    must be evaluated as equivalent.
    """
    q = QuantumRegister(1, "q")
    ancilla = QuantumRegister(1, "ancilla")
    left = QuantumCircuit(q, ancilla)
    left.cx(1, 0)

    right = QuantumCircuit(2)
    right.cx(1, 0)

    res = check_equivalence(left, right, method="hybrid", timeout=5, backend=backend)
    assert res.equivalent == "equivalent"


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_different_qubit_counts(backend):
    """
    Circuits with different numbers of qubits should be reported as not equivalent.
    """
    c1 = QuantumCircuit(2)
    c2 = QuantumCircuit(3)

    res = check_equivalence(c1, c2, backend=backend)
    assert res.equivalent == "not_equivalent"


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_anonymous_qubits(backend):
    """
    Circuits with anonymous qubits (no registers, e.g. Qiskit 1.0+)
    should work without error.
    """
    left = QuantumCircuit([Qubit(), Qubit()])
    left.h(0)
    left.cx(0, 1)

    right = QuantumCircuit(2)
    right.h(0)
    right.cx(0, 1)

    res = check_equivalence(left, right, backend=backend)
    assert res.equivalent == "equivalent"

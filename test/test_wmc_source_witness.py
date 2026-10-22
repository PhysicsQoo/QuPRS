"""Independent source-level certificates without WMC tolerance heuristics."""
from fractions import Fraction
import pytest
from qiskit import QuantumCircuit

from QuPRS.utils.wmc_certificates import (
    certify_source_witness,
    certify_rz_basis_witness,
    certify_clifford_tableau_difference,
    make_source_witness_certificate,
    verify_source_witness_certificate,
)


@pytest.mark.parametrize("delta", (1e-6, 1e-4, 1e-3, 0.01, 0.2, -1e-6))
def test_rz_nonzero_has_computational_basis_witness(delta):
    identity, rotated = QuantumCircuit(1), QuantumCircuit(1)
    rotated.rz(delta, 0)
    assert certify_rz_basis_witness(identity, rotated) == "not_equivalent"


def test_rz_zero_is_exact_identity_and_canceling_pairs():
    a, b = QuantumCircuit(1), QuantumCircuit(1)
    b.rz(0.0, 0)
    assert certify_source_witness(a, b) == "equivalent"
    a.rz(0.125, 0)
    a.rz(-0.125, 0)
    assert certify_rz_basis_witness(a, b) == "equivalent"


def test_rz_witness_rejects_large_angle_and_non_rz_gates():
    lhs, rhs = QuantumCircuit(1), QuantumCircuit(1)
    rhs.rz(7, 0)
    assert certify_rz_basis_witness(lhs, rhs) is None
    rhs = QuantumCircuit(1)
    rhs.rx(0.1, 0)
    assert certify_rz_basis_witness(lhs, rhs) is None


def test_clifford_tableau_witness_issue21_reproducer():
    a, b = QuantumCircuit(2), QuantumCircuit(2)
    b.cx(1, 0)
    b.sx(0)
    assert certify_clifford_tableau_difference(a, b) == "not_equivalent"


def test_equal_clifford_tableaux_do_not_certify_strict_phase_equality():
    a, b = QuantumCircuit(1), QuantumCircuit(1)
    for gate in ("s", "x", "s", "x"):
        getattr(b, gate)(0)
    assert certify_clifford_tableau_difference(a, b) is None


def test_mixed_or_unsupported_inputs_cannot_generate_source_proof():
    a, b = QuantumCircuit(1), QuantumCircuit(1)
    b.t(0)
    assert certify_clifford_tableau_difference(a, b) is None
    assert certify_source_witness("OPENQASM 2.0;", b) is None
    assert certify_source_witness(a, "OPENQASM 2.0;") is None


def test_multiqubit_basis_witness_is_local_and_exact():
    a, b = QuantumCircuit(3), QuantumCircuit(3)
    a.rz(0.125, 0)
    b.rz(0.125, 0)
    b.rz(-0.2, 2)
    assert certify_rz_basis_witness(a, b) == "not_equivalent"

def test_independent_rz_certificate_can_be_rechecked_and_detects_tampering():
    a, b = QuantumCircuit(1), QuantumCircuit(1)
    b.rz(0.001, 0)
    certificate = make_source_witness_certificate(a, b)
    assert certificate["kind"] == "rz-basis-inequality"
    assert verify_source_witness_certificate(a, b, certificate)
    changed = dict(certificate, numerator="0")
    assert not verify_source_witness_certificate(a, b, changed)


def test_independent_clifford_certificate_can_be_rechecked_and_detects_tampering():
    a, b = QuantumCircuit(2), QuantumCircuit(2)
    b.cx(1, 0)
    b.sx(0)
    certificate = make_source_witness_certificate(a, b)
    assert certificate["kind"] == "clifford-tableau-inequality"
    assert verify_source_witness_certificate(a, b, certificate)
    corrupted = dict(certificate, left=certificate["right"])
    assert not verify_source_witness_certificate(a, b, corrupted)


def test_equal_tableau_does_not_forge_strict_certificate():
    a, b = QuantumCircuit(1), QuantumCircuit(1)
    b.z(0)
    b.z(0)
    assert make_source_witness_certificate(a, b) is None

def test_rz_strict_equality_does_not_ignore_qiskit_global_phase():
    a, b = QuantumCircuit(1), QuantumCircuit(1)
    b.global_phase = 0.125
    assert certify_rz_basis_witness(a, b) is None
    assert make_source_witness_certificate(a, b) is None
    b.rz(0.001, 0)
    # The RZ-only witness deliberately fails closed for explicit phases
    # instead of claiming source provenance that it has not modeled.
    assert certify_rz_basis_witness(a, b) is None

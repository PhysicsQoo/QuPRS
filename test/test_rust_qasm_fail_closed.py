"""Fail-closed native-QASM import controls using the real Rust entrypoint.

Unsupported gate sets must never be interpreted as empty/identity
operations. This is an input-safety contract, not a floating WMC oracle.
"""
import pytest
from qiskit import QuantumCircuit

from QuPRS import check_equivalence


def verify(a, b, **kwargs):
    return check_equivalence(
        a, b, backend="rust", method="reduction_rules",
        tool_name="gpmc", strategy="Naive", timeout=30, **kwargs
    )


@pytest.mark.parametrize("unsupported", [
    lambda: _gate("csx"),
    lambda: _gate("crz"),
    lambda: _gate("measure"),
])
def test_quantumcircuit_unsupported_gate_must_fail_closed(unsupported):
    with pytest.raises(ValueError, match="Unsupported QASM gate"):
        verify(QuantumCircuit(2), unsupported())


def _gate(name):
    c = QuantumCircuit(2, 1)
    if name == "csx":
        c.csx(0, 1)
    elif name == "crz":
        c.crz(0.125, 0, 1)
    elif name == "measure":
        c.measure(0, 0)
    else:
        raise ValueError(name)
    return c


@pytest.mark.parametrize("qasm,expected", [
    ('OPENQASM 3.0;\nqubit[1] q;\nx q[0];', "Unsupported QASM header"),
    ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncsx q[0],q[1];', "Unsupported QASM gate"),
    ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\nrz(0.1,0.2) q[0];', "Invalid QASM arity"),
    ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\nx q[5];', "out of bounds"),
])
def test_direct_unsupported_qasm_rejected_before_solver(qasm, expected):
    with pytest.raises(ValueError, match=expected):
        verify(qasm, qasm)


@pytest.mark.parametrize("name,apply", [
    ("p", lambda q: q.p(0.125, 0)),
    ("swap", lambda q: q.swap(0, 1)),
    ("sx", lambda q: q.sx(0)),
    ("sxdg", lambda q: q.sxdg(0)),
])
def test_supported_qiskit_gates_are_not_silently_erased(name, apply):
    blank = QuantumCircuit(2)
    altered = QuantumCircuit(2)
    apply(altered)
    result = verify(blank, altered)
    assert result.gate_num2 == (3 if name in ("sx", "sxdg") else 1), (name, result)
    # Reduction may return unknown, but must not mistake a nonidentity gate
    # for exact equivalence by silently skipping its source instruction.
    assert result.equivalent in ("unknown", "not_equivalent")


@pytest.mark.parametrize("gate", ["p(0.125)", "u1(0.125)", "u2(0.1,0.2)", "u3(0.1,0.2,0.3)", "u(0.1,0.2,0.3)"])
def test_ir_phase_gates_are_explicitly_parsed_from_qasm2(gate):
    source = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n' + gate + ' q[0];'
    no_op = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    result = verify(no_op, source)
    assert result.gate_num2 == 1
    assert result.equivalent in ("unknown", "not_equivalent")


@pytest.mark.parametrize("gate,phase", [("sx", "s"), ("sxdg", "sdg")])
def test_sx_is_identical_to_exact_h_phase_h_sequence(gate, phase):
    from qiskit.quantum_info import Operator
    import numpy as np

    left = QuantumCircuit(1)
    getattr(left, gate)(0)
    right = QuantumCircuit(1)
    right.h(0)
    getattr(right, phase)(0)
    right.h(0)
    assert np.allclose(Operator(left).data, Operator(right).data, atol=1e-14, rtol=0)
    result = verify(left, right)
    assert result.equivalent == "equivalent"
    assert result.tool_time is None


def test_existing_clifford_bell_control_is_preserved():
    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)
    result = verify(bell, bell.copy())
    assert result.equivalent == "equivalent"
    assert result.gate_num == result.gate_num2 == 2
    assert result.tool_time is None

@pytest.mark.parametrize("method", ["reduction_rules", "hybrid", "wmc_only"])
@pytest.mark.parametrize("angle", ["1e-12", "-1e-12", "1e-100"])
def test_nonzero_tiny_qasm_rotation_fails_closed_through_public_rust_api(
    method, angle
):
    """Reject a lost source rotation; never return an equivalence verdict."""
    identity = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    rotated = identity + f"rz({angle}) q[0];\n"
    with pytest.raises(ValueError, match="Nonzero source angle"):
        check_equivalence(
            identity, rotated, backend="rust", method=method, strategy="Naive",
            tool_name="gpmc", timeout=30,
        )

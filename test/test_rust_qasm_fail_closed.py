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
def test_nonzero_tiny_qasm_rotation_preserves_source_through_public_rust_api(
    method, angle
):
    """Accepted exact source literals must not be rounded into an identity.

    A floating WMC near-identity verdict is only numerical evidence.
    Reduction Rules can reject the exact source without invoking the solver.
    """
    identity = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    rotated = identity + f"rz({angle}) q[0];\n"
    result = check_equivalence(
        identity, rotated, backend="rust", method=method, strategy="Naive",
        tool_name="gpmc", timeout=30,
    )
    assert result.gate_num2 == 1
    if method == "wmc_only":
        # The original nonzero source phase is preserved, while the solver
        # may numerically report equivalence below its observable resolution.
        assert result.equivalent in {"equivalent", "equivalent*"}
        assert result.wmc_numerical_verdict == result.equivalent
        assert result.tool_time is not None
    else:
        # RR-only and Hybrid must honor the public per-call RR tolerance.
        # These source phases are far below the default 1e-10 cycles, and
        # are not arbitrarily rejected just because they are nonzero.
        assert result.equivalent in {"equivalent", "equivalent*"}
        assert result.rr_approximate is True
        assert result.tool_time is None


@pytest.mark.parametrize("angle,strict_tol", [
    ("1e-12", 1e-14),
    ("-1e-12", 1e-14),
    ("1e-100", 1e-110),
])
def test_tiny_qasm_source_is_not_lost_when_rr_tolerance_is_tight(angle, strict_tol):
    identity = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    rotated = identity + f"rz({angle}) q[0];\n"
    out = check_equivalence(
        identity, rotated, backend="rust", method="reduction_rules",
        strategy="Naive", rr_tolerance=strict_tol,
    )
    assert out.equivalent == "not_equivalent"
    assert out.rr_approximate is False
    assert out.wmc_solver_invoked is False

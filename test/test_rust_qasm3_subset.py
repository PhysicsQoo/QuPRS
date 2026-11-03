"""Restricted native OpenQASM 3 source and public FFI regressions.

These tests deliberately avoid QASM2 round-tripping QASM3 sources.  A genuine
unsupported QASM3 feature must fail closed before verification, not be stripped.
"""
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence

Q3_BELL = (
    'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[2] q;\n'
    'h q[0];\ncx q[0], q[1];\n'
)
Q2_BELL = (
    'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\n'
    'h q[0];\ncx q[0],q[1];\n'
)


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("method", ["reduction_rules", "hybrid"])
def test_qasm3_bell_matches_qasm2_without_serialization_bridge(backend, method):
    result = check_equivalence(
        Q3_BELL, Q2_BELL, backend=backend, method=method,
        tool_name="gpmc", strategy="Naive", timeout=30,
    )
    assert result.equivalent == "equivalent", (backend, method, result)
    assert result.tool_time is None


def test_native_qasm3_file_input_and_register_declaration_order(tmp_path):
    first = (
        'OPENQASM 3.0;\ninclude "stdgates.inc";\n'
        'qubit[1] alpha;\nqubit[1] beta;\n'
        'h alpha[0];\ncx alpha[0], beta[0];\n'
    )
    path = tmp_path / "bell.qasm3"
    path.write_text(first, encoding="utf-8")
    result = check_equivalence(
        str(path), Q2_BELL, backend="rust", method="reduction_rules",
        tool_name="gpmc", strategy="Naive",
    )
    assert result.equivalent == "equivalent"


def test_native_qasm3_exact_decimal_not_forced_to_zero_by_parser():
    base = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit q;\n'
    identity = base
    tiny_rz = base + 'rz(1e-12) q;\n'
    strict = check_equivalence(
        identity, tiny_rz, backend="rust", method="reduction_rules",
        rr_tolerance=1e-14, strategy="Naive", timeout=30,
    )
    assert strict.equivalent == "not_equivalent"
    assert strict.rr_approximate is False


def test_native_qasm3_phase_gate_preserves_nonzero_relative_scalar():
    base = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[1] q;\n'
    rz = base + 'rz(pi/2) q[0];\n'
    phase = base + 'p(pi/2) q[0];\n'
    r = check_equivalence(
        rz, phase, backend="rust", method="reduction_rules",
        rr_tolerance=0.0, strategy="Naive", timeout=30,
    )
    # RZ(theta) = exp(-i*theta/2) P(theta), nonzero exact scalar.
    assert r.equivalent == "equivalent*", r
    qc_rz = QuantumCircuit(1)
    qc_rz.rz(3.141592653589793 / 2, 0)
    qc_p = QuantumCircuit(1)
    qc_p.p(3.141592653589793 / 2, 0)
    import numpy as np
    assert not np.allclose(Operator(qc_rz).data, Operator(qc_p).data, atol=1e-12, rtol=0)


@pytest.mark.parametrize("method", ["reduction_rules", "hybrid"])
def test_native_qasm3_exact_global_phase_classification(method):
    base = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[1] q;\n'
    identity = base + 'x q[0];\nx q[0];\n'
    rotated = base + 'gphase(pi/2);\nx q[0];\nx q[0];\n'
    equal_source = base + 'gphase(pi/2);\ngphase(-pi/2);\n'
    def verify(left, right):
        return check_equivalence(
            left, right, backend="rust", method=method,
            strategy="Naive", rr_tolerance=0.0,
            tool_name="gpmc", timeout=30,
        )
    relative = verify(identity, rotated)
    assert relative.equivalent == "equivalent*", relative
    inverse = verify(rotated, identity)
    assert inverse.equivalent == "equivalent*", inverse
    cancellation = verify(base, equal_source)
    assert cancellation.equivalent == "equivalent", cancellation
    modulo = verify(base, base + 'gphase(2*pi);\n')
    assert modulo.equivalent == "equivalent", modulo


def test_native_qasm3_exact_decimal_global_phase_survives_parser():
    base = 'OPENQASM 3.0;\nqubit q;\n'
    phase = base + 'gphase(1e-12);\n'
    result = check_equivalence(
        base, phase, backend="rust", method="reduction_rules",
        strategy="Naive", rr_tolerance=0.0, timeout=30,
    )
    assert result.equivalent == "equivalent*", result


@pytest.mark.parametrize("unsupported", [
    'gphase(theta);',
    'gphase(pi/4) q[0];',
    'bit[1] c;',
    'c[0] = measure q[0];',
    'measure q[0];',
    'reset q[0];',
    'if (true) x q[0];',
    'ctrl @ x q[0], q[1];',
    'gate custom a { x a; }',
    'rz(theta) q[0];',
])
def test_native_qasm3_unsupported_not_silent(unsupported):
    base = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[2] q;\n'
    source = base + unsupported + '\n'
    with pytest.raises(ValueError):
        check_equivalence(source, source, backend="rust", method="reduction_rules")


def test_native_qasm3_negative_solver_control():
    base = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[1] q;\n'
    neq = check_equivalence(
        base, base + 'x q[0];\n', backend="rust", method="wmc_only",
        tool_name="gpmc", strategy="Naive", timeout=30,
    )
    assert neq.equivalent == "not_equivalent", neq

"""Public Python PathSum source global-phase transport contracts.

Qiskit QASM3 parser outputs numeric scalar global_phase. Its floating source
representation must be retained through the Python RR and WMC miter; it is not
a formal proof of the literal source-radian identity.
"""
import math

import pytest
from qiskit import QuantumCircuit, qasm3

from QuPRS import check_equivalence
from QuPRS.interface.load_qiskit import build_circuit


BASE = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[1] q;\n'


@pytest.mark.parametrize("method", ["reduction_rules", "hybrid"])
def test_qasm3_numeric_global_phase_survives_python_miter(method):
    first = BASE + "gphase(pi/2);\n"
    second = BASE
    assert math.isclose(float(qasm3.loads(first).global_phase), math.pi / 2)
    for left, right in [(first, second), (second, first)]:
        outcome = check_equivalence(
            left, right, backend="python", method=method, strategy="Naive",
            phase_tolerance=1e-15, rr_tolerance=0, timeout=30,
        )
        assert outcome.equivalent == "equivalent*", (left, right, outcome)
        assert not outcome.wmc_solver_invoked


@pytest.mark.parametrize("method", ["reduction_rules", "hybrid"])
def test_qasm3_numeric_global_phase_cancellation_and_full_period(method):
    for program in (
        BASE + "gphase(pi/2);\ngphase(-pi/2);\n",
        BASE + "gphase(2*pi);\n",
    ):
        actual = check_equivalence(
            BASE, program, backend="python", method=method,
            strategy="Naive", rr_tolerance=0, phase_tolerance=1e-15,
            timeout=30,
        )
        assert actual.equivalent == "equivalent", actual


def test_qasm3_small_numeric_phase_respects_phase_tolerance():
    source = BASE + "gphase(1e-12);\n"
    tolerant = check_equivalence(
        BASE, source, backend="python", method="reduction_rules",
        strategy="Naive", rr_tolerance=0, timeout=30,
    )
    assert tolerant.equivalent == "equivalent", tolerant
    strict = check_equivalence(
        BASE, source, backend="python", method="reduction_rules",
        strategy="Naive", rr_tolerance=0, phase_tolerance=1e-15, timeout=30,
    )
    assert strict.equivalent == "equivalent*", strict


def test_build_circuit_retains_loaded_qiskit_global_phase():
    qc = qasm3.loads(BASE + "gphase(pi/2);\n")
    ps = build_circuit(qc)
    assert abs(float(ps.P.evalf()) - 0.25) < 1e-14


def test_python_unbound_global_phase_fails_closed():
    from qiskit.circuit import Parameter

    original = QuantumCircuit(1)
    original.global_phase = Parameter("unbound")
    identity = QuantumCircuit(1)
    with pytest.raises(ValueError, match="bound numeric.*global_phase"):
        check_equivalence(
            original, identity, backend="python", method="reduction_rules",
            timeout=30,
        )


def test_python_wmc_only_uses_source_scalar_instead_of_analytic_identity():
    source = BASE + "gphase(pi/2);\n"
    result = check_equivalence(
        BASE, source, backend="python", method="wmc_only",
        strategy="Naive", tool_name="gpmc", timeout=30,
        phase_tolerance=1e-15, rr_tolerance=0,
    )
    assert result.equivalent == "equivalent*", result

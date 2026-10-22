"""WMC numerical-boundary parity: independent physics and count-policy oracles.

Two explicitly separate kinds of evidence:
* Actual Ganak/GPMC processes with Qiskit dense-operator physics oracles;
* Controlled external GPMC stdout to isolate the Python/Rust FLOATING COUNT
  classification boundary. A substituted WMC count is NOT a physics oracle.

The WMC classifier is now fail-closed without a verifiable certificate.
The float magnitude/phase acceptance bands remain historical diagnostics,
not strict-equivalence decisions.
"""
from contextlib import contextmanager
import os

import numpy as np
import pytest
from mpmath import mp
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence, config
from QuPRS.utils.wmc_certificates import verify_source_witness_certificate
from QuPRS.utils.util import algebraic_to_logical


BACKENDS = ("python", "rust")
SOLVERS = ("ganak", "gpmc")


@pytest.mark.parametrize("coefficient,logical", [(0, False), (1, True), (-1, False)])
def test_plain_integer_coefficients_are_valid_logical_inputs(coefficient, logical):
    """Regression: SXSX constant phase previously crashed before invoking WMC."""
    assert bool(algebraic_to_logical(coefficient)) is logical


@pytest.mark.parametrize(
    "angle,expected",
    [(0.0025, "equivalent"), (0.0031, "not_equivalent")],
    ids=("inside-magnitude-budget", "outside-magnitude-budget"),
)
@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("solver", SOLVERS)
def test_real_solver_magnitude_policy_is_not_physical_equivalence(
    angle, expected, backend, solver
):
    """An inequivalent RZ circuit may pass an explicitly approximate WMC gate.

    The independent operator/mathematical oracle says the circuits are NOT
    equal even up to global phase for any nonzero tested angle. The distinct
    numerical policy accepts |Tr(U†V)|/2 when it lies within 1e-6 of unity.
    """
    identity, target = QuantumCircuit(1), QuantumCircuit(1)
    target.h(0)
    target.rz(angle, 0)
    target.h(0)

    operator_left, operator_right = Operator(identity), Operator(target)
    assert not operator_left.equiv(operator_right, atol=1e-10, rtol=0)

    with mp.workdps(70):
        theta = mp.mpf(str(angle))
        normalized_trace = mp.cos(theta / 2)
        # Independent high-precision derivation, not QuPRS's WMC classifier.
        trace_budget = mp.mpf(str(config.WMC_MAGNITUDE_TOLERANCE))
        predicted = (
            "equivalent" if abs(normalized_trace - 1) < trace_budget
            else "not_equivalent"
        )
        assert predicted == expected
        # Cross-check numerical identity with the actual Qiskit matrix trace.
        trace_from_matrix = abs(np.trace(operator_right.data.conj().T) / 2)
        assert abs(trace_from_matrix - float(normalized_trace)) < 1e-12

    result = check_equivalence(
        identity, target, backend=backend, tool_name=solver,
        method="wmc_only", timeout=60,
    )
    # A previously decisive numerical policy must not certify equality or
    # inequality of a true unitary without an end-to-end error enclosure.
    assert result.equivalent == "unknown", (
        f"solver={solver}, backend={backend}, angle={angle}, "
        f"|Tr|/2={float(normalized_trace):.12g}, "
        f"expected_policy={expected}, actual={result.equivalent}"
    )
    assert result.tool_name == solver
    assert result.tool_time is not None


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("solver", SOLVERS)
def test_real_solver_nontrivial_global_phase_has_matrix_oracle(backend, solver):
    """S X S X = iI; physical equivalence and exact equality differ."""
    identity, phase = QuantumCircuit(1), QuantumCircuit(1)
    for gate in ("s", "x", "s", "x"):
        getattr(phase, gate)(0)

    reference, actual = Operator(identity), Operator(phase)
    assert reference.equiv(actual, atol=1e-10, rtol=0)
    assert not np.allclose(reference.data, actual.data, atol=1e-10, rtol=0)
    assert np.allclose(actual.data, 1j * np.eye(2), atol=1e-10, rtol=0)

    result = check_equivalence(
        identity, phase, backend=backend, tool_name=solver,
        method="wmc_only", timeout=60,
    )
    assert result.equivalent == "equivalent*", (
        backend, solver, result.equivalent
    )
    assert result.tool_name == solver
    assert result.tool_time is not None


@pytest.mark.skipif(os.name != "posix", reason="Controlled POSIX shell solver fixture")
@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize(
    "kind,factor,expected",
    [
        ("phase", -1.8, "equivalent*"),
        ("phase", -0.4, "equivalent"),
        ("phase", 0.4, "equivalent"),
        ("phase", 1.8, "equivalent*"),
        ("magnitude", 0.4, "equivalent"),
        ("magnitude", 1.8, "not_equivalent"),
    ],
)
def test_controlled_solver_count_agrees_across_python_and_rust(
    tmp_path, monkeypatch, backend, kind, factor, expected
):
    """Exercise the real WMC subprocess/parser and API classification path.

    The fake *GPMC executable* emits an analytically specified complex count;
    it deliberately does not solve the generated CNF. Therefore this checks
    tolerance/classification parity only, NOT the circuit's physical relation.
    Rust uses its real FFI and parser, not a mocked Rust result dictionary.
    """
    with mp.workdps(70):
        tol = (config.WMC_PHASE_TOLERANCE if kind == "phase"
               else config.WMC_MAGNITUDE_TOLERANCE)
        offset = mp.mpf(str(factor)) * mp.mpf(str(tol))
        if kind == "phase":
            expected_count = mp.mpc(4) * mp.exp(1j * offset)
            assert ("equivalent" if abs(offset) < mp.mpf(str(tol))
                    else "equivalent*") == expected
        else:
            expected_count = mp.mpc(4 * (1 - offset))
            assert ("equivalent" if abs(offset) < mp.mpf(str(tol))
                    else "not_equivalent") == expected
        real, imag = float(expected_count.real), float(expected_count.imag)

    # GPMC's parser accepts complex counts from this existing result prefix.
    # Writing at 17 significant digits keeps the fake output stable and
    # avoids conflating solver printing precision with classifier precision.
    complex_number = (
        f"{real:.17g} {'+' if imag >= 0 else '-'} {abs(imag):.17g}i"
    )
    fake = tmp_path / "fixed-count-gpmc"
    fake.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' 'c s exact quadruple float {complex_number}'\n"
    )
    fake.chmod(0o700)

    @contextmanager
    def resource(name):
        assert name == "gpmc"
        yield fake

    import QuPRS.utils as resources
    import QuPRS.interface.ps2wmc as adapter

    monkeypatch.setattr(resources, "WMC", resource)
    monkeypatch.setattr(adapter, "WMC", resource)

    identity, hh = QuantumCircuit(1), QuantumCircuit(1)
    hh.h(0)
    hh.h(0)
    # These circuits are physically exactly equal. The injected *count*
    # creates a separate, deliberately synthetic numerical-policy decision.
    assert np.allclose(
        Operator(identity).data, Operator(hh).data, atol=1e-10, rtol=0
    )

    result = check_equivalence(
        identity, hh, backend=backend, tool_name="gpmc",
        method="wmc_only", timeout=15,
    )
    # The injected count cannot be a proof. A separate *exact* Q(zeta_8)
    # source-replay certificate DOES establish H^2 = I, independent of the
    # fake count (including its deliberately inconsistent imaginary part).
    assert result.equivalent == "equivalent", (
        f"backend={backend}, count={complex_number}, kind={kind}, "
        f"factor={factor}, expected_policy={expected}, "
        f"actual={result.equivalent}"
    )
    assert result.source_certificate is not None
    assert result.source_certificate["kind"] == "cyclotomic-operator-full"
    assert verify_source_witness_certificate(identity, hh, result.source_certificate)
    assert result.tool_name == "gpmc"
    assert result.tool_time is not None

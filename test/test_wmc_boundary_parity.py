"""WMC numerical-boundary parity: independent physics and count-policy oracles.

Two explicitly separate kinds of evidence:
* Actual Ganak/GPMC processes with Qiskit dense-operator physics oracles;
* Controlled external GPMC stdout to isolate the Python/Rust FLOATING COUNT
  classification boundary. A substituted WMC count is NOT a physics oracle.

The projective-distance classifier is the only public WMC numerical policy.
"""
from contextlib import contextmanager
import os

import numpy as np
import pytest
from mpmath import mp
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence, config
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
    ids=("inside-distance-budget", "outside-distance-budget"),
)
@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("solver", SOLVERS)
def test_real_solver_projective_policy_is_not_source_exact_equivalence(
    angle, expected, backend, solver
):
    """An inequivalent RZ circuit may pass an explicitly approximate WMC gate.

    The independent operator/mathematical oracle says the circuits are NOT
    equal even up to global phase for any nonzero tested angle. The
    numerical distance tolerance is an explicitly approximate criterion.
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
        distance = abs(mp.sin(theta / 2))
        predicted = (
            "equivalent" if distance < mp.mpf("0.0014142132")
            else "not_equivalent"
        )
        assert predicted == expected
        # Cross-check numerical identity with the actual Qiskit matrix trace.
        trace_from_matrix = abs(np.trace(operator_right.data.conj().T) / 2)
        assert abs(trace_from_matrix - float(normalized_trace)) < 1e-12

    result = check_equivalence(
        identity, target, backend=backend, tool_name=solver,
        method="wmc_only", timeout=60,
        approximate_distance_tolerance=0.0014142132, wmc_phase_tolerance=1e-6,
    )
    assert result.equivalent == expected, (
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
    # Explicit 2e-4 projective distance; high-resolution fake stdout
    # isolates the parser and classifier, not real Solver arithmetic.
    epsilon = mp.mpf("0.0002")
    with mp.workdps(90):
        if kind == "phase":
            phase = mp.mpf(str(factor)) * mp.mpf(str(config.WMC_PHASE_TOLERANCE))
            real = mp.nstr(4 * mp.cos(phase), 75)
            imag_val = 4 * mp.sin(phase)
            imag = mp.nstr(imag_val, 75)
            assert ("equivalent" if abs(phase) < mp.mpf(str(config.WMC_PHASE_TOLERANCE))
                    else "equivalent*") == expected
        else:
            threshold = epsilon**2 / (1 + mp.sqrt(1 - epsilon**2))
            deficit = mp.mpf(str(factor)) * threshold
            real = mp.nstr(4 * (1 - deficit), 75)
            imag_val = mp.mpf("0")
            imag = "0"
            assert ("equivalent" if deficit < threshold
                    else "not_equivalent") == expected
    complex_number = real + ("+" if imag_val >= 0 else "") + imag + "i"

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
        approximate_distance_tolerance=2e-4,
    )
    assert result.equivalent == expected, (
        f"backend={backend}, count={complex_number}, kind={kind}, "
        f"factor={factor}, expected_policy={expected}, "
        f"actual={result.equivalent}"
    )
    assert result.tool_name == "gpmc"
    assert result.tool_time is not None

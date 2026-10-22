"""Source-pinned acceptance for the fail-closed, *uncertified* WMC stage.

Real Ganak/GPMC output currently has no verified enclosure for the true
normalized trace. This test distinguishes independent, source-level exact certificates from
uncertified numeric WMC counts. Bare solver diagnostics stay Unknown.

A future certified implementation must revise these expectations only
together with independently checked proof evidence, not a smaller tolerance.
"""
from fractions import Fraction
import math

import pytest
from qiskit import QuantumCircuit

from QuPRS import check_equivalence
from QuPRS.utils.wmc_solvers import classify_weighted_count


@pytest.mark.parametrize(
    "value,expected_log2",
    [(4.0 + 0j, 2.0), (4.0 - 1e-8j, 2.0),
     (3.9999999995 + 0j, 2.0), (0j, 2.0),
     (2.0 + 0j, 2.0), (0.0 + 4.0j, 2.0),
     (1e300 + 0j, math.log2(1e300))],
)
def test_uncertified_numeric_counts_are_not_proofs(value, expected_log2):
    status, log_count = classify_weighted_count(
        value.real, value.imag, expected_log2,
        magnitude_tolerance=1e-6, phase_tolerance=1e-6,
    )
    assert status == "unknown"
    if value == 0:
        assert log_count == float("-inf")
    else:
        assert math.isfinite(log_count)


@pytest.mark.parametrize("solver", ("gpmc", "ganak"))
@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("delta", (0.0, 1e-6, 1e-4, 1e-3, 1e-2, 0.2))
def test_real_solver_never_promotes_uncertified_rz_to_exact_result(
    solver, backend, delta,
):
    reference, target = QuantumCircuit(1), QuantumCircuit(1)
    target.rz(delta, 0)

    # Independent exact *source-angle* oracle. A nonzero rational-radian
    # argument cannot be a nonzero integer multiple of 2*pi since pi is
    # irrational; hence RZ(delta) is not scalar except for delta=0.
    source_radians = Fraction(str(delta))
    mathematically_equivalent_up_to_phase = (source_radians == 0)
    assert mathematically_equivalent_up_to_phase == (delta == 0.0)

    result = check_equivalence(
        reference, target, method="wmc_only", backend=backend,
        tool_name=solver, timeout=60,
    )
    assert result.equivalent == (
        "equivalent" if delta == 0.0 else "not_equivalent"
    ), (backend, solver, delta, result.equivalent)
    assert result.tool_name == solver
    assert result.tool_time is not None


@pytest.mark.parametrize("solver", ("gpmc", "ganak"))
@pytest.mark.parametrize("backend", ("python", "rust"))
def test_real_solver_nonzero_global_phase_requires_proof(solver, backend):
    reference, phase = QuantumCircuit(1), QuantumCircuit(1)
    for gate in ("s", "x", "s", "x"):
        getattr(phase, gate)(0)

    result = check_equivalence(
        reference, phase, method="wmc_only", backend=backend,
        tool_name=solver, timeout=60,
    )
    # This finite exact discrete circuit carries an independent no-path
    # global-phase certificate. The rounded solver count is still untrusted.
    assert result.equivalent == "equivalent*"
    assert result.tool_name == solver
    assert result.tool_time is not None


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_non_wmc_reduction_evidence_is_not_disabled(backend):
    reference = QuantumCircuit(1)
    result = check_equivalence(
        reference, reference.copy(), method="reduction_rules",
        backend=backend, timeout=30,
    )
    assert result.equivalent == "equivalent"

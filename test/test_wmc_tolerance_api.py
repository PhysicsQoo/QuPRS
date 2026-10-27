"""Per-request WMC tolerance contract across both backends and both solvers.

Tolerance changes are numerical classification policy, not a replacement for
the independent source-QASM strict-equivalence reference.
"""
import math

import pytest
from qiskit import QuantumCircuit

from QuPRS import check_equivalence, config
from QuPRS.utils.wmc_solvers import classify_weighted_count


def pair(angle=None):
    left, right = QuantumCircuit(1), QuantumCircuit(1)
    if angle is not None:
        right.rz(angle, 0)
    return left, right


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
def test_user_selected_wmc_tolerance_changes_only_numeric_classification(backend, solver):
    a, b = pair(0.001)
    strict = check_equivalence(
        a, b, backend=backend, tool_name=solver, method="wmc_only",
        strategy="Naive", timeout=60,
        wmc_magnitude_tolerance=1e-10,
        wmc_phase_tolerance=1e-10,
    )
    loose = check_equivalence(
        a, b, backend=backend, tool_name=solver, method="wmc_only",
        strategy="Naive", timeout=60,
        wmc_magnitude_tolerance=1e-6,
        wmc_phase_tolerance=1e-6,
    )
    assert strict.equivalent == "not_equivalent"
    assert loose.equivalent in {"equivalent", "equivalent*"}
    assert strict.wmc_magnitude_tolerance == 1e-10
    assert strict.wmc_phase_tolerance == 1e-10
    assert loose.wmc_magnitude_tolerance == 1e-6
    assert loose.wmc_phase_tolerance == 1e-6
    assert strict.wmc_policy == loose.wmc_policy == "legacy"


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
def test_proposed_default_accepts_exact_identity_and_rejects_known_near_identity(backend, solver):
    a, b = pair()
    identical = check_equivalence(
        a, b, backend=backend, tool_name=solver,
        method="wmc_only", strategy="Naive", timeout=60
    )
    assert identical.equivalent == "equivalent"
    assert identical.wmc_magnitude_tolerance == config.WMC_MAGNITUDE_TOLERANCE
    assert identical.wmc_phase_tolerance == config.WMC_PHASE_TOLERANCE
    a, b = pair(0.001)
    negative = check_equivalence(
        a, b, backend=backend, tool_name=solver,
        method="wmc_only", strategy="Naive", timeout=60
    )
    assert negative.equivalent == "not_equivalent"


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
def test_conservative_mode_downgrades_uncertified_numeric_verdict(backend, solver):
    a, b = pair(0.001)
    result = check_equivalence(
        a, b, backend=backend, tool_name=solver, method="wmc_only",
        strategy="Naive", timeout=60, wmc_policy="conservative",
        wmc_magnitude_tolerance=1e-10, wmc_phase_tolerance=1e-10,
    )
    assert result.equivalent == "unknown"
    assert result.wmc_numerical_verdict == "not_equivalent"
    assert result.wmc_magnitude_tolerance == 1e-10


@pytest.mark.parametrize("bad", [0, -1e-8, 1, 2.0, float("nan"), float("inf"), False, True, "1e-10", object()])
@pytest.mark.parametrize("field", ["wmc_magnitude_tolerance", "wmc_phase_tolerance"])
def test_invalid_tolerances_fail_before_any_native_solver(bad, field):
    a, b = pair()
    for backend in ("python", "rust"):
        with pytest.raises(ValueError, match=field):
            check_equivalence(
                a, b, backend=backend, method="wmc_only",
                **{field: bad}
            )


def test_phase_tolerance_controls_only_global_phase_label():
    # Normalized trace with slight nonzero phase and |trace| within 1e-3.
    t = dict(magnitude_tolerance=1e-3)
    assert classify_weighted_count(1.0, 1e-4, 0.0,
                                   phase_tolerance=1e-5, **t)[0] == "equivalent*"
    assert classify_weighted_count(1.0, 1e-4, 0.0,
                                   phase_tolerance=1e-3, **t)[0] == "equivalent"


def test_existing_symbolic_tolerance_remains_independent():
    # Calling check_equivalence must not mutate the global reduction tolerance.
    before = config.get_tolerance()
    a, b = pair()
    for value in (1e-6, 1e-10):
        result = check_equivalence(
            a, b, method="reduction_rules", backend="python",
            wmc_magnitude_tolerance=value, wmc_phase_tolerance=value,
        )
        assert result.equivalent == "equivalent"
        assert result.wmc_magnitude_tolerance == value
    assert config.get_tolerance() == before

"""Single projective-distance numerical policy across both public backends."""
import math

import pytest
from qiskit import QuantumCircuit

from QuPRS import check_equivalence, config
from QuPRS.utils.verification_tolerances import current_rr_tolerance


def pair(angle=None):
    left, right = QuantumCircuit(1), QuantumCircuit(1)
    if angle is not None:
        right.rz(angle, 0)
    return left, right


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("solver", ("gpmc", "ganak"))
def test_user_selected_distance_tolerance_changes_classification(backend, solver):
    # D_proj(I, Rz(0.001)) = |sin(0.0005)| < 1e-3, > 1e-8.
    a, b = pair(0.001)
    strict = check_equivalence(
        a, b, backend=backend, tool_name=solver, method="wmc_only",
        strategy="Naive", timeout=60, approximate_distance_tolerance=1e-8,
    )
    loose = check_equivalence(
        a, b, backend=backend, tool_name=solver, method="wmc_only",
        strategy="Naive", timeout=60, approximate_distance_tolerance=1e-3,
    )
    assert strict.equivalent == "not_equivalent"
    assert loose.equivalent in {"equivalent", "equivalent*"}
    assert strict.approximate_distance_tolerance == 1e-8
    assert loose.approximate_distance_tolerance == 1e-3
    assert strict.wmc_numerical_verdict == strict.equivalent
    assert loose.wmc_numerical_verdict == loose.equivalent


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("solver", ("gpmc", "ganak"))
def test_default_distance_accepts_identity_and_rejects_known_rotation(backend, solver):
    a, b = pair()
    identical = check_equivalence(
        a, b, backend=backend, tool_name=solver,
        method="wmc_only", strategy="Naive", timeout=60,
    )
    assert identical.equivalent == "equivalent"
    assert identical.approximate_distance_tolerance == config.DEFAULT_DISTANCE_TOLERANCE
    assert identical.wmc_phase_tolerance == config.WMC_PHASE_TOLERANCE
    a, b = pair(0.001)
    negative = check_equivalence(
        a, b, backend=backend, tool_name=solver,
        method="wmc_only", strategy="Naive", timeout=60,
    )
    assert negative.equivalent == "not_equivalent"


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("solver", ("gpmc", "ganak"))
def test_numerical_solver_verdict_remains_observable(backend, solver):
    a, b = pair(0.001)
    result = check_equivalence(
        a, b, backend=backend, tool_name=solver,
        method="wmc_only", strategy="Naive", timeout=60,
    )
    assert result.equivalent == "not_equivalent"
    assert result.wmc_numerical_verdict == result.equivalent
    assert result.tool_time is not None
    assert result.approximate_distance_tolerance == 1e-8


@pytest.mark.parametrize("bad", [0, -1e-8, 1, 2., float("nan"), float("inf"), False, True, "1e-10", object()])
@pytest.mark.parametrize("field", ("approximate_distance_tolerance", "wmc_phase_tolerance"))
def test_invalid_tolerances_fail_before_solver(bad, field):
    a, b = pair()
    for backend in ("python", "rust"):
        with pytest.raises(ValueError, match=field):
            check_equivalence(
                a, b, backend=backend, method="wmc_only",
                **{field: bad},
            )


def test_none_is_also_distance_default_not_magnitude_mode():
    one = QuantumCircuit(1)
    for backend in ("python", "rust"):
        answer = check_equivalence(
            one, one, method="reduction_rules", backend=backend,
            approximate_distance_tolerance=None,
        )
        assert answer.equivalent == "equivalent"
        assert answer.approximate_distance_tolerance == 1e-8


def test_phase_tolerance_controls_global_phase_label():
    lhs, rhs = QuantumCircuit(1), QuantumCircuit(1)
    lhs.rz(1e-6, 0)
    rhs.p(1e-6, 0)
    for tol, label in ((1e-5, "equivalent"), (1e-8, "equivalent*")):
        for backend in ("python", "rust"):
            result = check_equivalence(
                lhs, rhs, backend=backend, method="reduction_rules",
                phase_tolerance=tol,
            )
            assert result.equivalent == label


def test_existing_symbolic_tolerance_remains_independent():
    before = current_rr_tolerance()
    a, b = pair()
    for value in (1e-6, 1e-10):
        result = check_equivalence(
            a, b, method="reduction_rules", backend="python",
            wmc_phase_tolerance=value,
        )
        assert result.equivalent == "equivalent"
        assert result.wmc_phase_tolerance == value
    assert current_rr_tolerance() == before

"""Strict-equivalence RED cases, deliberately excluded from default testpaths.

Execute explicitly with:
python -m pytest -q .diagnostics/wmc_near_identity_red/test_near_identity.py

A failing scientific assertion is a real RED result, not xfail/skip and not
a reason to redefine existing numerical-policy boundary tests as proofs.
"""
import math

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence, config
from QuPRS.utils.wmc_solvers import classify_weighted_count


STRICT_POSITIVE = frozenset(("equivalent", "equivalent*"))
# Historical false positive at 1e-6: preserved in the original source-pinned RED.
LEGACY_ANGLE = 0.001
# Smaller but still representable in current Python/Rust QASM and f64 paths.
# Ideal unit defect = 1 - cos(0.0001) ~= 4.999999996e-9 < 1e-8.
SMALL_ANGLE = 0.0002
SOLVERS = ("gpmc", "ganak")
BACKENDS = ("python", "rust")


def pair(case):
    left = QuantumCircuit(1)
    right = QuantumCircuit(1)
    if case == "global_phase":
        # S X S X = iI: equivalent up to phase, not exact equality.
        for gate in ("s", "x", "s", "x"):
            getattr(right, gate)(0)
    elif case != "identity":
        right.rz({"near": SMALL_ANGLE, "historical": LEGACY_ANGLE, "far": 0.01}[case], 0)
    return left, right


@pytest.mark.parametrize(
    "case,expected",
    [
        ("identity", "equivalent"),
        ("global_phase", "equivalent*"),
        ("near", "not_equivalent"),
        ("historical", "not_equivalent"),
        ("far", "not_equivalent"),
    ],
)
def test_independent_dense_operator_controls(case, expected):
    left, right = pair(case)
    a, b = Operator(left), Operator(right)
    exactly_equal = np.allclose(a.data, b.data, atol=1e-12, rtol=0)
    equal_up_to_phase = a.equiv(b, atol=1e-12, rtol=0)
    status = (
        "equivalent" if exactly_equal
        else "equivalent*" if equal_up_to_phase
        else "not_equivalent"
    )
    assert status == expected
    if case in {"near", "historical", "far"}:
        delta = {"near": SMALL_ANGLE, "historical": LEGACY_ANGLE, "far": 0.01}[case]
        # RZ eigenvalue ratio is exp(i*delta), not one for this delta.
        assert abs(math.sin(delta / 2)) > 1e-6


def test_count_policy_controls_and_true_negative():
    kwargs = dict(
        magnitude_tolerance=config.WMC_MAGNITUDE_TOLERANCE,
        phase_tolerance=config.WMC_PHASE_TOLERANCE,
    )
    assert classify_weighted_count(2.0, 0.0, 1.0, **kwargs)[0] == "equivalent"
    assert classify_weighted_count(0.0, 2.0, 1.0, **kwargs)[0] == "equivalent*"
    assert classify_weighted_count(
        2 * math.cos(0.01 / 2), 0.0, 1.0, **kwargs
    )[0] == "not_equivalent"


def test_near_identity_count_must_not_certify_equivalence_red():
    # Independent analytic |Tr(RZ(delta))|/2 = cos(delta/2), with delta!=0.
    # An experimental RED is still expected for the 1e-8 default candidate.
    assert config.WMC_MAGNITUDE_TOLERANCE == 1e-8
    # This is the ideal trace, not a mocked solver error or QASM export.
    normalized = math.cos(SMALL_ANGLE / 2)
    defect = 1 - normalized
    assert 0 < defect < config.WMC_MAGNITUDE_TOLERANCE
    status, _ = classify_weighted_count(
        2 * normalized,
        0.0,
        1.0,
        magnitude_tolerance=config.WMC_MAGNITUDE_TOLERANCE,
        phase_tolerance=config.WMC_PHASE_TOLERANCE,
    )
    assert status not in STRICT_POSITIVE, (
        f"Uncertified strict-equivalence claim for RZ({SMALL_ANGLE}): "
        f"normalized_trace={normalized:.16g}, defect={defect:.6g}, "
        f"verdict={status}"
    )


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("solver", SOLVERS)
def test_selected_native_wmc_near_identity_red(backend, solver):
    left, right = pair("near")
    assert not Operator(left).equiv(Operator(right), atol=1e-12, rtol=0)
    result = check_equivalence(
        left, right, backend=backend, tool_name=solver,
        method="wmc_only", strategy="Naive", timeout=45,
    )
    # tool_time and tool_name identify the reported WMC branch, but alone do
    # not certify execve/CNF provenance or the correctness of native counting.
    assert result.tool_name == solver, (
        f"Requested {solver} but result reports {result.tool_name}"
    )
    assert result.tool_time is not None, (
        f"No WMC timing reported: {backend}/{solver}/{result.equivalent}"
    )
    assert result.equivalent not in STRICT_POSITIVE, (
        f"False strict equivalence: {backend}/{solver}/wmc_only, "
        f"delta={SMALL_ANGLE}, status={result.equivalent}, "
        f"reported_solver_time={result.tool_time}"
    )

@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("solver", SOLVERS)
def test_default_threshold_rejects_historical_counterexample(backend, solver):
    """The original 0.001 rad defect exceeds the *current* 1e-8 budget."""
    assert config.WMC_MAGNITUDE_TOLERANCE == 1e-8
    left, right = pair("historical")
    assert not Operator(left).equiv(Operator(right), atol=1e-12, rtol=0)
    normalized = math.cos(LEGACY_ANGLE / 2)
    assert 1 - normalized > config.WMC_MAGNITUDE_TOLERANCE
    result = check_equivalence(
        left, right, backend=backend, tool_name=solver,
        method="wmc_only", strategy="Naive", timeout=45,
    )
    assert result.tool_name == solver and result.tool_time is not None
    assert result.wmc_magnitude_tolerance == 1e-8
    assert result.equivalent == "not_equivalent", (backend, solver, result.equivalent)


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("solver", SOLVERS)
def test_explicit_historical_tolerance_retains_numeric_acceptance(backend, solver):
    """Old 1e-6 acceptance remains reproducible, but it is NOT a proof."""
    left, right = pair("historical")
    assert not Operator(left).equiv(Operator(right), atol=1e-12, rtol=0)
    result = check_equivalence(
        left, right, backend=backend, tool_name=solver,
        method="wmc_only", strategy="Naive", timeout=45,
        wmc_magnitude_tolerance=1e-6, wmc_phase_tolerance=1e-6,
    )
    assert result.tool_name == solver and result.tool_time is not None
    assert result.wmc_magnitude_tolerance == 1e-6
    assert result.equivalent in STRICT_POSITIVE, (backend, solver, result.equivalent)


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("solver", SOLVERS)
def test_conservative_mode_does_not_claim_small_angle_proof(backend, solver):
    """Uncertified WMC numeric positives remain only an observation."""
    left, right = pair("near")
    assert not Operator(left).equiv(Operator(right), atol=1e-12, rtol=0)
    result = check_equivalence(
        left, right, backend=backend, tool_name=solver,
        method="wmc_only", strategy="Naive", timeout=45,
        wmc_policy="conservative",
    )
    assert result.equivalent == "unknown", (backend, solver, result.equivalent)
    assert result.wmc_numerical_verdict in STRICT_POSITIVE
    assert result.wmc_magnitude_tolerance == 1e-8


def test_two_numerical_thresholds_are_not_equivalence_proofs():
    """Independent analytic certificate covers both numerical classification bands."""
    for delta, tol in ((LEGACY_ANGLE, 1e-6), (SMALL_ANGLE, 1e-8)):
        normalized = math.cos(delta / 2)
        defect = 1 - normalized
        assert delta != 0 and abs(math.sin(delta / 2)) > 1e-6
        assert 0 < defect < tol
        status, _ = classify_weighted_count(
            2 * normalized, 0.0, 1.0,
            magnitude_tolerance=tol, phase_tolerance=tol,
        )
        assert status in STRICT_POSITIVE

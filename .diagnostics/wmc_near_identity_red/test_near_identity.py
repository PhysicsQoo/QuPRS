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
SMALL_ANGLE = 0.001
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
        right.rz({"near": SMALL_ANGLE, "far": 0.01}[case], 0)
    return left, right


@pytest.mark.parametrize(
    "case,expected",
    [
        ("identity", "equivalent"),
        ("global_phase", "equivalent*"),
        ("near", "not_equivalent"),
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
    if case in {"near", "far"}:
        delta = SMALL_ANGLE if case == "near" else 0.01
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

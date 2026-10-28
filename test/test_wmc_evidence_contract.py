"""Unified WMC evidence and backward-incompatible policy removal contract.

Numerical WMC classifications are observations, not exact source certificates.
A future numerical guard may use the diagnostics to return unknown at boundaries.
"""
import inspect

import pytest
from qiskit import QuantumCircuit

from QuPRS import check_equivalence


def pair(case):
    left, right = QuantumCircuit(1), QuantumCircuit(1)
    if case == "near":
        right.rz(0.001, 0)
    elif case == "far":
        right.rz(0.01, 0)
    elif case == "hh":
        right.h(0)
        right.h(0)
    elif case != "identity":
        raise ValueError(case)
    return left, right


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
@pytest.mark.parametrize("case", ["identity", "near", "far"])
def test_wmc_numerical_evidence_available_without_policy(backend, solver, case):
    a, b = pair(case)
    result = check_equivalence(
        a, b, backend=backend, tool_name=solver, method="wmc_only",
        strategy="Naive", timeout=60,
    )
    assert result.tool_name == solver
    assert result.tool_time is not None
    assert result.equivalent in {"equivalent", "equivalent*", "not_equivalent"}
    assert result.wmc_numerical_verdict == result.equivalent
    assert not hasattr(result, "wmc_policy")


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
def test_hybrid_reports_numeric_evidence_only_when_wmc_runs(backend, solver):
    a, b = pair("near")
    result = check_equivalence(
        a, b, backend=backend, tool_name=solver, method="hybrid",
        strategy="Naive", timeout=60,
    )
    if result.tool_time is None:
        assert result.wmc_numerical_verdict is None
        assert result.equivalent == "not_equivalent"
    else:
        assert result.wmc_numerical_verdict == result.equivalent


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("method", ["reduction_rules", "hybrid"])
def test_symbolic_fast_path_has_no_wmc_observation(backend, method):
    a, b = pair("hh")
    result = check_equivalence(
        a, b, backend=backend, method=method, tool_name="gpmc",
        strategy="Naive", timeout=60,
    )
    assert result.equivalent == "equivalent"
    assert result.tool_time is None
    assert result.wmc_numerical_verdict is None


def test_policy_keyword_removed_instead_of_silently_ignored():
    assert "wmc_policy" not in inspect.signature(check_equivalence).parameters
    a, b = pair("identity")
    with pytest.raises(TypeError, match="wmc_policy"):
        check_equivalence(a, b, wmc_policy="legacy")


def test_different_qubit_counts_remain_structural_negative():
    a, b = QuantumCircuit(1), QuantumCircuit(2)
    result = check_equivalence(a, b)
    assert result.equivalent == "not_equivalent"
    assert result.tool_time is None
    assert result.wmc_numerical_verdict is None

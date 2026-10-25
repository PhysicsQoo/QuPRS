"""Conservative WMC evidence semantics for both existing execution backends.

This suite complements, but does not reclassify or xfail, the separate
scientific strict-equivalence RED. All native cases use real solvers.
"""
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
def test_conservative_wmc_only_never_certifies_float_count(backend, solver, case):
    a, b = pair(case)
    old = check_equivalence(
        a, b, backend=backend, tool_name=solver, method="wmc_only",
        strategy="Naive", timeout=60,
    )
    reviewed = check_equivalence(
        a, b, backend=backend, tool_name=solver, method="wmc_only",
        strategy="Naive", timeout=60, wmc_policy="conservative",
    )
    assert old.wmc_policy == "legacy"
    assert old.wmc_numerical_verdict is None
    assert old.equivalent in {"equivalent", "equivalent*", "not_equivalent"}
    assert reviewed.equivalent == "unknown"
    assert reviewed.wmc_policy == "conservative"
    assert reviewed.wmc_numerical_verdict == old.equivalent
    assert reviewed.tool_name == solver
    assert reviewed.tool_time is not None


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
def test_hybrid_uncertified_numeric_fallback_is_only_downgraded(backend, solver):
    a, b = pair("near")
    result = check_equivalence(
        a, b, backend=backend, tool_name=solver, method="hybrid",
        strategy="Naive", timeout=60, wmc_policy="conservative",
    )
    if result.tool_time is None:
        # The Rust reducer already proves this small nonzero rotation differs;
        # conservative WMC policy must NOT force an unnecessary solver call.
        assert result.equivalent == "not_equivalent"
        assert result.wmc_numerical_verdict is None
    else:
        assert result.equivalent == "unknown"
        assert result.wmc_numerical_verdict in {
            "equivalent", "equivalent*", "not_equivalent"
        }


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("method", ["reduction_rules", "hybrid"])
def test_symbolic_route_stays_unchanged_without_solver(backend, method):
    a, b = pair("hh")
    result = check_equivalence(
        a, b, backend=backend, method=method, tool_name="gpmc",
        strategy="Naive", timeout=60, wmc_policy="conservative",
    )
    assert result.equivalent == "equivalent"
    assert result.wmc_numerical_verdict is None
    assert result.wmc_policy == "conservative"
    assert result.tool_time is None


@pytest.mark.parametrize("policy", ["strict", "", None, "CONSERVATIVE", 0])
def test_fail_closed_on_unsupported_policy(policy):
    a, b = pair("identity")
    with pytest.raises(ValueError, match="wmc_policy"):
        check_equivalence(a, b, wmc_policy=policy)


def test_different_qubit_counts_still_report_structural_inequivalence():
    a = QuantumCircuit(1)
    b = QuantumCircuit(2)
    result = check_equivalence(a, b, wmc_policy="conservative")
    assert result.equivalent == "not_equivalent"
    assert result.wmc_numerical_verdict is None
    assert result.wmc_policy == "conservative"

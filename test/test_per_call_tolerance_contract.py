"""Per-verification tolerance state: cache keys, threads and subprocesses."""
import math
from concurrent.futures import ThreadPoolExecutor

import pytest
import symengine as se
from qiskit import QuantumCircuit

from QuPRS import check_equivalence, config
from QuPRS.utils.util import process_term, reduce_expression
from QuPRS.utils.verification_tolerances import (
    DEFAULT_RR_TOLERANCE, current_rr_tolerance, scoped_rr_tolerance,
)


def test_no_mutable_global_rr_config_api():
    assert not hasattr(config, "TOLERANCE")
    assert not hasattr(config, "set_tolerance")
    assert not hasattr(config, "get_tolerance")


def test_tolerance_is_explicit_cache_key_and_context_restores():
    x = se.Symbol("per_call_rr_cache")
    term = se.Rational(1, 2_000_000) * x
    baseline = current_rr_tolerance()
    assert baseline == DEFAULT_RR_TOLERANCE
    with scoped_rr_tolerance(1e-6):
        assert process_term(term) == se.S.Zero
        assert reduce_expression(term) == se.S.Zero
        with scoped_rr_tolerance(1e-10):
            assert process_term(term) != se.S.Zero
            assert reduce_expression(term) != se.S.Zero
        assert reduce_expression(term) == se.S.Zero
    assert current_rr_tolerance() == baseline
    assert reduce_expression(term) != se.S.Zero


def test_parallel_independent_rr_contexts():
    x = se.Symbol("parallel_rr_context")
    term = se.Rational(1, 2_000_000) * x

    def worker(value):
        with scoped_rr_tolerance(value):
            observed = [reduce_expression(term) for _ in range(8)]
            return all(v == se.S.Zero for v in observed)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, [1e-6, 1e-10]))
    assert results == [True, False]
    assert current_rr_tolerance() == DEFAULT_RR_TOLERANCE


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_phase_alias_mismatch_rejected(backend):
    with pytest.raises(ValueError, match="phase_tolerance conflicts"):
        check_equivalence(
            QuantumCircuit(1), QuantumCircuit(1), backend=backend,
            phase_tolerance=1e-7, wmc_phase_tolerance=1e-8,
        )


@pytest.mark.parametrize("bad", [False, 0, -1, float("nan"), float("inf"), "1e-10"])
def test_invalid_rr_tolerance_fails_before_solver(bad):
    with pytest.raises(ValueError, match="rr_tolerance"):
        check_equivalence(QuantumCircuit(1), QuantumCircuit(1), rr_tolerance=bad)


def test_rust_custom_rr_tolerance_fails_closed_until_numeric_rules_supported():
    with pytest.raises(ValueError, match="custom rr_tolerance is not supported"):
        check_equivalence(
            QuantumCircuit(1), QuantumCircuit(1), backend="rust",
            method="reduction_rules", rr_tolerance=1e-6,
        )


def test_spawned_safe_mode_receives_rr_context():
    result = check_equivalence(
        QuantumCircuit(1), QuantumCircuit(1),
        method="reduction_rules", backend="python",
        safe_mode=True, rr_tolerance=1e-6, timeout=60,
    )
    assert result.equivalent == "equivalent"
    assert current_rr_tolerance() == DEFAULT_RR_TOLERANCE


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_rr_global_phase_label_respects_per_call_tolerance(backend):
    lhs, rhs = QuantumCircuit(1), QuantumCircuit(1)
    lhs.rz(1e-9, 0)
    rhs.p(1e-9, 0)
    for tolerance, expected in (
        (1e-8, "equivalent"),
        (1e-12, "equivalent*"),
    ):
        result = check_equivalence(
            lhs, rhs, backend=backend,
            method="reduction_rules", strategy="Naive",
            phase_tolerance=tolerance,
        )
        assert result.equivalent == expected
        assert result.tool_time is None
        if expected == "equivalent":
            assert result.decision_basis == "symbolic_phase_tolerance"

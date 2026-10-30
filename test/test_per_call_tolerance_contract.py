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


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_custom_rr_tolerance_accepted_with_per_call_scope(backend):
    identity = QuantumCircuit(1)
    for tolerance in (1e-6, 1e-12):
        result = check_equivalence(
            identity, identity, backend=backend,
            method="reduction_rules", rr_tolerance=tolerance,
        )
        assert result.equivalent == "equivalent"
        assert result.wmc_solver_invoked is False
    assert current_rr_tolerance() == DEFAULT_RR_TOLERANCE


def test_public_rust_rr_tolerance_changes_near_diagonal_verdict():
    # The Rust core uses a conservative *aggregate* phase bound without
    # modifying exact source angles. Exercise that path through the PyO3
    # public backend, not just the native crate's unit tests.
    identity = QuantumCircuit(1)
    near = QuantumCircuit(1)
    near.rz(1e-9, 0)
    loose = check_equivalence(
        identity, near, backend="rust",
        method="reduction_rules", strategy="Naive", rr_tolerance=1e-8,
    )
    strict = check_equivalence(
        identity, near, backend="rust",
        method="reduction_rules", strategy="Naive", rr_tolerance=1e-12,
    )
    assert loose.equivalent in ("equivalent", "equivalent*")
    assert loose.rr_approximate is True
    assert strict.equivalent == "not_equivalent"
    assert strict.rr_approximate is False
    assert loose.wmc_solver_invoked is False
    assert strict.wmc_solver_invoked is False


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
        assert result.wmc_time is None

@pytest.mark.parametrize("backend", ["python", "rust"])
def test_result_execution_metadata_replaces_redundant_basis(backend):
    # A reduction-only verdict is visible without inventing a basis label.
    result = check_equivalence(
        QuantumCircuit(1), QuantumCircuit(1),
        method="reduction_rules", backend=backend,
    )
    assert result.equivalent == "equivalent"
    assert result.wmc_time is None
    assert result.tool_time is None
    assert result.wmc_solver_invoked is False
    assert result.wmc_numerical_verdict is None
    assert not hasattr(result, "decision_basis")


def test_direct_ffi_result_omits_redundant_basis():
    from QuPRS import _pathsum_rust

    qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    result = _pathsum_rust.check_equivalence(
        qasm, qasm, method="reduction_rules",
    )
    assert "decision_basis" not in result
    assert result["wmc_solver_invoked"] is False
    assert "wmc_time_sec" not in result


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_rr_only_near_zero_obeys_same_per_call_tolerance_across_backends(backend):
    identity = QuantumCircuit(1)
    tiny = QuantumCircuit(1)
    tiny.rz(1e-9, 0)
    outcomes = []
    for rr_tolerance in (1e-8, 1e-12):
        result = check_equivalence(
            identity, tiny, backend=backend, method="reduction_rules",
            strategy="Naive", rr_tolerance=rr_tolerance,
        )
        outcomes.append(result.equivalent)
        assert result.wmc_solver_invoked is False
        assert result.tool_time is None
    assert outcomes == ["equivalent", "not_equivalent"]


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("method", ("reduction_rules", "hybrid"))
@pytest.mark.parametrize("distance_tolerance", (1e-6, 1e-12))
def test_rr_decision_is_independent_of_wmc_distance_tolerance(
    backend, method, distance_tolerance,
):
    # Source rotation is nonzero and its real projective distance is much
    # larger than 1e-12. A deliberately loose RR tolerance accepts it
    # in BOTH RR-only and the RR stage of Hybrid without any WMC solver.
    qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    result = check_equivalence(
        qasm, qasm + "rz(0.000000001) q[0];\n",
        backend=backend, method=method, strategy="Naive",
        tool_name="gpmc", rr_tolerance=1e-8,
        approximate_distance_tolerance=distance_tolerance,
    )
    assert result.equivalent == "equivalent", (
        backend, method, distance_tolerance, result.equivalent,
    )
    assert result.tool_time is None
    assert result.wmc_time is None
    assert result.wmc_solver_invoked is False


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("distance_tolerance", (1e-6, 1e-12))
def test_rr_only_strict_tolerance_does_not_inherit_wmc_distance(
    backend, distance_tolerance,
):
    qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    result = check_equivalence(
        qasm, qasm + "rz(0.000000001) q[0];\n",
        backend=backend, method="reduction_rules", strategy="Naive",
        rr_tolerance=1e-12,
        approximate_distance_tolerance=distance_tolerance,
    )
    assert result.equivalent == "not_equivalent"
    assert result.wmc_solver_invoked is False
    assert result.tool_time is None

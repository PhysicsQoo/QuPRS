"""Numerical-distance and solver-precision cross-backend regression tests.

The reference precision bounds are mathematical fixtures, not certificates of
external weighted solver arithmetic. The public API tests must pass normally.
"""
from contextlib import contextmanager
import math
import os

from mpmath import mp
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence, config, _pathsum_rust
from QuPRS.utils import WMC


PREFIX = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
SOLVERS = ("gpmc", "ganak")
EPS = 2e-4


def qasm(operations=""):
    return PREFIX + operations


@contextmanager
def solver_binary(solver):
    """Use exactly the selected real solver for the native FFI prototype."""
    key = "QUPRS_" + solver.upper() + "_PATH"
    old = os.environ.get(key)
    with WMC(solver) as path:
        os.environ[key] = str(path)
        try:
            yield
        finally:
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def normalize_status(result):
    return {
        "Equivalent": "equivalent",
        "Equivalent (Up to Global Phase)": "equivalent*",
        "Not Equivalent": "not_equivalent",
        "Unknown": "unknown",
        "Timeout": "Timeout",
    }.get(result["status"], result["status"])


def trace_defect_from_distance(distance):
    sq = distance * distance
    return sq / (1 + math.sqrt(1 - sq))


def interval_distance_classification(m_hat, error_bound, epsilon):
    """Independent reference with an explicitly supplied *valid* m error bound.

    This is a mathematical oracle, not a claim that empirical solver deviations
    provide a certified universal bound.
    """
    if not (0 <= error_bound < 1):
        raise ValueError("invalid error bound")
    m_lo = max(0.0, m_hat - error_bound)
    m_hi = min(1.0, m_hat + error_bound)
    boundary = math.sqrt(1 - epsilon * epsilon)
    if m_lo >= boundary:
        return "inside"
    if m_hi < boundary:
        return "outside"
    return "unknown"


@pytest.mark.parametrize("ratio", ["0.5", "0.99999999", "1", "1.00000001", "1.5"])
def test_distance_to_magnitude_boundary_high_precision(ratio):
    """Do not subtract a floating-point cosine rounded to one."""
    with mp.workdps(90):
        eps = mp.mpf("0.0002")
        distance = eps * mp.mpf(ratio)
        theta = 2 * mp.asin(distance)
        m = abs(mp.cos(theta / 2))
        defect = 1 - m
        derived = mp.sqrt(1 - m * m)
        assert abs(derived - distance) < mp.mpf("1e-75")
        assert abs(defect - distance * distance / (1 + mp.sqrt(1 - distance * distance))) < mp.mpf("1e-75")
        assert (derived <= eps) == (mp.mpf(ratio) <= 1)


def test_f64_cannot_reliably_resolve_1e_8_distance_using_unit_magnitude():
    # An epsilon_D of 1e-8 needs a magnitude defect around 5e-17.
    tau = trace_defect_from_distance(1e-8)
    assert 0 < tau < math.ulp(1.0)
    assert 1.0 - tau == 1.0
    assert trace_defect_from_distance(1e-4) > tau


def test_reference_uncertainty_guard_has_three_distinct_outcomes():
    eps = 5e-4
    boundary = math.sqrt(1 - eps * eps)
    assumed_bound = 3e-9  # illustration only; NOT a solver certification
    assert interval_distance_classification(boundary + 3e-8, assumed_bound, eps) == "inside"
    assert interval_distance_classification(boundary - 3e-8, assumed_bound, eps) == "outside"
    assert interval_distance_classification(boundary, assumed_bound, eps) == "unknown"


@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("theta,expected", [
    ("0.00032", "equivalent"),
    ("0.00048", "not_equivalent"),
])
def test_native_distance_mode_has_no_early_strict_negative(solver, theta, expected):
    """Native opt-in path: strict RR negative must not preempt distance mode."""
    left, right = qasm(), qasm("rz(" + theta + ") q[0];\n")
    with solver_binary(solver):
        rr = _pathsum_rust.check_equivalence(
            left, right, method="reduction_rules", strategy="Naive",
            tool_name=solver, timeout=45, approximate_distance_tolerance=EPS,
        )
        hybrid = _pathsum_rust.check_equivalence(
            left, right, method="hybrid", strategy="Naive",
            tool_name=solver, timeout=45, approximate_distance_tolerance=EPS,
        )
        wmc = _pathsum_rust.check_equivalence(
            left, right, method="wmc_only", strategy="Naive",
            tool_name=solver, timeout=45, approximate_distance_tolerance=EPS,
        )
    assert normalize_status(rr) == "unknown", (solver, theta, rr)
    assert normalize_status(hybrid) == expected, (solver, theta, hybrid)
    assert normalize_status(wmc) == expected, (solver, theta, wmc)
    assert "wmc_solver_time_sec" in hybrid
    assert "wmc_solver_time_sec" not in rr


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("theta,expected", [
    ("0.00032", "equivalent"),
    ("0.00048", "not_equivalent"),
])
def test_public_distance_api_contract(backend, theta, expected):
    """The opt-in API must work in both execution backends."""
    left, right = qasm(), qasm("rz(" + theta + ") q[0];\n")
    result = check_equivalence(
        left, right, backend=backend, method="hybrid", strategy="Naive",
        tool_name="gpmc", timeout=45, approximate_distance_tolerance=EPS,
    )
    assert result.equivalent == expected


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_public_sub_f64_distance_guard(backend):
    """WMC float output cannot by itself resolve a projective D of 1e-8."""
    left, right = qasm(), qasm("rz(0.00000002) q[0];\n")
    result = check_equivalence(
        left, right, method="wmc_only", backend=backend, tool_name="gpmc",
        strategy="Naive", timeout=45, approximate_distance_tolerance=1e-8,
    )
    # Explicitly tiny epsilon is a numerical observation, not a proof
    # of a source-exact relation or certified solver arithmetic.
    assert result.equivalent in (
        "equivalent", "equivalent*", "not_equivalent", "unknown",
    )
    assert result.wmc_solver_invoked is True
    assert result.wmc_precision_reason is not None


def test_multi_step_cancellation_preserves_net_rotation_in_python_wmc():
    """Local tiny rotations and cancellations must not erase a larger residue."""
    identity = QuantumCircuit(1)
    multi = QuantumCircuit(1)
    for _ in range(40):
        multi.rz(1.5e-5, 0)
        multi.rz(-1.5e-5, 0)
    multi.rz(6e-4, 0)
    total = QuantumCircuit(1)
    total.rz(6e-4, 0)
    assert Operator(multi).equiv(Operator(total), atol=1e-10, rtol=0)
    assert not Operator(identity).equiv(Operator(total), atol=1e-8, rtol=0)
    for target in (multi, total):
        result = check_equivalence(
            identity, target, backend="python", method="wmc_only",
            strategy="Naive", tool_name="gpmc", timeout=45,
            approximate_distance_tolerance=1e-8, rr_tolerance=1e-6,
        )
        assert result.equivalent == "not_equivalent"
        assert result.tool_time is not None


@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("depth", (60, 80))
def test_true_identity_solver_numerical_floor_is_reported_not_hidden(solver, depth):
    """Solver-specific observations must never become a universal error bound."""
    identity, many_h = QuantumCircuit(1), QuantumCircuit(1)
    for _ in range(depth):
        many_h.h(0)
    assert Operator(identity).equiv(Operator(many_h), atol=1e-12, rtol=0)
    answer = check_equivalence(
        identity, many_h, method="wmc_only", backend="python",
        strategy="Naive", tool_name=solver, timeout=45,
        approximate_distance_tolerance=1e-8,
    )
    assert answer.equivalent in ("equivalent", "unknown"), (solver, depth, answer.equivalent)
    assert answer.tool_time is not None
    assert answer.log_wmc is not None
    expected_log2 = 1 + depth / 2
    observed_rel_error = abs(math.expm1((float(answer.log_wmc) - expected_log2) * math.log(2)))
    assert math.isfinite(observed_rel_error)
    assert observed_rel_error < 1e-8, (solver, depth, observed_rel_error)
    if solver == "ganak":
        # Case-specific reference, not a guarantee for other circuits.
        assert observed_rel_error > 1e-10


@pytest.mark.parametrize("depth", (60, 80))
def test_ganak_tight_distance_does_not_falsely_reject_true_identity(depth):
    identity, many_h = QuantumCircuit(1), QuantumCircuit(1)
    for _ in range(depth):
        many_h.h(0)
    answer = check_equivalence(
        identity, many_h, method="wmc_only", backend="python",
        strategy="Naive", tool_name="ganak", timeout=45,
        approximate_distance_tolerance=1e-8,
    )
    assert answer.equivalent in ("equivalent", "unknown"), answer.equivalent
    assert answer.tool_time is not None


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("bad", (0, 1, -1e-8, float("nan"), float("inf"), False, True, "1e-8"))
def test_public_distance_rejects_invalid_parameters_before_verification(backend, bad):
    with pytest.raises(ValueError, match="approximate_distance_tolerance"):
        check_equivalence(
            qasm(), qasm(), backend=backend, method="reduction_rules",
            approximate_distance_tolerance=bad,
        )


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_removed_magnitude_parameter_is_rejected(backend):
    with pytest.raises(TypeError):
        check_equivalence(
            qasm(), qasm(), backend=backend, method="reduction_rules",
            wmc_magnitude_tolerance=1e-8,
        )


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_opt_in_exact_rr_fast_path_retains_proof_provenance(backend):
    result = check_equivalence(
        qasm(), qasm(), backend=backend, method="hybrid",
        approximate_distance_tolerance=EPS,
    )
    assert result.equivalent == "equivalent"
    assert result.tool_time is None
    assert result.wmc_time is None
    assert result.approximate_distance_tolerance == EPS


def test_projective_distance_threshold_is_not_magnitude_budget():
    eps = 1e-8
    defect = trace_defect_from_distance(eps)
    assert 0 < defect < 1e-16


def test_removed_mutable_magnitude_default():
    assert not hasattr(config, "WMC_MAGNITUDE_TOLERANCE")
    assert config.DEFAULT_DISTANCE_TOLERANCE == 1e-8


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_structural_mismatch_has_consistent_provenance(backend):
    different_size = qasm().replace("qreg q[1]", "qreg q[2]")
    result = check_equivalence(
        qasm(), different_size, backend=backend, method="hybrid",
        approximate_distance_tolerance=EPS,
    )
    assert result.equivalent == "not_equivalent"
    assert result.tool_time is None
    assert result.wmc_solver_invoked is False
    assert result.wmc_time is None


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_none_distance_uses_default(backend):
    result = check_equivalence(
        qasm(), qasm(), backend=backend, method="reduction_rules",
        approximate_distance_tolerance=None,
    )
    assert result.equivalent == "equivalent"
    assert result.approximate_distance_tolerance == 1e-8


def test_direct_pyo3_structural_mismatch_has_explicit_provenance():
    two = qasm().replace("qreg q[1]", "qreg q[2]")
    raw = _pathsum_rust.check_equivalence(
        qasm(), two, method="hybrid", approximate_distance_tolerance=EPS,
    )
    assert raw["status"] == "Not Equivalent"
    assert "wmc_solver_time_sec" not in raw
    assert raw["wmc_solver_invoked"] is False


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_public_wmc_observation_identifies_real_solver_invocation(backend):
    result = check_equivalence(
        qasm(), qasm("rz(0.001) q[0];\n"),
        backend=backend, method="wmc_only", strategy="Naive",
        tool_name="gpmc", timeout=45,
    )
    assert result.wmc_solver_invoked is True
    assert result.wmc_time is not None
    assert result.tool_time is not None
    assert result.wmc_numerical_verdict == result.equivalent

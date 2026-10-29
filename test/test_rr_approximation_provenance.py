"""RR tolerance compatibility, diagnostic provenance and Hybrid handoff.

The local RR tolerance is NOT a projective-distance error budget.
"""
from contextlib import contextmanager
import math

import pytest
import symengine as se
from qiskit import QuantumCircuit

from QuPRS import check_equivalence, config
from QuPRS.pathsum.pattern_match import match_omega
from QuPRS.pathsum.reduction_provenance import (
    capture_rr_provenance, tracked_reduce_expression,
)


@contextmanager
def tolerance(value):
    previous = config.get_tolerance()
    config.set_tolerance(value)
    try:
        yield
    finally:
        config.set_tolerance(previous)


def hsh(extra_rz=0.0):
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.s(0)
    if extra_rz:
        circuit.rz(extra_rz, 0)
    circuit.h(0)
    return circuit


@pytest.mark.parametrize("method", ["reduction_rules", "hybrid"])
def test_loose_rr_tolerance_restores_original_accepted_equivalence(method):
    left = hsh()
    right = hsh(2 * math.pi * 1e-7)
    with tolerance(1e-6):
        result = check_equivalence(
            left, right, method=method, strategy="Naive",
            backend="python", tool_name="gpmc",
            approximate_distance_tolerance=1e-8, timeout=15,
        )
    # RR's coefficient tolerance remains independent of projective-distance
    # tolerance; this is an APPROXIMATE RR verdict, not a distance proof.
    assert result.equivalent == "equivalent", result
    assert result.decision_basis == "symbolic"
    assert result.rr_approximation_unbounded
    assert any(
        e["kind"] == "phase_normalization"
        and e["nonconstant"] and e["applied"]
        for e in result.rr_approximation_events
    ), result.rr_approximation_events
    assert not result.wmc_solver_invoked


@pytest.mark.parametrize("method", ["reduction_rules", "hybrid"])
def test_strict_rr_unknown_hybrid_uses_final_pathsum_for_wmc(method):
    from unittest.mock import patch
    from QuPRS.interface import ps2wmc

    left = hsh()
    right = hsh(2 * math.pi * 1e-7)
    passed = []
    original_to_dimacs = ps2wmc.to_DIMACS

    def audited_to_dimacs(pathsum, filename="wmc.cnf", tool_name="gpmc"):
        passed.append(pathsum)
        return original_to_dimacs(pathsum, filename, tool_name)

    with tolerance(1e-10), patch.object(
        ps2wmc, "to_DIMACS", side_effect=audited_to_dimacs
    ):
        result = check_equivalence(
            left, right, method=method, strategy="Naive",
            backend="python", tool_name="gpmc",
            approximate_distance_tolerance=1e-8, timeout=15,
        )
    assert not result.rr_approximation_unbounded
    if method == "hybrid":
        assert result.equivalent == "not_equivalent", result
        assert result.decision_basis == "numerical_approximate"
        assert result.wmc_solver_invoked
        assert len(passed) == 1 and passed[0] is result.final_pathsum
        assert result.wmc_numerical_verdict == "not_equivalent"
        assert result.wmc_precision_reason == "modelled_count_below_distance_threshold"
        assert result.wmc_printed_verdict == "not_equivalent"
    else:
        assert result.equivalent == "unknown", result
        assert result.decision_basis == "inconclusive"
        assert not result.wmc_solver_invoked
        assert passed == []


@pytest.mark.parametrize("method", ["reduction_rules", "hybrid"])
def test_exact_hh_and_omega_remain_available(method):
    identity = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    hh.h(0)
    hh.h(0)
    with tolerance(1e-6):
        hh_result = check_equivalence(
            identity, hh, method=method, strategy="Naive",
            backend="python", approximate_distance_tolerance=1e-8,
            timeout=15,
        )
        omega_result = check_equivalence(
            identity, hsh(), method="reduction_rules", strategy="Naive",
            backend="python", approximate_distance_tolerance=1e-8,
            timeout=15,
        )
    assert hh_result.equivalent in ("equivalent", "equivalent*")
    assert not hh_result.rr_approximation_unbounded
    assert not hh_result.wmc_solver_invoked
    assert omega_result.Statistics.get_reduction_count("omega") > 0
    assert not omega_result.rr_approximation_unbounded


def test_constant_global_phase_is_diagnostic_not_projective_error():
    x = se.Symbol("x")
    with tolerance(1e-6):
        with capture_rr_provenance() as evidence:
            assert tracked_reduce_expression(se.Rational(1, 10_000_000)) == se.S.Zero
            assert not evidence.unbounded
            assert tracked_reduce_expression(se.Rational(1, 10_000_000)*x) == se.S.Zero
            assert evidence.unbounded
    assert evidence.total_events == 2
    assert evidence.events[0]["nonconstant"] is False
    assert evidence.events[1]["nonconstant"] is True


def test_cached_phase_drops_are_audited_on_every_request():
    x = se.Symbol("x")
    with tolerance(1e-6):
        for _ in range(2):
            with capture_rr_provenance() as evidence:
                assert tracked_reduce_expression(se.Rational(1, 10_000_000)*x) == 0
                assert evidence.unbounded
                assert evidence.total_events == 1


def test_near_omega_match_records_unbounded_approximation():
    y, x = se.symbols("y x")
    delta = se.Rational(1, 10_000_000)
    phase = y * (se.Rational(1, 4) + delta + x / 2)
    with tolerance(1e-6):
        with capture_rr_provenance() as evidence:
            match = match_omega(phase, (y,), (y,), (x,))
    assert match[0] is not None
    assert evidence.unbounded
    assert any(e["kind"] == "omega_coefficient_match" for e in evidence.events)


def test_diagnostic_provenance_does_not_change_rr_coefficient_deletion():
    x = se.Symbol("x")
    delta = se.Rational(1, 10_000_000)
    with tolerance(1e-6):
        with capture_rr_provenance() as evidence:
            assert tracked_reduce_expression(delta) == 0
            assert tracked_reduce_expression(delta*x) == 0
    assert evidence.total_events == 2
    assert evidence.unbounded
    assert all(e["applied"] for e in evidence.events)


def test_diagnostic_provenance_does_not_disable_near_omega():
    y, x = se.symbols("y x")
    delta = se.Rational(1, 10_000_000)
    phase = y * (se.Rational(1, 4) + delta + x/2)
    with tolerance(1e-6):
        with capture_rr_provenance() as evidence:
            match = match_omega(phase, (y,), (y,), (x,))
    assert match[0] is not None
    assert evidence.unbounded
    assert any(
        e["kind"] == "omega_coefficient_match" and e["applied"]
        for e in evidence.events
    )


def test_no_provenance_spills_into_independent_circuit_request():
    identity = QuantumCircuit(1)
    with tolerance(1e-6):
        result = check_equivalence(
            identity, identity, method="reduction_rules",
            backend="python", strategy="Naive",
            approximate_distance_tolerance=1e-8, timeout=15,
        )
    assert result.equivalent == "equivalent"
    assert not result.rr_approximation_unbounded
    assert result.rr_approximation_events == ()

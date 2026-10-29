"""Fail-closed RR source-accuracy contract on real circuits and exact controls.

The local RR tolerance is NOT a projective distance error budget.
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
def test_near_hh_nonconstant_phase_no_longer_proves_equivalence(method):
    left = hsh()
    right = hsh(2 * math.pi * 1e-7)
    with tolerance(1e-6):
        observed = check_equivalence(
            left, right, method=method, strategy="Naive",
            backend="python", tool_name="gpmc",
            approximate_distance_tolerance=1e-8, timeout=15,
        )
    assert observed.equivalent == "unknown", observed
    assert observed.decision_basis == "inconclusive"
    assert observed.rr_approximation_unbounded
    assert any(
        event["kind"] == "phase_normalization" and event["nonconstant"]
        for event in observed.rr_approximation_events
    ), observed.rr_approximation_events
    # Never feed a lossy reduced path sum into WMC to "confirm" the identity.
    assert observed.wmc_solver_invoked is False
    assert observed.wmc_numerical_verdict is None


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

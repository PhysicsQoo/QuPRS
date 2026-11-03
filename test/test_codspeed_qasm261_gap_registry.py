"""Cheap, solver-free evidence inventory guard for QASM261 gap studies."""
from pathlib import Path

from benchmarks.codspeed.case_registry import (
    QASM261_COVERAGE_GAP_CASES, QASM261_PILOT_CASES, WALLTIME_CASE_IDS,
)

FIXTURES = Path(__file__).resolve().parents[1] / "benchmarks/MQTBench"


def test_gap_six_distinct_versioned_research_identities():
    cases = QASM261_COVERAGE_GAP_CASES
    assert len(cases) == len({c.id for c in cases}) == 6
    assert not ({c.id for c in cases}
                & ({c.id for c in QASM261_PILOT_CASES} | WALLTIME_CASE_IDS))
    assert all(c.id.startswith("q261_gap_") for c in cases)


def test_gap_covers_wmc_only_python_ganak_positive_and_negative():
    cases = QASM261_COVERAGE_GAP_CASES
    assert {c.backend for c in cases} == {"python", "rust"}
    assert {c.method for c in cases} == {"hybrid", "wmc_only"}
    assert {c.solver for c in cases} == {"gpmc", "ganak"}
    assert {c.expected_verdict for c in cases} == {
        "equivalent_or_phase", "not_equivalent"
    }
    assert sum(c.backend == "python" for c in cases) == 3
    assert sum(c.method == "wmc_only" for c in cases) == 3


def test_gap_pinned_sources_and_censored_timeout_contract():
    for case in QASM261_COVERAGE_GAP_CASES:
        assert case.qasm_corpus == "qiskit-2.6.1-opt0"
        assert case.expected_solver_invoked is True
        assert 0 < case.solver_timeout_s < case.watchdog_s <= 30
        assert (FIXTURES / case.qasm).is_file(), case.id
        target_group = ("Random_Rotation"
                        if case.pair_variant == "random_rotation" else "h,ry,rz,cx")
        assert (FIXTURES / case.qasm_corpus / target_group / case.qasm).is_file(), case.id

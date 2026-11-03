"""Versioned Qiskit 2.6.1 Level-0 QASM screening; distinct CodSpeed URIs.

Bounded manual/experiment branch WallTime only. Source and verdict evidence
were independently archived before this benchmark; no claims of solver
arithmetic certification or a default-suite promotion are made.
"""
import pytest

from benchmarks.codspeed.case_registry import QASM261_PILOT_CASES
from benchmarks.codspeed.test_codspeed_candidate_pilot import (
    run_source_pinned_candidate,
)


@pytest.mark.parametrize(
    "case", QASM261_PILOT_CASES,
    ids=[case.id for case in QASM261_PILOT_CASES],
)
def test_qiskit261_versioned_candidate(benchmark, case):
    return run_source_pinned_candidate(benchmark, case)

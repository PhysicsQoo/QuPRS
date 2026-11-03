"""Bounded QASM261 method/backend/Solver pilot; manual GitHub Actions only.

The first CodSpeed sample is an observation, not a base/HEAD performance
regression.  Source/verdict/stage failures and timeouts are preserved in
the evidence artifact and never silently promoted to every-PR coverage.
"""
import pytest

from benchmarks.codspeed.case_registry import QASM261_COVERAGE_GAP_CASES
from benchmarks.codspeed.test_codspeed_candidate_pilot import (
    run_source_pinned_candidate,
)


@pytest.mark.parametrize(
    "case", QASM261_COVERAGE_GAP_CASES,
    ids=[case.id for case in QASM261_COVERAGE_GAP_CASES],
)
def test_qasm261_coverage_gap(benchmark, case):
    return run_source_pinned_candidate(benchmark, case)

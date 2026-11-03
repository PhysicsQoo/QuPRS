"""Opt-in paper difficulty-gap pilot; never merged into legacy eight IDs."""
import pytest

from benchmarks.codspeed.case_registry import PAPER_GAP_PILOT_CASES
from benchmarks.codspeed.test_codspeed_candidate_pilot import run_source_pinned_candidate


@pytest.mark.parametrize(
    "case", PAPER_GAP_PILOT_CASES, ids=[case.id for case in PAPER_GAP_PILOT_CASES]
)
def test_paper_gap_source_pinned_candidate(benchmark, case):
    return run_source_pinned_candidate(benchmark, case)

"""Research-only contracts: 101 modern Solver cases and precision caveats."""
import json
from pathlib import Path

from scripts import tacas26_modern_full_101 as m
from scripts import tacas26_modern_101_worker as worker


def test_all_101_original_counts_are_source_pinned():
    cohort = m.comparable_source_records(m.ROOT)
    assert len(cohort) == 101
    labels = [m.prior.binary(saved["verdict"]) for _case, saved, _a, _b in cohort]
    assert labels.count("EQUIVALENT") == 45
    assert labels.count("NOT_EQUIVALENT") == 56
    assert sum(case["method"] == "hybrid" for case, *_ in cohort) == 44
    assert sum(case["method"] == "wmc_only" for case, *_ in cohort) == 57
    assert all(source["sha256"] and counterpart["sha256"]
               for _case, _saved, source, counterpart in cohort)


def test_complete_nonoverlapping_24_shard_partition():
    cohort = m.comparable_source_records(m.ROOT)
    pieces = [m.slice_corpus(m.ROOT, i, 24) for i in range(24)]
    assert sum(map(len, pieces)) == 101
    assert sorted(c["id"] for group in pieces for c, *_ in group) == [
        c["id"] for c, *_ in cohort]
    assert all(4 <= len(group) <= 5 for group in pieces)
    assert all(len(group) <= 5 for group in pieces)


def test_no_timeout_or_missing_output_is_accepted_as_not_equivalent():
    assert m.classification("not_equivalent", {"run_status": "COMPLETED",
           "verdict": "not_equivalent"}) == "BINARY_MATCH"
    assert m.classification("equivalent*", {"run_status": "COMPLETED",
           "verdict": "not_equivalent"}) == "BINARY_MISMATCH"
    assert m.classification("not_equivalent", {"run_status": "COMPLETED",
           "verdict": "equivalent*"}) == "BINARY_MISMATCH"
    for status in ("EXTERNAL_WATCHDOG_CENSORED", "PROCESS_OR_OUTPUT_ERROR",
                   "PROCESS_SPAWN_ERROR", "SOLVER_OUTPUT_PARSE_ERROR"):
        assert m.classification("not_equivalent", {"run_status": status,
               "verdict": "not_equivalent"}) == "NOT_MEASURED_OR_CENSORED"
    assert m.classification("not_equivalent", {"run_status": "COMPLETED",
           "verdict": "Timeout"}) == "NOT_MEASURED_OR_CENSORED"


def test_printed_decimal_is_not_a_solver_arithmetic_certificate():
    # A known finite 30-digit count can have a reliable display interval
    # while the GPMC arithmetic and input-weight error remain unbounded.
    stdout = ("c o precision 30\n"
              "c s exact double prec-sci 2097151.99998117482242531644506+0i\n")
    record = worker._solver_stdout_details(stdout, 42, 2e-5)
    assert record["printed_status"] in ("equivalent", "not_equivalent", "unknown")
    assert record["certified_solver_arithmetic"] is False
    assert record["solver_arithmetic_error_bound"] is None
    assert record["solver_arithmetic_certificate"] == "ABSENT"
    assert record["stdout_sha256"] is not None
    assert record["conditional_allowable_count_error"] is not None


def test_wmc_raw_output_error_is_not_certified_even_if_parseable():
    bad = worker._solver_stdout_details("not a solver count", 20, 2e-5)
    assert bad["printed_status"] == "UNCLASSIFIABLE"
    assert bad["certified_solver_arithmetic"] is False

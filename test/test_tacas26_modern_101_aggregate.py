"""Fail-closed aggregator unit tests; no GPMC invocation."""
import json
from decimal import Decimal
import pytest

from scripts import tacas26_modern_101_aggregate as a


def _row(value, cnf="source-pinned-cnf"):
    return {"observation": {"run_status": "COMPLETED", "solver_invoked": True,
            "observed_solver_calls": [{"cnf_sha256": cnf,
                "printed_count": {"solver_printed_complex_re": value,
                    "solver_printed_complex_im": "0", "printed_status": "equivalent",
                    "conditional_allowable_normalized_error": "1e-10"}}]}}


def test_identical_cnf_30_90_digit_gap_is_only_empirical():
    actual = a.normalized_complex_gap(_row("100"), _row("100.000000000000001"))
    assert actual["status"] == "SAME_CNF_PRECISION_COMPARABLE"
    assert Decimal(actual["gpmc_output_relative_difference"]) > 0
    assert actual["arithmetic_bound"] is None
    assert actual["certified_gpmc_arithmetic"] is False


def test_changed_cnf_is_not_a_precision_comparison():
    assert a.normalized_complex_gap(_row("100",cnf="A"),_row("100",cnf="B"))["status"] == "CNF_MISMATCH"


def test_printed_count_cannot_be_invented():
    assert a.normalized_complex_gap(
        {"observation":{"run_status":"COMPLETED","solver_invoked":True,"observed_solver_calls":[]}},
        _row("100"))["status"] == "MISSING_OR_DUPLICATE_RAW_SOLVER_WITNESS"


def test_source_archive_must_be_pinned_before_101_aggregation():
    cohort = a.comparable_source_records(a.ROOT)
    assert len(cohort)==101
    assert sum(row["method"]=="wmc_only" for row,*_ in cohort)==57

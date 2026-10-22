"""Outcome policy regression without external quantum solver processes."""
from types import SimpleNamespace

import pytest

from _benchmark_outcomes import assert_benchmark_result


def _result(status):
    return SimpleNamespace(equivalent=status)


@pytest.mark.parametrize("status", ["equivalent", "equivalent*"])
def test_positive_benchmark_statuses(status):
    record = SimpleNamespace(extra_info={})
    assert_benchmark_result(_result(status), benchmark=record, file_name="example.qasm")
    assert record.extra_info["verification_status"] == "PASS"


@pytest.mark.parametrize("status", ["not_equivalent", "Unknown", "solver_error"])
def test_unexpected_benchmark_status_fails(status):
    record = SimpleNamespace(extra_info={})
    with pytest.raises(AssertionError):
        assert_benchmark_result(_result(status), benchmark=record, file_name="example.qasm")


@pytest.mark.parametrize("status", ["Timeout", "MemoryOut"])
def test_resource_limits_are_inconclusive_not_proved(status):
    record = SimpleNamespace(extra_info={})
    with pytest.raises(pytest.skip.Exception, match="INCONCLUSIVE_RESOURCE"):
        assert_benchmark_result(_result(status), benchmark=record,
                                file_name="example.qasm", tool_name="gpmc",
                                backend="rust")
    assert record.extra_info["verification_status"] == "INCONCLUSIVE_RESOURCE"
    assert record.extra_info["raw_status"] == status
    assert record.extra_info["case"] == "example.qasm"
    assert record.extra_info["solver"] == "gpmc"
    assert record.extra_info["backend"] == "rust"


def test_ganak_format_error_is_failure():
    record = SimpleNamespace(extra_info={})
    with pytest.raises(pytest.fail.Exception):
        assert_benchmark_result(_result("WMC output format error"), benchmark=record,
                                file_name="example.qasm", tool_name="ganak")
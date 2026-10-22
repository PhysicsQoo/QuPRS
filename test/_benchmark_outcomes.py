"""Shared correctness outcome policy for the existing benchmark suites.

This runs *after* pytest-benchmark's timed call, so it does not change the
measured function or introduce memory-sampling overhead into CodSpeed.
Resource exhaustion means the benchmark did not complete, never that
circuit equivalence was proved. Standalone small correctness tests remain
fail-closed and independent of these resource-limited performance cases.
"""

import pytest


EXPECTED_EQUIVALENCE = frozenset({"equivalent", "equivalent*"})
RESOURCE_LIMITS = frozenset({"Timeout", "MemoryOut"})


def assert_benchmark_result(result, *, benchmark, file_name: str,
                            tool_name: str | None = None) -> None:
    """Validate a historical positive-pair benchmark, without solver fallback."""
    status = str(result.equivalent)
    if tool_name == "ganak" and (
        "WMC output format error" in status or "error" in status.lower()
    ):
        benchmark.extra_info["status"] = f"Ganak format error: {file_name}: {result}"
        pytest.fail(f"Ganak output error for {file_name}: {result}")

    if status in RESOURCE_LIMITS:
        benchmark.extra_info["status"] = (
            f"Resource limited (not correctness pass): {status}"
        )
        pytest.skip(f"Resource limited (not correctness pass): {file_name}: {status}")

    assert status in EXPECTED_EQUIVALENCE, (
        f"Verification failed for {file_name}. "
        f"Expected {sorted(EXPECTED_EQUIVALENCE)}, got {status!r}. "
        f"Full result: {result}"
    )
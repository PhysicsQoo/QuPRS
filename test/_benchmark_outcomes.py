"""Shared correctness outcome policy for the existing benchmark suites.

This runs *after* pytest-benchmark's timed call, so it does not change the
measured function or introduce memory-sampling overhead into CodSpeed.
Resource exhaustion is an inconclusive performance sample, not a circuit
verification result. The pytest skip below transports the outcome to JUnit;
the separate coverage gate distinguishes INCONCLUSIVE_RESOURCE from SKIP.
Definitive wrong verdicts and solver format errors remain hard failures.
"""

import pytest


EXPECTED_EQUIVALENCE = frozenset({"equivalent", "equivalent*"})
RESOURCE_LIMITS = frozenset({"Timeout", "MemoryOut"})


def assert_benchmark_result(result, *, benchmark, file_name: str,
                            tool_name: str | None = None,
                            backend: str | None = None) -> None:
    """Validate a historical positive-pair benchmark, without solver fallback."""
    status = str(result.equivalent)
    if tool_name == "ganak" and (
        "WMC output format error" in status or "error" in status.lower()
    ):
        benchmark.extra_info["status"] = f"Ganak format error: {file_name}: {result}"
        pytest.fail(f"Ganak output error for {file_name}: {result}")

    if status in RESOURCE_LIMITS:
        benchmark.extra_info.update({
            "verification_status": "INCONCLUSIVE_RESOURCE",
            "raw_status": status, "case": file_name,
            "solver": tool_name, "backend": backend,
        })
        # This marked pytest skip transports a distinct scientific outcome.
        pytest.skip(
            f"INCONCLUSIVE_RESOURCE: case={file_name}; "
            f"solver={tool_name or 'none'}; backend={backend or 'unknown'}; "
            f"reason={status}. No equivalence or performance pass."
        )

    if status in EXPECTED_EQUIVALENCE:
        benchmark.extra_info["verification_status"] = "PASS"
    assert status in EXPECTED_EQUIVALENCE, (
        f"Verification failed for {file_name}. "
        f"Expected {sorted(EXPECTED_EQUIVALENCE)}, got {status!r}. "
        f"Full result: {result}"
    )
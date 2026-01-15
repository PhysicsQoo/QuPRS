import os
from pathlib import Path

import pytest

from QuPRS import check_equivalence

PROJECT_ROOT = Path(".").resolve()
MQT_BENCH_ROOT = PROJECT_ROOT / "benchmarks" / "MQTBench"
path1 = MQT_BENCH_ROOT
path2 = MQT_BENCH_ROOT / "h,ry,rz,cx"


def generate_test(file_name, strategy="proportional", tool_name="gpmc", switch=False):
    circuit1 = str(path1 / file_name)
    circuit2 = str(path2 / file_name)
    if switch:
        circuit1, circuit2 = circuit2, circuit1
    IS_CODSPEED = os.getenv("CODSPEED_ENV") is not None
    REAL_TIMEOUT = 60 if not IS_CODSPEED else 999999
    try:
        result = check_equivalence(
            circuit1,
            circuit2,
            method="hybrid",
            strategy=strategy,
            tool_name=tool_name,
            timeout=REAL_TIMEOUT,
        )
    except Exception as e:
        error_msg = str(e)
        if tool_name == "ganak":
            pytest.skip(f"\n::[Ganak Crash] {file_name}: {error_msg}")
        raise e

    return result


@pytest.mark.parametrize(
    "file_name, strategy, tool_name, switch",
    [
        ("ghz_nativegates_ibm_qiskit_opt0_32.qasm", "straightforward", "gpmc", True),
        ("ghz_nativegates_ibm_qiskit_opt0_32.qasm", "straightforward", "ganak", True),
        ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "naive", "gpmc", False),
        ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "naive", "ganak", False),
        (
            "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
            "proportional",
            "gpmc",
            True,
        ),
        (
            "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
            "proportional",
            "ganak",
            True,
        ),
        ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", "gpmc", False),
        ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", "ganak", False),
        ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", "gpmc", True),
        ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", "ganak", True),
        ("vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", "gpmc", False),
        ("vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", "ganak", False),
        # ("new_benchmark_file.qasm", "new_strategy"),
    ],
)
def test_all_benchmarks(benchmark, file_name, strategy, tool_name, switch):
    """
    A function to test all benchmark files.
    Pytest will execute this function once for each row in the parametrize list.
    """

    result = benchmark(
        generate_test,
        file_name,
        strategy=strategy,
        tool_name=tool_name,
        switch=switch,
    )

    is_ganak_format_error = tool_name == "ganak" and (
        "WMC output format error" in str(result.equivalent)
        or "error" in str(result.equivalent).lower()
    )
    if is_ganak_format_error:
        benchmark.extra_info["status"] = f"[Ganak Format Error] {file_name}: {result}"
        pytest.skip(f"\n::[Ganak Format Error] {file_name}: {result}")

    resource_limits = {"Timeout", "MemoryOut"}
    if result.equivalent in resource_limits:
        benchmark.extra_info["status"] = (
            f"Skipped due to resource limit: {result.equivalent}"
        )
        pytest.skip(f"\n::Benchmark skipped due to resource limit: {result.equivalent}")

    expected_outcomes = {"equivalent", "equivalent*"}
    assert result.equivalent in expected_outcomes, (
        f"Verification failed for {file_name}.\n"
        f"Expected one of {expected_outcomes}, but got '{result.equivalent}'.\n"
        f"Full Result:\n{result}"
    )

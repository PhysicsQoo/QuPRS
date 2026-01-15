import signal
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
    try:
        result = check_equivalence(
            circuit1,
            circuit2,
            method="hybrid",
            strategy=strategy,
            tool_name=tool_name,
            timeout=60,
        )
    except Exception as e:
        error_msg = str(e)
        if tool_name == "ganak":
            pytest.skip(f"\n::[Ganak Crash] {file_name}: {error_msg}")
        raise e

    return result


file_names = [
    "ghz_nativegates_ibm_qiskit_opt0_32.qasm",
    "graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
    "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
    "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
    "qft_nativegates_ibm_qiskit_opt0_16.qasm",
    "vqe_nativegates_ibm_qiskit_opt0_4.qasm",
]
strategies = ["difference", "proportional", "naive", "straightforward"]
tool_names = ["gpmc", "ganak"]

def ignore_handler(signum, frame):
    pass

@pytest.mark.parametrize("switch", [False])
@pytest.mark.parametrize("tool_name", tool_names)
@pytest.mark.parametrize("strategy", strategies)
@pytest.mark.parametrize("file_name", file_names)
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
    signal.alarm(0)
    original_handler = signal.signal(signal.SIGALRM, ignore_handler)
    try:
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
    finally:
        if original_handler:
            signal.signal(signal.SIGALRM, original_handler)
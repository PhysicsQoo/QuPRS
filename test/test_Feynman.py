from pathlib import Path

import pytest

from QuPRS import check_equivalence

PROJECT_ROOT = Path(".").resolve()
Feynman_BENCH_ROOT = PROJECT_ROOT / "benchmarks" / "Feynman"
path1 = Feynman_BENCH_ROOT
path2 = Feynman_BENCH_ROOT / "h,y,z,t,tdg,cx"


def generate_test(file_name, strategy="proportional", switch=False):
    circuit1 = str(path1 / file_name)
    circuit2 = str(path2 / file_name)
    if switch:
        circuit1, circuit2 = circuit2, circuit1
    result = check_equivalence(
        circuit1, circuit2, method="reduction_rules", strategy=strategy, timeout=60
    )

    return result


@pytest.mark.parametrize(
    "file_name, strategy, switch",
    [
        ("adder_8.qasm", "proportional", False),
        ("gf2^4_mult.qasm", "proportional", False),
        ("tof_3.qasm", "proportional", True),
        ("vbe_adder_3.qasm", "proportional", True),
        # ("new_benchmark_file.qasm", "new_strategy"),
    ],
)
def test_all_benchmarks(benchmark, file_name, strategy, switch):
    """
    A function to test all benchmark files.
    Pytest will execute this function once for each row in the parametrize list.
    """
    result = benchmark(generate_test, file_name, strategy=strategy, switch=switch)

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

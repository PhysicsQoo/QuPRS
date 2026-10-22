import os
from pathlib import Path

import pytest

from QuPRS import check_equivalence
from _benchmark_cases import MQT_CASES
from _benchmark_outcomes import assert_benchmark_result

PROJECT_ROOT = Path(".").resolve()
MQT_BENCH_ROOT = PROJECT_ROOT / "benchmarks" / "MQTBench"
path1 = MQT_BENCH_ROOT
path2 = MQT_BENCH_ROOT / "h,ry,rz,cx"


def generate_test(file_name, strategy="proportional", tool_name="gpmc", switch=False, backend="python"):
    circuit1 = str(path1 / file_name)
    circuit2 = str(path2 / file_name)
    if switch:
        circuit1, circuit2 = circuit2, circuit1
    IS_CODSPEED = os.getenv("CODSPEED_ENV") is not None
    REAL_TIMEOUT = 60 if not IS_CODSPEED else 999999
    result = check_equivalence(
        circuit1,
        circuit2,
        method="hybrid",
        strategy=strategy,
        tool_name=tool_name,
        timeout=REAL_TIMEOUT,
        backend=backend,
    )

    return result


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("tool_name", ["gpmc", "ganak"])
@pytest.mark.parametrize("file_name, strategy, switch", MQT_CASES)
def test_all_benchmarks(benchmark, file_name, strategy, tool_name, switch, backend):
    """Run the paper-selected MQT pair using the historical Hybrid settings."""
    result = benchmark(
        generate_test,
        file_name,
        strategy=strategy,
        tool_name=tool_name,
        switch=switch,
        backend=backend,
    )
    assert_benchmark_result(
        result, benchmark=benchmark, file_name=file_name, tool_name=tool_name,
        backend=backend,
    )
import os
from pathlib import Path

import pytest

from QuPRS import check_equivalence
from _benchmark_cases import FEYNMAN_CASES
from _benchmark_outcomes import assert_benchmark_result

PROJECT_ROOT = Path(".").resolve()
Feynman_BENCH_ROOT = PROJECT_ROOT / "benchmarks" / "Feynman"
path1 = Feynman_BENCH_ROOT
path2 = Feynman_BENCH_ROOT / "h,y,z,t,tdg,cx"


def generate_test(file_name, strategy="proportional", switch=False, backend="python"):
    circuit1 = str(path1 / file_name)
    circuit2 = str(path2 / file_name)
    if switch:
        circuit1, circuit2 = circuit2, circuit1

    IS_CODSPEED = os.getenv("CODSPEED_ENV") is not None
    REAL_TIMEOUT = 60 if not IS_CODSPEED else 999999

    result = check_equivalence(
        circuit1,
        circuit2,
        method="reduction_rules",
        strategy=strategy,
        timeout=REAL_TIMEOUT,
        backend=backend,
    )

    return result


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("file_name, strategy, switch", FEYNMAN_CASES)
def test_all_benchmarks(benchmark, file_name, strategy, switch, backend):
    """Run the paper-selected Feynman pair using historical Reduction settings."""
    result = benchmark(
        generate_test, file_name, strategy=strategy, switch=switch, backend=backend
    )
    assert_benchmark_result(result, benchmark=benchmark, file_name=file_name,
                            backend=backend)
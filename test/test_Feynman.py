import pytest

from QuPRS import check_equivalence

path1 = "./benchmarks/Feynman/"
path2 = "./benchmarks/Feynman/h,y,z,t,tdg,cx/"


def generate_test(file_name, strategy="proportional"):
    circuit1 = path1 + file_name
    circuit2 = path2 + file_name
    result = check_equivalence(
        circuit1, circuit2, method="reduction_rules", strategy=strategy
    )
    assert (
        result.equivalent == "equivalent" or result.equivalent == "equivalent*"
    ), f"Expected equivalent or equivalent*, got {result.equivalent} \n {result}"


@pytest.mark.parametrize(
    "file_name, strategy",
    [
        ("adder_8.qasm", "proportional"),
        ("gf2^4_mult.qasm", "proportional"),
        ("tof_3.qasm", "proportional"),
        ("vbe_adder_3.qasm", "proportional"),
        # ("new_benchmark_file.qasm", "new_strategy"),
    ],
)
def test_all_benchmarks(benchmark, file_name, strategy):
    """
    A function to test all benchmark files.
    Pytest will execute this function once for each row in the parametrize list.
    """
    benchmark(generate_test, file_name, strategy=strategy)

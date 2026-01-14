import pytest

from QuPRS import check_equivalence

path1 = "./benchmarks/Feynman/"
path2 = "./benchmarks/Feynman/h,y,z,t,tdg,cx/"


def generate_test(file_name, strategy="proportional", switch=False):
    circuit1 = path1 + file_name
    circuit2 = path2 + file_name
    if switch:
        circuit1, circuit2 = circuit2, circuit1
    result = check_equivalence(
        circuit1, circuit2, method="reduction_rules", strategy=strategy
    )
    assert (
        result.equivalent == "equivalent" or result.equivalent == "equivalent*"
    ), f"Expected equivalent or equivalent*, got {result.equivalent} \n {result}"

file_names = [
    "adder_8.qasm",
    "gf2^4_mult.qasm",
    "tof_3.qasm",
    "vbe_adder_3.qasm",
]
strategies = ["proportional"]

@pytest.mark.parametrize("switch", [False])
@pytest.mark.parametrize("strategy", strategies)
@pytest.mark.parametrize("file_name", file_names)
def test_all_benchmarks(benchmark, file_name, strategy, switch):
    """
    A function to test all benchmark files.
    Pytest will execute this function once for each row in the parametrize list.
    """
    benchmark(generate_test, file_name, strategy=strategy, switch=switch)

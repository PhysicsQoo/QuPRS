import pytest

from QuPRS import check_equivalence

path1 = "./benchmarks/MQTBench/"
path2 = "./benchmarks/MQTBench/h,ry,rz,cx/"


def generate_test(file_name, strategy="proportional", switch=False):
    circuit1 = path1 + file_name
    circuit2 = path2 + file_name
    if switch:
        circuit1, circuit2 = circuit2, circuit1
    result = check_equivalence(
        circuit1, circuit2, method="hybrid", strategy=strategy
    )
    assert (
        result.equivalent == "equivalent" or result.equivalent == "equivalent*"
    ), f"Expected equivalent or equivalent*, got {result.equivalent} \n {result}"

@pytest.mark.parametrize(
    "file_name, strategy, switch",
    [
        ("ghz_nativegates_ibm_qiskit_opt0_32.qasm", "straightforward", True),
        ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "naive", False),
        ("grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", True),
        ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", False),
        ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", True),
        ("vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", False),
        # ("new_benchmark_file.qasm", "new_strategy"),
    ],
)
def test_all_benchmarks(benchmark, file_name, strategy, switch):
    """
    A function to test all benchmark files.
    Pytest will execute this function once for each row in the parametrize list.
    """
    benchmark(generate_test, file_name, strategy=strategy, switch=switch)

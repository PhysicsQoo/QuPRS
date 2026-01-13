import pytest

from QuPRS import check_equivalence

path1 = "./benchmarks/MQTBench/"
path2 = "./benchmarks/MQTBench/h,ry,rz,cx/"


def generate_test(file_name, strategy="proportional", tool_name="gpmc", switch=False):
    circuit1 = path1 + file_name
    circuit2 = path2 + file_name
    if switch:
        circuit1, circuit2 = circuit2, circuit1
    result = check_equivalence(circuit1, circuit2, method="hybrid", strategy=strategy, tool_name=tool_name)
    assert (
        result.equivalent == "equivalent" or result.equivalent == "equivalent*"
    ), f"Expected equivalent or equivalent*, got {result.equivalent} \n {result}"


@pytest.mark.parametrize(
    "file_name, strategy, tool_name, switch",
    [
        ("ghz_nativegates_ibm_qiskit_opt0_32.qasm", "straightforward","gpmc", True),
        ("ghz_nativegates_ibm_qiskit_opt0_32.qasm", "straightforward","ganak", True),
        ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "naive","gpmc", False),
        ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "naive","ganak", False),
        ("grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "proportional","gpmc", True),
        ("grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "proportional","ganak", True),
        ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional","gpmc", False),
        ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional","ganak", False),
        ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional","gpmc", True),
        ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional","ganak", True),
        ("vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional","gpmc", False),
        ("vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional","ganak", False),
        # ("new_benchmark_file.qasm", "new_strategy"),
    ],
)
def test_all_benchmarks(benchmark, file_name, strategy, tool_name, switch):
    """
    A function to test all benchmark files.
    Pytest will execute this function once for each row in the parametrize list.
    """
    try:
        benchmark(generate_test, file_name, strategy=strategy, tool_name=tool_name, switch=switch)
    except AssertionError as e:
        error_msg = str(e)
        if tool_name == "ganak" and "WMC output format error" in error_msg:
            pytest.skip(f"Ganak runtime crashed: {error_msg}")
        else:
            raise e

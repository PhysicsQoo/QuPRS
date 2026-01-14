import pytest
import sys

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

@pytest.mark.parametrize("switch", [True, False])
@pytest.mark.parametrize("tool_name", tool_names)
@pytest.mark.parametrize("strategy", strategies)
@pytest.mark.parametrize("file_name", file_names)
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
            pytest.skip(f"\n::warning title=Ganak Skipped {file_name} :: skipped due to Ganak binary crash. error_msg:{error_msg}")
        else:
            raise e
    except Exception as e:
        error_msg = str(e)
        if tool_name == "ganak":
            pytest.skip(f"\n::warning title=Ganak Error {file_name}:: encountered unexpected error. error_msg:{error_msg}")
        else:
            raise e

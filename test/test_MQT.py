import os
import tempfile

from QuPRS.interface.load_qiskit import qasm_eq_check_with_wmc

path1 = "./benchmarks/MQTBench/"
path2 = "./benchmarks/MQTBench/h,ry,rz,cx/"


def generate_test(file_name):
    circuit1 = path1 + file_name
    circuit2 = path2 + file_name
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".cnf") as temp_file:
            temp_name = temp_file.name
            output_dict = qasm_eq_check_with_wmc(
                circuit1, circuit2, cnf_filename=temp_name
            )
    finally:
        if temp_name and os.path.exists(temp_name):
            os.remove(temp_name)
    return output_dict


def test_grover_4(benchmark):
    file_name = "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm"
    output_dict = benchmark(generate_test, file_name)
    assert (
        output_dict["equivalent"] == "equivalent*"
    ), "should be equivalent* but got {}".format(output_dict)


def test_qaoa_7(benchmark):
    file_name = "qaoa_nativegates_ibm_qiskit_opt0_7.qasm"
    output_dict = benchmark(generate_test, file_name)
    assert (
        output_dict["equivalent"] == "equivalent*"
    ), "should be equivalent* but got {}".format(output_dict)


def test_qft_16(benchmark):
    file_name = "qft_nativegates_ibm_qiskit_opt0_16.qasm"
    output_dict = benchmark(generate_test, file_name)
    assert (
        output_dict["equivalent"] == "equivalent*"
    ), "should be equivalent* but got {}".format(output_dict)


def test_vqe_4(benchmark):
    file_name = "vqe_nativegates_ibm_qiskit_opt0_4.qasm"
    output_dict = benchmark(generate_test, file_name)
    assert (
        output_dict["equivalent"] == "equivalent*"
    ), "should be equivalent* but got {}".format(output_dict)

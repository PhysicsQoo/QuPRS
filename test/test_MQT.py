from QuPRS import check_equivalence

path1 = "./benchmarks/MQTBench/"
path2 = "./benchmarks/MQTBench/h,ry,rz,cx/"


def generate_test(file_name):
    circuit1 = path1 + file_name
    circuit2 = path2 + file_name
    return check_equivalence(circuit1, circuit2)


def test_grover_4(benchmark):
    file_name = "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm"
    result = benchmark(generate_test, file_name)

    assert (
        result.equivalent == "equivalent*"
    ), "should be equivalent* but got {}".format(result.equivalent)


def test_qaoa_7(benchmark):
    file_name = "qaoa_nativegates_ibm_qiskit_opt0_7.qasm"
    result = benchmark(generate_test, file_name)

    assert (
        result.equivalent == "equivalent*"
    ), "should be equivalent* but got {}".format(result.equivalent)


def test_qft_16(benchmark):
    file_name = "qft_nativegates_ibm_qiskit_opt0_16.qasm"
    result = benchmark(generate_test, file_name)

    assert (
        result.equivalent == "equivalent*"
    ), "should be equivalent* but got {}".format(result.equivalent)


def test_vqe_4(benchmark):
    file_name = "vqe_nativegates_ibm_qiskit_opt0_4.qasm"
    result = benchmark(generate_test, file_name)

    assert (
        result.equivalent == "equivalent*"
    ), "should be equivalent* but got {}".format(result.equivalent)

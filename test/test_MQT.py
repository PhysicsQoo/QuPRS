from QuPRS import check_equivalence

path1 = "./benchmarks/MQTBench/"
path2 = "./benchmarks/MQTBench/h,ry,rz,cx/"


def generate_test(file_name, strategy= "proportional"):
    circuit1 = path1 + file_name
    circuit2 = path2 + file_name
    result = check_equivalence(circuit1, circuit2, strategy= strategy)
    assert (
            result.equivalent == "equivalent" or result.equivalent == "equivalent*"
        ), f"Expected equivalent or equivalent*, got {result.equivalent} \n {result}"
   

def test_ghz_32(benchmark):
    file_name = "ghz_nativegates_ibm_qiskit_opt0_32.qasm"
    benchmark(generate_test, file_name, strategy="straightforward")
def test_graphstate_16(benchmark):
    file_name = "graphstate_nativegates_ibm_qiskit_opt0_16.qasm"
    benchmark(generate_test, file_name, strategy="naive")

def test_grover_4(benchmark):
    file_name = "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm"
    benchmark(generate_test, file_name)

def test_qaoa_7(benchmark):
    file_name = "qaoa_nativegates_ibm_qiskit_opt0_7.qasm"
    benchmark(generate_test, file_name)


def test_qft_16(benchmark):
    file_name = "qft_nativegates_ibm_qiskit_opt0_16.qasm"
    benchmark(generate_test, file_name)


def test_vqe_4(benchmark):
    file_name = "vqe_nativegates_ibm_qiskit_opt0_4.qasm"
    benchmark(generate_test, file_name)

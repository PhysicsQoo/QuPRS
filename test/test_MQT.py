from QuPRS.interface.load_qiskit import qasm_eq_check_with_wmc

path1 = "./benchmarks/MQTBench/"
path2 = "./benchmarks/MQTBench/h,ry,rz,cx/"

def test_grover_4():
    file_name = "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm"
    circuit1 = path1 + file_name
    circuit2 = path2 + file_name
    output_dict = qasm_eq_check_with_wmc(circuit1, circuit2)
    assert output_dict["equivalent"] == "equivalent*", "should be equivalent* but got {}".format(output_dict)

def test_qaoa_7():
    file_name = "qaoa_nativegates_ibm_qiskit_opt0_7.qasm"
    circuit1 = path1 + file_name
    circuit2 = path2 + file_name
    output_dict = qasm_eq_check_with_wmc(circuit1, circuit2)
    assert output_dict["equivalent"] == "equivalent*", "should be equivalent* but got {}".format(output_dict)
def test_qft_16():
    file_name = "qft_nativegates_ibm_qiskit_opt0_16.qasm"
    circuit1 = path1 + file_name
    circuit2 = path2 + file_name
    output_dict = qasm_eq_check_with_wmc(circuit1, circuit2)
    assert output_dict["equivalent"] == "equivalent*", "should be equivalent* but got {}".format(output_dict)

def test_vqe_4():
    file_name = "vqe_nativegates_ibm_qiskit_opt0_4.qasm"
    circuit1 = path1 + file_name
    circuit2 = path2 + file_name
    output_dict = qasm_eq_check_with_wmc(circuit1, circuit2)
    assert output_dict["equivalent"] == "equivalent*", "should be equivalent* but got {}".format(output_dict)
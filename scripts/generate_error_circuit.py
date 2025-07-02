from QuPRS.utils.Qiskit_Circuit_Utils import add_random_rotation_gates
from QuPRS.interface.load_qiskit import load_circuit
import os


def generate_error_circuit(path1, path2):
    files =os.listdir(path1)
    files = list(filter(lambda x: x.endswith('.qasm'), files))
    for file in files:
        circuit = load_circuit(path1+file)
        gate_num = len(circuit.data)
        num_add_gates = int(gate_num * 0.01)+1
        add_random_rotation_gates(path1+file, num_add_gates, 'qasm2_file' ,path2+file)

if __name__ == "__main__":
    path1 = "../benchmarks/MQTBench/h,ry,rz,cx/"
    path2 = "../benchmarks/MQTBench/Random_Rotation/"
    if not os.path.exists(path2):
        os.makedirs(path2)
    # Add random rotation gates to the circuits in path1 and save them in path2
    generate_error_circuit(path1, path2)

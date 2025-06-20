import signal
import time

import numpy as np
import symengine as se
from qiskit import QuantumCircuit, qasm2, qasm3

from QuPRS import config
from QuPRS.interface.gate_library import gate_map, support_gate_set
from QuPRS.pathsum import PathSum, Register


def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")


signal.signal(signal.SIGALRM, timeout_handler)


def build_circuit(circuit: QuantumCircuit, initial_state: bool | list | tuple = None):
    pathsum_circuit = initialize(circuit, initial_state)
    gate_list = get_gates(circuit)
    for gate in gate_list:
        assert gate[0] in support_gate_set, "Not support %s gate yet." % gate[0]
        # print(pathsum_circuit, gate)
        pathsum_circuit = gate_map(
            pathsum_circuit,
            gate[0],
            [f"{item[0]}_{item[1]}" for item in gate[1]],
            gate[2],
        )

    return pathsum_circuit


def initialize(circuit: QuantumCircuit, initial_state: bool | list | tuple = None):
    """
    Construct initial PathSum and the name mapping.
    """
    qiskit_regs = circuit.qregs
    regs = []
    for reg in qiskit_regs:
        regs.append(Register(reg.size, reg.name))

    return PathSum.QuantumCircuit(*regs, initial_state=initial_state)


def get_gate(circuit: QuantumCircuit, gate):
    """Get a gate properties."""
    gate_name = gate.operation.name
    gate_params = gate.operation.params
    qubits_old = gate.qubits
    qubits = []
    for qubit in qubits_old:
        QuantumRegister = circuit.find_bit(qubit).registers
        qubits.append((QuantumRegister[0][0].name, QuantumRegister[0][1]))
    return gate_name, tuple(qubits), tuple(gate_params)


def get_gates(circuit: QuantumCircuit):
    gates = []
    for gate in circuit.data:
        gates.append(get_gate(circuit, gate))
    return gates


def add_gate(
    pathsum_circuit: PathSum, gate, is_bra=False, count=0, debug=False
) -> tuple[PathSum, int]:
    assert gate[0] in support_gate_set, "Not support %s gate yet." % gate[0]
    if debug:
        print(f"gate:{gate}, is_bra: {is_bra}")
    pathsum_circuit = gate_map(
        pathsum_circuit,
        gate[0],
        [f"{item[0]}_{item[1]}" for item in gate[1]],
        gate[2],
        is_bra,
    )

    count += 1
    if debug:
        print(count, pathsum_circuit)
    return pathsum_circuit, count


def load_circuit(circuit: str) -> QuantumCircuit:
    """
    Load a Qiskit circuit from a file or qasm string.

    Args:
        circuit (str): The path to the QASM file or a QASM string.

    Returns:
        QuantumCircuit: The loaded Qiskit circuit.
    """
    if isinstance(circuit, str):
        if circuit.endswith(".qasm"):
            f = open(circuit, "r")
            data = f.read()
            if "OPENQASM 3.0" in data:
                return qasm3.load(circuit)
            else:
                return qasm2.load(circuit)
        elif "OPENQASM" in circuit:
            if "OPENQASM 3.0" in circuit:
                return qasm3.loads(circuit)
            else:
                return qasm2.loads(circuit)
        else:
            raise ValueError("Invalid circuit format")
    elif isinstance(circuit, QuantumCircuit):
        return circuit


def qasm_eq_check(
    circuit1: str | QuantumCircuit,
    circuit2: str | QuantumCircuit,
    strategy="Difference",
    Benchmark_Name=None,
    timeout=600,
):
    tolerance = config.TOLERANCE

    qiskit_circuit = load_circuit(circuit1)
    qiskit_circuit2 = load_circuit(circuit2)

    start_time = time.time()

    initial_state = initialize(qiskit_circuit)
    pathsum_circuit = initial_state
    qubit_num = initial_state.num_qubits

    l1 = len(qiskit_circuit.data)
    l2 = len(qiskit_circuit2.data)

    output_dict = {
        "Benchmark_Name": Benchmark_Name,
        "qubit_num": qubit_num,
        "gate_num": l1,
        "gate_num2": l2,
    }

    if strategy == "Proportional":
        from QuPRS.utils.strategy import proportional

        output_dict, pathsum_circuit = proportional(
            pathsum_circuit,
            qiskit_circuit,
            qiskit_circuit2,
            l1,
            l2,
            output_dict,
            timeout,
        )
    elif strategy == "Naive":
        from QuPRS.utils.strategy import naive

        output_dict, pathsum_circuit = naive(
            pathsum_circuit,
            qiskit_circuit,
            qiskit_circuit2,
            l1,
            l2,
            output_dict,
            timeout,
        )
    elif strategy == "Straightforward":
        from QuPRS.utils.strategy import straightforward

        output_dict, pathsum_circuit = straightforward(
            pathsum_circuit,
            qiskit_circuit,
            qiskit_circuit2,
            l1,
            l2,
            output_dict,
            timeout,
        )
    elif strategy == "Difference":
        from QuPRS.utils.strategy import difference

        output_dict, pathsum_circuit = difference(
            pathsum_circuit,
            qiskit_circuit,
            qiskit_circuit2,
            l1,
            l2,
            output_dict,
            timeout,
        )
    else:
        raise ValueError("Invalid strategy")
    if "equivalent" in output_dict:
        return output_dict, pathsum_circuit
    else:
        total_time = time.time() - start_time
        output_dict["Time"] = round(total_time, 3)

        if pathsum_circuit.f == initial_state.f:
            if pathsum_circuit.P == initial_state.P:
                output_dict["equivalent"] = "equivalent"
            P_free_symbols = pathsum_circuit.P.free_symbols
            check_P_symbol = tuple(
                filter(lambda x: x.name in pathsum_circuit.f.bits, P_free_symbols)
            )
            if len(P_free_symbols) == 0:
                if pathsum_circuit.P < tolerance:
                    output_dict["equivalent"] = "equivalent"
                else:
                    output_dict["equivalent"] = "equivalent*"
            elif len(check_P_symbol) == 0:
                output_dict["equivalent"] = "equivalent*"
            else:
                output_dict["equivalent"] = "not_equivalent"
            return output_dict, pathsum_circuit
        else:
            output_dict["equivalent"] = "unknown"
            return output_dict, pathsum_circuit


def qasm_eq_check_with_wmc(
    circuit1: str | QuantumCircuit,
    circuit2: str | QuantumCircuit,
    strategy="Difference",
    Benchmark_Name=None,
    cnf_filename=None,
    timeout=600,
):
    tolerance = config.TOLERANCE

    output_dict, circuit = qasm_eq_check(
        circuit1=circuit1,
        circuit2=circuit2,
        strategy=strategy,
        Benchmark_Name=Benchmark_Name,
        timeout=timeout,
    )
    wmc_time = 0
    log_wmc = None
    expect = None
    theta = None
    to_DIMACS_time = 0
    if output_dict["equivalent"] == "unknown":
        from QuPRS.interface.ps2wmc import run_wmc, to_DIMACS
        from QuPRS.utils.util import get_theta

        expect = circuit.num_qubits + circuit.num_pathvar / 2
        signal.alarm(timeout)
        start_time = time.time()
        try:
            if cnf_filename is None:
                cnf_filename = "wmc.cnf"
            to_DIMACS(circuit, cnf_filename)
            to_DIMACS_time = round(time.time() - start_time, 3)
        except TimeoutError:
            to_DIMACS_time = f">{timeout}"
        finally:
            signal.alarm(0)

        if to_DIMACS_time != f">{timeout}":
            signal.alarm(timeout)
            start_time = time.time()
            try:
                complex_number = run_wmc(cnf_filename)
                wmc_time = round(time.time() - start_time, 3)
                abs_num = np.sqrt(complex_number[0] ** 2 + complex_number[1] ** 2)
                log_wmc = round(np.log2(abs_num), 3)
                theta = get_theta(
                    complex_number[1] / abs_num, complex_number[0] / abs_num
                )
                if abs(log_wmc - expect) < tolerance:
                    if abs(theta) < tolerance * 2 * np.pi:
                        output_dict["equivalent"] = "equivalent"
                    else:
                        output_dict["equivalent"] = "equivalent*"
                else:
                    output_dict["equivalent"] = "not_equivalent"
            except TimeoutError:
                wmc_time = f">{timeout}"
            finally:
                signal.alarm(0)

    elif output_dict["equivalent"] == "equivalent*":
        theta = str((circuit.P * 2 * se.pi).evalf())
    elif output_dict["equivalent"] == "equivalent":
        theta = 0

    output_dict["PathSum_time"] = output_dict["Time"]
    output_dict["to_DIMACS_time"] = to_DIMACS_time
    output_dict["wmc_time"] = wmc_time
    if (
        output_dict["equivalent"] == "Timeout"
        or to_DIMACS_time == f">{timeout}"
        or wmc_time == f">{timeout}"
    ):
        output_dict["equivalent"] = "Timeout"
        output_dict["Time"] = f">{timeout}"
    else:
        output_dict["Time"] = round(
            wmc_time + to_DIMACS_time + output_dict["PathSum_time"], 3
        )
    return output_dict

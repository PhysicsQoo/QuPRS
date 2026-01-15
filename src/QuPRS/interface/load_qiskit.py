import signal
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
from qiskit import QuantumCircuit, qasm2, qasm3

from QuPRS import config
from QuPRS.interface.gate_library import gate_map, support_gate_set
from QuPRS.pathsum import PathSum, Register
from QuPRS.pathsum.statistics import StatisticsManager
from QuPRS.utils.util import set_safe_memory_limit


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


# =============================================================================
# check_equivalence: Unified Quantum Circuit Equivalence Checking Interface
# =============================================================================
# This function provides a unified interface for verifying the equivalence of two
# quantum circuits using various verification methods, including reduction rules,
# weighted model counting (WMC), or a hybrid approach. It is designed to be
# extensible and follows the documentation and code style conventions of this
# project. All lines are wrapped to comply with E501, and spacing follows E226.
# =============================================================================


def check_equivalence(
    circuit1: str | QuantumCircuit,
    circuit2: str | QuantumCircuit,
    method: str = "hybrid",
    strategy: str = "Difference",
    tool_name: str = "gpmc",
    timeout: int = 600,
    safe_mode: bool = False,
):
    """
    Check whether two quantum circuits are equivalent using different verification
    methods.

    Args:
        circuit1 (str | QuantumCircuit): The first quantum circuit to compare. It can
            be a file path or a Qiskit circuit object.
        circuit2 (str | QuantumCircuit): The second quantum circuit to compare. It can
            be a file path or a Qiskit circuit object.
        method (str, optional): Verification method. Default is "hybrid".
            - 'hybrid': Uses both Reduction Rules (RR) and Weighted Model Counting
              (WMC). This is the recommended mode.
            - 'reduction_rules': Uses only Reduction Rules. If reduction is
              incomplete, returns 'unknown'.
            - 'wmc_only': Uses only Weighted Model Counting (WMC), without any
              reduction.
        strategy (str, optional): Internal strategy for handling quantum gates.
            Default is "Difference".
            - 'Difference': Uses a difference-based strategy.
            - 'Proportional': Uses a proportional strategy.
            - 'Naive': Uses a naive strategy.
            - 'Straightforward': Uses a straightforward strategy.
        timeout (int, optional): Timeout in seconds for the operation. Default is 600.
        safe_mode (bool, optional): If True, enables safe mode with memory limits by
            using multiple processes. Default is False.

    Returns:
        EquivalenceCheckResult: An object containing the result dictionary and the
            final PathSum circuit object.
    """
    # Validate method argument
    if method not in ["hybrid", "reduction_rules", "wmc_only"]:
        raise ValueError(
            "Invalid method parameter. Choose from 'hybrid', "
            "'reduction_rules', or 'wmc_only'."
        )
    try:
        from QuPRS.utils.strategy import Strategy

        strategy_obj = Strategy.get(strategy)
    except ValueError as e:
        raise e

    tolerance = config.TOLERANCE

    # Load circuits from file or QASM string
    qiskit_circuit1 = load_circuit(circuit1)
    qiskit_circuit2 = load_circuit(circuit2)

    start_time = time.time()

    # Initialize PathSum circuit and reduction switch
    initial_state = initialize(qiskit_circuit1)
    pathsum_circuit = initial_state
    reduction_enabled = method != "wmc_only"
    pathsum_circuit.set_reduction_switch(reduction_enabled)
    qubit_num = initial_state.num_qubits

    l1 = len(qiskit_circuit1.data)
    l2 = len(qiskit_circuit2.data)

    gates1 = get_gates(qiskit_circuit1)
    gates2 = get_gates(qiskit_circuit2)

    set_safe_memory_limit()
    signal.alarm(timeout)

    try:
        to_DIMACS_time = None
        tool_time = None
        wmc_time = None
        CNF = (None,)
        log_wmc = None
        expect = None

        # Run the selected strategy to build the PathSum circuit
        pathsum_time = f">{timeout}"
        if safe_mode:
            elapsed_so_far = time.time() - start_time
            remaining_time = max(1, int(timeout - elapsed_so_far))
            pathsum_circuit = strategy_obj.safe_run(
                pathsum_circuit, gates1, gates2, timeout=remaining_time
            )
        else:
            pathsum_circuit = strategy_obj.run(pathsum_circuit, gates1, gates2)
        pathsum_time = round(time.time() - start_time, 3)
        progress = f"{strategy_obj.count}/{l1 + l2}"

        # Reduction rules check (if enabled)
        if method != "wmc_only":
            if pathsum_circuit.f == initial_state.f:
                if pathsum_circuit.P == initial_state.P:
                    equivalent = "equivalent"
                P_free_symbols = pathsum_circuit.P.free_symbols
                # check_P_symbol = tuple(
                #     filter(lambda x: x.name in pathsum_circuit.f.bits, P_free_symbols)
                # )
                if len(P_free_symbols) == 0:
                    if pathsum_circuit.P < tolerance:
                        equivalent = "equivalent"
                    else:
                        equivalent = "equivalent*"
                else:
                    equivalent = "unknown"
            elif len(pathsum_circuit.pathvar) == 0:
                equivalent = "not_equivalent"
            else:
                equivalent = "unknown"

        # If reduction is incomplete or WMC-only, run weighted model counting
        if method == "wmc_only" or (method == "hybrid" and equivalent == "unknown"):
            from QuPRS.interface.ps2wmc import run_wmc, to_DIMACS
            from QuPRS.utils.util import get_theta

            current_elapsed = time.time() - start_time
            if current_elapsed >= timeout:
                raise TimeoutError("Timeout before WMC")
            signal.alarm(int(timeout - current_elapsed + 1))
            try:
                to_DIMACS_time = f">{timeout - pathsum_time}"
                log_wmc = None
                theta = None
                expect = pathsum_circuit.num_qubits + pathsum_circuit.num_pathvar / 2
                import os
                import tempfile

                # Convert PathSum to CNF (DIMACS format)
                to_DIMACS_start_time = time.time()
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".cnf"
                ) as temp_file:
                    temp_name = temp_file.name
                    CNF = to_DIMACS(pathsum_circuit, temp_name, tool_name=tool_name)
                to_DIMACS_time = round(time.time() - to_DIMACS_start_time, 3)

                # Run weighted model counting (WMC)
                tool_time = f">{timeout - pathsum_time - to_DIMACS_time}"
                tool_start_time = time.time()
                complex_number = run_wmc(temp_name, tool_name)
                tool_time = round(time.time() - tool_start_time, 3)
                abs_num = np.sqrt(complex_number[0] ** 2 + complex_number[1] ** 2)
                log_wmc = round(np.log2(abs_num), 3)
                theta = get_theta(
                    complex_number[1] / abs_num, complex_number[0] / abs_num
                )
                if abs(log_wmc - expect) < tolerance:
                    if abs(theta) < tolerance * 2 * np.pi:
                        equivalent = "equivalent"
                    else:
                        equivalent = "equivalent*"
                else:
                    equivalent = "not_equivalent"
                wmc_time = tool_time + to_DIMACS_time
                # Clean up temporary CNF file
                if temp_name and os.path.exists(temp_name):
                    os.remove(temp_name)
            finally:
                signal.alarm(0)
        Time = round(time.time() - start_time, 3)

    except TimeoutError:
        Time = f">{timeout}"
        equivalent = "Timeout"
        progress = f"{strategy_obj.count}/{l1 + l2}"
        signal.alarm(0)
    except MemoryError:
        Time = round(time.time() - start_time, 3)
        if pathsum_time == f">{timeout}":
            pathsum_time = Time
        equivalent = "MemoryOut"
        progress = f"{strategy_obj.count}/{l1 + l2}"
        signal.alarm(0)
    except Exception as e:
        signal.alarm(0)
        raise e
    finally:
        signal.alarm(0)

    # Return result as a dataclass object
    Result = EquivalenceCheckResult(
        # Circuit information
        qubit_num=qubit_num,
        gate_num=l1,
        gate_num2=l2,
        # Method and strategy
        method=method,
        strategy=strategy,
        # Result
        equivalent=equivalent,
        verification_time=Time,
        pathsum_time=pathsum_time,
        final_pathsum=pathsum_circuit,
        progress=progress,
        Statistics=pathsum_circuit._stats,
        # If method runs WMC, then to_DIMACS_time and tool_time are not None
        to_DIMACS_time=to_DIMACS_time,
        tool_name=tool_name,
        tool_time=tool_time,
        wmc_time=wmc_time,
        CNF=CNF,
        expect=expect,
        log_wmc=log_wmc,
    )
    return Result


@dataclass(repr=False)
class EquivalenceCheckResult:
    """
    Dataclass for storing the result of quantum circuit equivalence checking.

    Attributes:
        qubit_num (int): Number of qubits in the circuit.
        gate_num (int): Number of gates in the first circuit.
        gate_num2 (int): Number of gates in the second circuit.
        method (str): Verification method used.
        strategy (str): Strategy used for gate handling.
        equivalent (str): Result of the equivalence check.
        verification_time (float): Total verification time in seconds.
        pathsum_time (float): Time spent on PathSum computation.
        final_pathsum (PathSum): Final PathSum circuit object.
        Statistics (StatisticsManager): Statistics for the computation.
        progress (str): Progress string (e.g., "N/M").
        to_DIMACS_time (Optional[float]): Time for CNF conversion.
        tool_name (Optional[str]): Name of the WMC tool used (if applicable).
        tool_time (Optional[float]): Time for weighted model counting.
        wmc_time (Optional[float]): Total WMC time.
        CNF (Optional[str]): CNF representation (if generated).
    """

    # Circuit information
    qubit_num: int
    gate_num: int
    gate_num2: int
    # Method and strategy
    method: str
    strategy: str
    # Result
    equivalent: str
    verification_time: float | str
    pathsum_time: float | str
    final_pathsum: PathSum
    Statistics: StatisticsManager
    progress: str = "0/0"
    # If method runs WMC, then to_DIMACS_time and tool_time are not None
    to_DIMACS_time: Optional[float] = None
    tool_name: Optional[str] = None
    tool_time: Optional[float | str] = None
    wmc_time: Optional[float | str] = None
    CNF: Optional[str] = None
    expect: Optional[float] = None
    log_wmc: Optional[float] = None

    @staticmethod
    def _fmt(val: float | str | None) -> str:
        """
        Unified formatting logic:
        1. If the value is a number (float/int) -> format to .3f (without unit)
        2. If the value is None -> return 'N/A'
        3. If the value is something else (e.g., error string)
            -> return the original string
        """
        if val is None:
            return "N/A"
        if isinstance(val, (int, float)):
            return f"{val:.3f}"
        return str(val)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__

        return (
            f"{class_name}(result={self.equivalent}, "
            f"method={self.method}, "
            f"time={self._fmt(self.verification_time)}s)"
        )

    def __str__(self) -> str:
        f = self._fmt
        lines = [
            "Equivalence Check Result",
            "-----------circuit information---------",
            f"  Qubits: {self.qubit_num}",
            f"  Gates:  {self.gate_num}",
            f"  Gates2: {self.gate_num2}",
            "-----------method and strategy---------",
            f"  Method: {self.method}",
            f"  Strategy: {self.strategy}",
            "-----------result----------------------",
            f"  Equivalent: {self.equivalent}",
            "-----------verification time-----------",
            f"  PathSum Time:   {f(self.pathsum_time)} s",
            f"  to_DIMACS Time: {f(self.to_DIMACS_time)} s",
            f"  tool Time:      {f(self.tool_time)} s",
            f"  wmc Time:       {f(self.wmc_time)} s",
            f"  Total Time:     {f(self.verification_time)} s",
            "-----------final pathsum circuit-------",
            f"  {self.final_pathsum}",
            "-----------statistics------------------",
            f"  {self.Statistics}",
            "-----------progress--------------------",
            f"  {self.progress}",
            "-----------CNF------------------------",
            f"  {self.CNF if self.CNF is not None else 'N/A'}",
            "-----------expect---------------------",
            f"  {self.expect if self.expect is not None else 'N/A'}",
            "-----------log_wmc--------------------",
            f"  {self.log_wmc if self.log_wmc is not None else 'N/A'}",
            "-----------tool name------------------",
            f"  {self.tool_name if self.tool_name is not None else 'N/A'}",
        ]
        return "\n".join(lines)

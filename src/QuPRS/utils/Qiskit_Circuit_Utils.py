# SPDX-License-Identifier: MIT
#
# Copyright (c) 2025, Wei-Jia Huang
#
# This file is licensed under the MIT License.
#
# ---
#
# This file contains functions (`random_circuit`, `random_clifford_T_circuit`)
# that are derived from the Qiskit library. The original Qiskit code
# is licensed under the Apache License, Version 2.0.
#
# In compliance with the Apache License 2.0, the original copyright notice
# and license text from Qiskit are preserved below. Any modifications
# made by Wei-Jia Huang are licensed under the MIT License.
#
# --- Original Qiskit Notice ---
#
# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utility functions for generating random circuits."""

import random

import numpy as np
from qiskit import QuantumCircuit, qasm2, qasm3, transpile
from qiskit.circuit import CircuitInstruction, library
from qiskit.circuit.library import standard_gates
from qiskit.circuit.parameter import Parameter
from qiskit.circuit.parametervector import ParameterVectorElement
from qiskit.quantum_info.operators.symplectic.clifford_circuits import (
    _BASIS_1Q,
    _BASIS_2Q,
)

from QuPRS.interface.load_qiskit import load_circuit


def pqc_generator(
    qubit_num=1,
    reps=1,
    function_name="TwoLocal",
    basis_gates1=["h", "ry", "rz", "cx"],
    basis_gates2=["rz", "sx", "x", "cx"],
):
    """
    Generate a parameterized quantum circuit based on specified library function.

    Args:
        qubit_num (int): Number of qubits in the circuit.
        reps (int): Number of repetitions of the circuit.
        function_name (str): Name of the circuit library function to use.
        basis_gates1 (list): First set of basis gates for transpilation.
        basis_gates2 (list): Second set of basis gates for transpilation.

    Returns:
        tuple: Original circuit, transpiled circuit, and circuit name string.
    """
    if function_name == "TwoLocal":
        cir = library.TwoLocal(qubit_num, ["ry"], "cx", reps=reps)
    if function_name == "ExcitationPreserving":
        cir = library.ExcitationPreserving(qubit_num, reps=reps)
    if function_name == "RealAmplitudes":
        cir = library.RealAmplitudes(qubit_num, reps=reps)
    if function_name == "EfficientSU2":
        cir = library.EfficientSU2(qubit_num, reps=reps)
    if function_name == "PauliTwoDesign":
        cir = library.PauliTwoDesign(qubit_num, reps=reps)
    # cir = cir.decompose().decompose().decompose()
    cir = transpile(cir, basis_gates=basis_gates1)
    cir2 = transpile(cir, basis_gates=basis_gates2)
    return cir, cir2, "%s_%i_%i" % (function_name, qubit_num, reps)


def random_circuit(
    num_qubits: int,
    num_gates: int,
    gates: str | list[str] = "all",
    parameterized: bool = False,
    measure: bool = False,
    seed: int | np.random.Generator = None,
):
    """
    Generate a pseudo-random quantum circuit.

    Args:
        num_qubits (int): The number of qubits in the circuit.
        num_gates (int): The number of gates in the circuit.
        gates (list[str] or str): The gates to use in the circuit.
            If "all", use all the gates in the standard library.
            If "Clifford", use the gates in the Clifford set.
            If "Clifford+T", use the gates in the Clifford set and the T gate.
        parameterized (bool): Whether to parameterize the gates. Defaults to False.
        measure (bool): Whether to add a measurement at the end of the circuit.
            Defaults to False.
        seed (int or numpy.random.Generator, optional): The seed for the random number
            generator. Defaults to None.

    Returns:
        QuantumCircuit: The generated random circuit.
    """
    instructions = standard_gates.get_standard_gate_name_mapping()

    if gates == "all":
        gates = list(instructions.keys())
        gates.remove("delay")
        if measure is False:
            gates.remove("measure")
    elif gates == "Clifford":
        gates = ["x", "y", "z", "h", "s", "sdg", "sx", "sxdg", "cx", "cy", "cz", "ch"]
    elif gates == "Clifford+T":
        gates = [
            "x",
            "y",
            "z",
            "h",
            "s",
            "sdg",
            "t",
            "tdg",
            "sx",
            "sxdg",
            "cx",
            "cy",
            "cz",
            "ch",
        ]

    if isinstance(seed, np.random.Generator):
        rng = seed
    else:
        rng = np.random.default_rng(seed)

    samples = rng.choice(gates, num_gates)

    circ = (
        QuantumCircuit(num_qubits)
        if measure is False
        else QuantumCircuit(num_qubits, num_qubits)
    )

    param_base = Parameter("ϴ")
    num_params = 0

    for name in samples:
        gate, nqargs = instructions[name], instructions[name].num_qubits

        if (len_param := len(gate.params)) > 0:
            gate = gate.copy()
            if parameterized is True:
                gate.params = [
                    ParameterVectorElement(param_base, num_params + i)
                    for i in range(len_param)
                ]
                num_params += len_param
            else:
                param_list = rng.choice(range(1, 16), 2 * len_param)
                gate.params = [
                    param_list[2 * i] / param_list[2 * i + 1] * np.pi
                    for i in range(len_param)
                ]

        qargs = rng.choice(range(num_qubits), nqargs, replace=False).tolist()
        print(gate, qargs)
        circ.append(gate, qargs, copy=False)

    return circ


def random_clifford_T_circuit(num_qubits, num_gates, gates="all", seed=None):
    """
    Generate a pseudo-random Clifford+T circuit.

    This function generates a circuit by randomly selecting the chosen amount of
    Clifford and T gates from the set of standard gates in
    qiskit.circuit.library.standard_gates.

    Example:
        from qiskit.circuit.random import random_clifford_circuit
        circ = random_clifford_circuit(num_qubits=2, num_gates=6)
        circ.draw(output='mpl')

    Args:
        num_qubits (int): Number of quantum wires.
        num_gates (int): Number of gates in the circuit.
        gates (list[str]): Optional list of Clifford gate names to randomly sample
            from. If "all" (default), use all Clifford gates in the standard
            library.
        seed (int | np.random.Generator): Sets random seed/generator (optional).

    Returns:
        QuantumCircuit: Constructed circuit.
    """

    gates_1q = list(set(_BASIS_1Q.keys()) - {"v", "w", "id", "iden", "sinv"})
    gates_2q = list(_BASIS_2Q.keys())

    if gates == "all":
        if num_qubits == 1:
            gates = gates_1q
        else:
            gates = gates_1q + gates_2q

    # Dictionary mapping gate names to (gate instance, number of qubits)
    instructions = {
        "i": (standard_gates.IGate(), 1),
        "x": (standard_gates.XGate(), 1),
        "y": (standard_gates.YGate(), 1),
        "z": (standard_gates.ZGate(), 1),
        "h": (standard_gates.HGate(), 1),
        "s": (standard_gates.SGate(), 1),
        "sdg": (standard_gates.SdgGate(), 1),
        "t": (standard_gates.TGate(), 1),
        "tdg": (standard_gates.TdgGate(), 1),
        "sx": (standard_gates.SXGate(), 1),
        "sxdg": (standard_gates.SXdgGate(), 1),
        "cx": (standard_gates.CXGate(), 2),
        "cy": (standard_gates.CYGate(), 2),
        "cz": (standard_gates.CZGate(), 2),
        "swap": (standard_gates.SwapGate(), 2),
        "iswap": (standard_gates.iSwapGate(), 2),
        "ecr": (standard_gates.ECRGate(), 2),
        "dcx": (standard_gates.DCXGate(), 2),
    }

    if isinstance(seed, np.random.Generator):
        rng = seed
    else:
        rng = np.random.default_rng(seed)

    samples = rng.choice(gates, num_gates)

    circ = QuantumCircuit(num_qubits)

    for name in samples:
        gate, nqargs = instructions[name]
        qargs = rng.choice(range(num_qubits), nqargs, replace=False).tolist()
        circ.append(gate, qargs, copy=False)

    return circ


def remove_random_gates(
    input_circuit, num_gates_to_remove, output_format="circuit", output_path=None
):
    """
    Randomly remove a specified number of quantum gates from a quantum circuit.

    Args:
        input_circuit (QuantumCircuit or str): Input circuit or QASM file path.
        num_gates_to_remove (int): Number of gates to remove.
        output_format (str): Output format: "circuit", "qasm2_str", "qasm2_file",
            "qasm3_str", or "qasm3_file".
        output_path (str, optional): Output file path if saving to file.

    Returns:
        QuantumCircuit or str or None: Modified circuit or QASM string, or None if
            saved to file.
    """

    # 1. Handle input
    if isinstance(input_circuit, QuantumCircuit):
        qc = input_circuit.copy()
    elif isinstance(input_circuit, str):
        qc = load_circuit(input_circuit)
    else:
        raise ValueError(
            "Unsupported 'input_circuit' format. Provide a QuantumCircuit object or "
            "QASM file path."
        )

    # 2. Identify removable quantum gates (exclude barriers, measurements, resets, etc.)
    removable_indices = []
    for i, instruction in enumerate(qc.data):
        # Get .operation from CircuitInstruction object, then get its .name
        if instruction.operation.name not in [
            "barrier",
            "measure",
            "reset",
            "delay",
            "snapshot",
            "initialize",
        ]:
            removable_indices.append(i)

    num_available_gates = len(removable_indices)

    if num_gates_to_remove < 0:
        raise ValueError("'num_gates_to_remove' cannot be negative.")
    if num_gates_to_remove > num_available_gates:
        num_gates_to_remove = num_available_gates

    # 3. Randomly select gates to remove
    indices_to_remove = (
        set(random.sample(removable_indices, num_gates_to_remove))
        if num_gates_to_remove
        else set()
    )

    # 4. Build new circuit, skipping removed gates
    if not indices_to_remove:
        modified_qc = qc
    else:
        modified_qc = QuantumCircuit(*qc.qregs, *qc.cregs, name=qc.name)
        if hasattr(qc, "global_phase"):
            modified_qc.global_phase = qc.global_phase
        if hasattr(qc, "calibrations") and qc.calibrations:
            modified_qc.calibrations = qc.calibrations.copy()
        if hasattr(qc, "metadata") and qc.metadata:
            modified_qc.metadata = qc.metadata.copy()
        for i, instruction in enumerate(qc.data):
            if i not in indices_to_remove:
                modified_qc.append(instruction)

    # 5. Output handling
    if output_format == "circuit":
        return modified_qc
    elif output_format == "qasm2_str":
        return qasm2.dumps(modified_qc)
    elif output_format == "qasm2_file":
        if not output_path:
            raise ValueError(
                "Provide 'output_path' when output_format is 'qasm2_file'."
            )
        with open(output_path, "w") as f:
            f.write(qasm2.dumps(modified_qc))
        return None
    elif output_format == "qasm3_str":
        return qasm3.dumps(modified_qc)
    elif output_format == "qasm3_file":
        if not output_path:
            raise ValueError(
                "Provide 'output_path' when output_format is 'qasm3_file'."
            )
        with open(output_path, "w") as f:
            f.write(qasm3.dumps(modified_qc))
        return None
    else:
        raise ValueError(f"Unsupported 'output_format': '{output_format}'.")


def add_random_rotation_gates(
    input_circuit, num_gates_to_add, output_format="circuit", output_path=None
):
    """
    Randomly insert a specified number of single-qubit rotation gates into a quantum
    circuit. Supports multiple output formats.

    Args:
        input_circuit (QuantumCircuit or str): Input circuit or QASM file path.
        num_gates_to_add (int): Number of rotation gates to add.
        output_format (str): Output format: "circuit", "qasm2_str", "qasm2_file",
            "qasm3_str", or "qasm3_file".
        output_path (str, optional): Output file path if saving to file.

    Returns:
        QuantumCircuit or str or None: Modified circuit or QASM string, or None if
            saved to file.
    """
    # 1. Handle input
    if isinstance(input_circuit, QuantumCircuit):
        qc = input_circuit.copy()
    elif isinstance(input_circuit, str):
        qc = load_circuit(input_circuit)
    else:
        raise ValueError("Unsupported 'input_circuit' format.")

    if num_gates_to_add < 0:
        raise ValueError("'num_gates_to_add' cannot be negative.")
    if num_gates_to_add == 0 or qc.num_qubits == 0:
        return qc

    # 2. Insert random rotation gates before measurement
    instructions = list(qc.data)
    num_qubits = qc.num_qubits
    # Find the index of the first measurement gate, or use the end of the circuit
    max_insert_idx = next(
        (i for i, inst in enumerate(instructions) if inst.operation.name == "measure"),
        len(instructions),
    )

    # Add random rotation gates at random positions
    from qiskit.circuit.library import RXGate, RYGate, RZGate

    for _ in range(num_gates_to_add):
        # Select a random rotation gate type (RX, RY, or RZ)
        gate_cls = random.choice([RXGate, RYGate, RZGate])
        # Generate a random angle between 0 and 2π
        angle = random.uniform(0, 2 * np.pi)
        # Select a random qubit
        qubit_idx = random.randrange(num_qubits)
        # Create the new gate instruction
        new_inst = CircuitInstruction(gate_cls(angle), [qc.qubits[qubit_idx]])
        # Insert at a random position before any measurement
        insert_idx = random.randint(0, max_insert_idx)
        instructions.insert(insert_idx, new_inst)
        # Update the maximum insertion index
        max_insert_idx += 1

    # 3. Rebuild the circuit with the modified instructions
    new_qc = QuantumCircuit(*qc.qregs, *qc.cregs, name=qc.name)
    # Preserve the global phase
    new_qc.global_phase = qc.global_phase
    # Copy metadata if it exists
    if qc.metadata:
        new_qc.metadata = qc.metadata.copy()
    # Copy calibrations if they exist
    if qc.calibrations:
        new_qc.calibrations = qc.calibrations.copy()
    # Add all instructions to the new circuit
    for inst in instructions:
        new_qc.append(inst)

    # 4. Handle different output formats
    if output_format == "circuit":
        # Return the circuit object directly
        return new_qc
    elif output_format == "qasm2_str":
        # Return QASM 2.0 as a string
        return qasm2.dumps(new_qc)
    elif output_format == "qasm2_file":
        # Save QASM 2.0 to a file
        if not output_path:
            raise ValueError("'output_path' required for 'qasm2_file'.")
        with open(output_path, "w") as f:
            qasm2.dump(new_qc, f)
        return None
    elif output_format == "qasm3_str":
        # Return QASM 3.0 as a string
        return qasm3.dumps(new_qc)
    elif output_format == "qasm3_file":
        # Save QASM 3.0 to a file
        if not output_path:
            raise ValueError("'output_path' required for 'qasm3_file'.")
        with open(output_path, "w") as f:
            qasm3.dump(new_qc, f)
        return None
    else:
        # Handle unsupported format
        raise ValueError(f"Unsupported output format '{output_format}'.")


def add_random_pauli_gates(
    input_circuit, num_gates_to_add, output_format="circuit", output_path=None
):
    """
    Randomly insert a specified number of single-qubit Pauli gates into a quantum
    circuit. Supports multiple output formats.

    Args:
        input_circuit (QuantumCircuit or str): Input circuit or QASM file path.
        num_gates_to_add (int): Number of Pauli gates to add.
        output_format (str): Output format: "circuit", "qasm2_str", "qasm2_file",
            "qasm3_str", or "qasm3_file".
        output_path (str, optional): Output file path if saving to file.

    Returns:
        QuantumCircuit or str or None: Modified circuit or QASM string, or None if
            saved to file.
    """
    # 1. Handle input
    if isinstance(input_circuit, QuantumCircuit):
        qc = input_circuit.copy()
    elif isinstance(input_circuit, str):
        qc = load_circuit(input_circuit)
    else:
        raise ValueError("Unsupported 'input_circuit' format.")

    if num_gates_to_add < 0:
        raise ValueError("'num_gates_to_add' cannot be negative.")
    if num_gates_to_add == 0 or qc.num_qubits == 0:
        return qc

    # 2. Insert random pauli gates before measurement
    instructions = list(qc.data)
    num_qubits = qc.num_qubits
    # Find the index of the first measurement gate, or use the end of the circuit
    max_insert_idx = next(
        (i for i, inst in enumerate(instructions) if inst.operation.name == "measure"),
        len(instructions),
    )

    # Add random pauli gates at random positions
    from qiskit.circuit.library import XGate, YGate, ZGate

    for _ in range(num_gates_to_add):
        # Select a random pauli gate type (X, Y, or Z)
        gate_cls = random.choice([XGate, YGate, ZGate])
        # Select a random qubit
        qubit_idx = random.randrange(num_qubits)
        # Create the new gate instruction
        new_inst = CircuitInstruction(gate_cls(), [qc.qubits[qubit_idx]])
        # Insert at a random position before any measurement
        insert_idx = random.randint(0, max_insert_idx)
        instructions.insert(insert_idx, new_inst)
        # Update the maximum insertion index
        max_insert_idx += 1

    # 3. Rebuild the circuit with the modified instructions
    new_qc = QuantumCircuit(*qc.qregs, *qc.cregs, name=qc.name)
    # Preserve the global phase
    new_qc.global_phase = qc.global_phase
    # Copy metadata if it exists
    if qc.metadata:
        new_qc.metadata = qc.metadata.copy()
    # Copy calibrations if they exist
    if qc.calibrations:
        new_qc.calibrations = qc.calibrations.copy()
    # Add all instructions to the new circuit
    for inst in instructions:
        new_qc.append(inst)

    # 4. Handle different output formats
    if output_format == "circuit":
        # Return the circuit object directly
        return new_qc
    elif output_format == "qasm2_str":
        # Return QASM 2.0 as a string
        return qasm2.dumps(new_qc)
    elif output_format == "qasm2_file":
        # Save QASM 2.0 to a file
        if not output_path:
            raise ValueError("'output_path' required for 'qasm2_file'.")
        with open(output_path, "w") as f:
            qasm2.dump(new_qc, f)
        return None
    elif output_format == "qasm3_str":
        # Return QASM 3.0 as a string
        return qasm3.dumps(new_qc)
    elif output_format == "qasm3_file":
        # Save QASM 3.0 to a file
        if not output_path:
            raise ValueError("'output_path' required for 'qasm3_file'.")
        with open(output_path, "w") as f:
            qasm3.dump(new_qc, f)
        return None
    else:
        # Handle unsupported format
        raise ValueError(f"Unsupported output format '{output_format}'.")

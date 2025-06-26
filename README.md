[![PyPI version](https://img.shields.io/pypi/v/QuPRS)](https://pypi.org/project/QuPRS/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE.md)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/QuPRS)
[![DOI](https://zenodo.org/badge/1000013052.svg)](https://doi.org/10.5281/zenodo.15705190)
![GitHub last commit](https://img.shields.io/github/last-commit/PhysicsQoo/QuPRS)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/PhysicsQoo/QuPRS)

# QuPRS: Quantum Path-sum Reduction and Solver

`QuPRS`("kyu-parse") is a tool for **Qu**antum Circuit tool integrate **P**ath-sum **R**eduction and **S**olver. 

In quantum computing, verifying whether an optimized or compiled quantum circuit is functionally equivalent to the original circuit is a crucial task. `QuPRS` aims to solve this problem, and its features include:

- **Novel verification method**: Based on pathsum, which is a circuit representation method different from traditional matrix products.
- **Multiple verification strategies**:
  1. **Hybrid mode (RR + WMC)**: Combines the efficiency of reduction rules and the completeness of weighted model counting.
  2. **Reduction rules only (RR)**: Extremely fast, suitable for circuits that can be simplified by local rules.
  3. **WMC only**: A powerful SAT-based method for more complex circuit structures.
- **Seamless integration with Qiskit ecosystem**: Circuits can be directly loaded from Qiskit `QuantumCircuit` objects or QASM files.

## Contents

- [QuPRS: Quantum Path-sum Reduction and Solver](#quprs-quantum-path-sum-reduction-and-solver)
  - [Contents](#contents)
  - [Installation](#installation)
  - [Using QuPRS](#using-quprs)
    - [Create pathsum Circuit](#create-pathsum-circuit)
    - [Import From qasm](#import-from-qasm)
  - [Equivalence Checking](#equivalence-checking)
    - [Circuit Prepare](#circuit-prepare)
    - [Run Equivalence Checking](#run-equivalence-checking)
  - [Cite](#cite)
  - [License Information](#license-information)
  - [Acknowledgements](#acknowledgements)

## Installation

It is recommended to install `QuPRS` in a virtual environment.

1.  Create and activate a Conda virtual environment:
    ```bash
    conda create --name QuPRS python=3.12 # Or your preferred Python version
    conda activate QuPRS
    ```

2.  Install `QuPRS` using pip:
    ```bash
    pip install QuPRS
    ```
    or install `QuPRS` latest commit:
    ```bash
    pip install git+https://github.com/PhysicsQoo/QuPRS.git
    ```

## Using QuPRS

This tool can build quantum circuit using path-sum formulation. 

First, import the necessary components from the `QuPRS` library.

```python
from QuPRS.pathsum import PathSum
```

### Create pathsum Circuit

Create a `pathsum` Circuit
You can create a PathSum.QuantumCircuit object directly:
```python
qubit_num = 2
circuit = PathSum.QuantumCircuit(qubit_num)
circuit = circuit.h(0) # Apply Hadamard gate to qubit 0
circuit = circuit.h(0) # Apply Hadamard gate to qubit 0 again (H*H = I)
# Add more gates as needed
# e.g., circuit = circuit.cx(0, 1)
```
### Import From qasm

`pathsum` supports importing circuits from QASM files or strings.

From a QASM file:

```python
filename = "my_circuit.qasm"
# Ensure my_circuit.qasm exists and contains valid QASM code
# Example my_circuit.qasm:
# OPENQASM 2.0;
# include "qelib1.inc";
# qreg q[2];
# h q[0];
# cx q[0],q[1];

circuit = PathSum.load_from_qasm_file(filename)
```
Or
```python
qasm_str = """
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];
"""
circuit = PathSum.load_from_qasm_str(qasm_str)
```

## Equivalence Checking
`QuPRS` provides tools for checking the equivalence of two quantum circuits, potentially imported from Qiskit or QASM files.

Importing Circuits for Equivalence Checking
You can load circuits from QASM files or define them directly using Qiskit for comparison.


### Circuit Prepare 
- Load from QASM files 
  ```python
  # Assuming circuit1.qasm and circuit2.qasm exist
  from QuPRS.interface.load_qiskit import load_circuit

  circuit1 = load_circuit("circuit1.qasm")
  circuit2 = load_circuit("circuit2.qasm")
  ```
- Direct import from Qiskit `QuantumCircuit` objects:
  ```python
  from qiskit import QuantumCircuit 

  # Define circuit1 using Qiskit
  circuit1 = QuantumCircuit(2)
  circuit1.h(1)
  circuit1.cx(0, 1)
  circuit1.h(1)

  # Define circuit2 using Qiskit
  circuit2 = QuantumCircuit(2)
  circuit2.cz(0, 1)
  ```
### Run Equivalence Checking


- **Hybrid**: Reduction Rules (RR) and Weighted Model Counting (WMC)

  This method combines RR with WMC for equivalence checking.


  ```python
  from QuPRS import check_equivalence

  result = check_equivalence(circuit1, circuit2, method = "hybrid",)
  
  ```

- Using **Reduction Rules (RR)**
   

  ```python
  from QuPRS import check_equivalence

  result = check_equivalence(circuit1, circuit2, method = "reduction_rules",)
  ```



- **WMC** only (without RR)
   
  To perform equivalence checking using only WMC, you need to disable the Reduction Rules switch.

  ```python
  from QuPRS import check_equivalence

  result = check_equivalence(circuit1, circuit2, method = "wmc_only",)
  ```
## Cite
If you use `QuPRS` in your research, please consider citing it.

This code is associated with a forthcoming publication. Please cite this repository for now, and check back for the full paper citation.

[![DOI](https://zenodo.org/badge/1000013052.svg)](https://doi.org/10.5281/zenodo.15705190)
```
```
## License Information

- This project’s original source code is licensed under: [MIT](LICENSE.md)  
- Kenji Hashimoto’s binary component (`QuPRS/utils/gpmc`) is licensed under the MIT License and the file (`QuPRS/utils/Qiskit_Circuit_Utils.py`) contains functions (`random_circuit`, `random_clifford_T_circuit`) that are derived from the Qiskit library. The original Qiskit code is licensed under the Apache 2.0. see: [NOTICE](NOTICE.md)


## Acknowledgements
This project utilizes `gpmc`, a binary component developed by Kenji Hashimoto, for parts of its Weighted Model Counting functionality.







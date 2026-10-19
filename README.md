<!-- Academic & Citation -->
[![Paper](https://img.shields.io/badge/TACAS'26-Paper-orange?style=flat-square)](https://doi.org/10.1007/978-3-032-22749-2_21)
[![Paper DOI](https://img.shields.io/badge/DOI-10.1007%2F978--3--032--22749--2__21-blue?style=flat-square)](https://doi.org/10.1007/978-3-032-22749-2_21)
[![Zenodo DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.15705190-blue.svg?style=flat-square)](https://doi.org/10.5281/zenodo.15705190)

<!-- Release & License -->
[![PyPI version](https://img.shields.io/pypi/v/QuPRS?style=flat-square)](https://pypi.org/project/QuPRS/)
[![Python Version](https://img.shields.io/pypi/pyversions/QuPRS?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/QuPRS/)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE.md)

<!-- Project Status & Code Quality -->
![GitHub last commit](https://img.shields.io/github/last-commit/PhysicsQoo/QuPRS?style=flat-square&logo=github)
[![codecov](https://codecov.io/gh/PhysicsQoo/QuPRS/graph/badge.svg?token=H9XIZF2EZ9)](https://codecov.io/gh/PhysicsQoo/QuPRS)

<!-- Statistics & Community -->
[![PyPI Downloads](https://static.pepy.tech/badge/quprs?style=flat-square)](https://pepy.tech/projects/quprs)
[![Docker Pulls](https://img.shields.io/docker/pulls/physicsqoo/quprs?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/repository/docker/physicsqoo/quprs/)
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
    - [Platform Support](#platform-support)
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
### Platform Support

QuPRS provides pre-built wheels for the following operating systems and architectures:

| OS | Architecture | Status | Note |
| :--- | :--- | :--- | :--- |
| **Linux** | x86_64 | ✅ Supported | Tested on Ubuntu |
| **Linux** | ARM64 (aarch64) | ✅ Supported | Tested on Ubuntu |
| **macOS** | Intel (x86_64) | ✅ Supported | macOS 15+ |
| **macOS** | Apple Silicon (M1/M2/M3) | ✅ Supported | macOS 14+ |
| **Windows** | x86_64 / ARM64 | ⚠️ **WSL2 Only** | Please use [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) |


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
### Solver subprocess reliability and timeout limits

On **Linux** and **macOS**, both backends supervise each invocation of the
selected external weighted model counter (Ganak or GPMC). The solver gets
the **remaining** monotonic time budget; Ganak's `--version` provenance
check has its own shorter cap within that budget. When the budget is
exhausted, the supervisor terminates the solver's POSIX process group,
waits for the directly owned child, and closes captured output. Children
that deliberately detach into a different session/process group are
**not** covered by this guarantee. A terminated grandchild may temporarily
appear as a zombie while its adoptive process reaps it; it is no longer
executing. Native Windows is not supported; use WSL2.

Each subprocess has a **1 MiB per-stream diagnostic output limit**.
Both Python and Rust capture streams in private temporary files; files can
briefly grow past the threshold between checks, but returned diagnostic
buffers are limited to 1 MiB each. Unlike pipe readers, this design does
not wait on inherited pipe descriptors held by detached descendants. Temporary circuit-CNF files are removed
on success and failure by default. Rust can explicitly retain a failed CNF
for diagnosis with `QUPRS_KEEP_FAILED_CNF=1`; such files may contain
sensitive circuit details.

**Important: `timeout` is not currently a strict wall-clock limit for
every part of `check_equivalence()`.** Rust's in-process circuit
construction/Reduction and CNF encoding are not forcibly interrupted
by the solver subprocess supervisor. On POSIX, Python uses `SIGALRM`
for a cooperative request-level limit **only on the main thread**; the
same alarm cannot protect non-main-thread calls, and a Python strategy
`safe_mode` worker timeout does not supervise later work by itself.
A solver invocation is bounded by its own remaining-budget deadline;
long-running in-process work can still exceed the requested overall
time. Do not rely on this API as a hard end-to-end kill switch.

The result status `equivalent` / `equivalent*` is a verified equivalence
classification; `not_equivalent` is an actual negative result;
`unknown` means reduction alone was inconclusive; `Timeout` means a
deadline expired. Solver launch failures, output overflow, nonzero exits,
malformed counts and other solver errors **raise an exception** rather
than returning `not_equivalent` or silently switching to another solver.
QuPRS-managed solver dispatch currently uses one process-wide lock because
the Rust FFI resolves executable overrides via environment variables; this
prioritizes correctness over concurrent WMC throughput. Unrelated threads
that modify these environment variables directly remain outside this guarantee.
The public API requires a positive integer timeout in seconds (zero is invalid).

The Python backend exposes solver-related Python exceptions directly;
the Rust FFI currently wraps external solver failures as a Python
`ValueError` prefixed `Verification Engine Failed`. Use distinct handling
for exceptions, timeouts and mathematical results.

## Cite
If you use `QuPRS` in your research, please cite our paper:

[![Paper](https://img.shields.io/badge/TACAS'26-Paper-orange?style=flat-square)](https://doi.org/10.1007/978-3-032-22749-2_21)
[![Paper DOI](https://img.shields.io/badge/DOI-10.1007%2F978--3--032--22749--2__21-blue?style=flat-square)](https://doi.org/10.1007/978-3-032-22749-2_21)

> **Equivalence Checking of Quantum Circuits via Path-Sum and Weighted Model Counting**  
> Wei-Jia Huang, Christophe Chareton, Yu-Fang Chen, Kai-Min Chung, Min-Hsiu Hsieh, Alfons Laarman, and Jingyi Mei.  
> In *Tools and Algorithms for the Construction and Analysis of Systems (TACAS 2026)*, Lecture Notes in Computer Science, vol. 15668, pp. 419–439. Springer, 2026.  
> DOI: [10.1007/978-3-032-22749-2_21](https://doi.org/10.1007/978-3-032-22749-2_21)

```bibtex
@inproceedings{huang2026equivalence,
  author    = {Huang, Wei-Jia and Chareton, Christophe and Chen, Yu-Fang and Chung, Kai-Min and Hsieh, Min-Hsiu and Laarman, Alfons and Mei, Jingyi},
  title     = {Equivalence Checking of Quantum Circuits via Path-Sum and Weighted Model Counting},
  booktitle = {Tools and Algorithms for the Construction and Analysis of Systems (TACAS 2026)},
  series    = {Lecture Notes in Computer Science},
  pages     = {419--439},
  year      = {2026},
  publisher = {Springer Nature Switzerland},
  doi       = {10.1007/978-3-032-22749-2_21},
  url       = {https://doi.org/10.1007/978-3-032-22749-2_21}
}
```

You can also cite this software repository via Zenodo:

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.15705190-blue.svg)](https://doi.org/10.5281/zenodo.15705190)
## Floating weighted counts

Ganak 2.8.0 uses `--mode=6`; GPMC uses `-mode=1`. Both operate on
floating-point encodings of the path sum. Ganak mode 6 prints rounded complex
counts (nine significant digits in the pinned release). Neither solver is an
exact-arithmetic certificate for the original circuit. Ganak's pinned version,
archive/executable SHA256 and architecture checks still apply.

Count fixtures compare against hand-computed complex sums and the other solver
using relative error `1e-8` and absolute error `1e-12`; individual Rust
solver-integration fixtures use a documented `2e-9` absolute budget. These are
fixture budgets, not universal error bounds under cancellation. Rust serializes
both solver inputs with 17 significant decimal digits in scientific notation
(enough to round-trip binary64 weights). Python evaluates symbolic weights at
113 bits where supported and writes their decimal form without an arbitrary
nine-decimal quantization. Input precision cannot exceed the information in
the original circuit parameters or the numerical type used upstream.

Both Python and Rust WMC backends classify the unrounded, normalized complex
count using `1e-6` magnitude and phase thresholds. Python exposes these as
`config.WMC_MAGNITUDE_TOLERANCE` and `config.WMC_PHASE_TOLERANCE`;
`config.TOLERANCE` remains the independent symbolic-reduction tolerance
(default `1e-10`). Nonzero global phase gives `equivalent*` when the count
magnitude passes the threshold. Python uses a scaled log-magnitude and signed
`atan2`, avoiding overflow, zero-count division, and negative phases wrapping
to nearly `2*pi`.
Results closer to a decision boundary than encoding or printed-count
error should be checked independently; agreement between two solvers alone does
not establish exact equivalence. Nonzero exits, crashes, missing results and
malformed/non-finite counts are failures, without cross-solver fallback.

### Python WMC precision profiling

Use the deterministic microbenchmark to compare 53-bit and 113-bit phase
weight evaluation on the same machine:

```bash
python scripts/profile_wmc_weight_precision.py --samples 96 --repeats 5 --warmups 2 --json-file python_wmc_precision_profile.json
```

Its JSON report includes distinct and repeated phases, normalized timing, and
platform metadata. Cache timings are experimental only, not enabled in
production. The PR benchmark workflow records the report as an artifact.
Absolute timings across different CI runners are not directly comparable.
This profile is observational and does not introduce a new release gate.

## License Information

- The original source code of this project is licensed under the **[MIT License](LICENSE.md)**.

- This project utilizes and depends on several third-party components and libraries, which are governed by their own licenses. For detailed copyright notices and the full license texts of these components, please see the **[NOTICE.md](NOTICE.md)** file.

## Acknowledgements
This project utilizes `gpmc`, a binary component developed by Kenji Hashimoto, for parts of its Weighted Model Counting functionality.







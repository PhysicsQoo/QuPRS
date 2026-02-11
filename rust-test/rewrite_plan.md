# QuPRS Rust Rewrite Plan

This plan outlines the steps to rewrite the core logic of **QuPRS** (Quantum Path-sum Reduction and Solver) from Python to Rust. The goal is to enhance the performance of the **Path-Sum** verification method while maintaining the existing Python API.

## Project Description

**QuPRS** ("kyu-parse") is a tool for **Qu**antum Circuit tool integrate **P**ath-sum **R**eduction and **S**olver. It uses a symbolic path-sum representation to verify quantum circuits. This rewrite focuses on the high-performance implementation of the `pathsum` module in Rust, which will be integrated back into Python via PyO3.

## Goal Description
Replace the Python implementation of `PathSum` with a high-performance Rust backend. The Rust implementation will be exposed to Python via **PyO3**, allowing users to continue using `from QuPRS.pathsum import PathSum` without changes to their high-level code.

## Key Changes

### 1. Foundation: Math & Data Structures
Implement core mathematical structures optimized for quantum simulation.

- **[MODIFY] [rust-test/src/rational.rs] (Rational Number) **
    - Implement arithmetic traits (`Add`, `Sub`, `Mul`, `Div`, `Neg`).
    - Implement `PartialOrd` for sorting terms.
    - Ensure robust GCD reduction.

- **[NEW] [rust-test/src/algebra.rs] (Algebraic Structure) **
    - **Monomial**: `Vec<u32>` (sorted, unique variable IDs).
    - **Polynomial**: `FxHashMap<Monomial, Rational>` (or custom hash map).
    - **BooleanPoly**: `FxHashSet<Monomial>` (ANF representation).
    - Operations: Term-wise addition, multiplication, scalar multiplication.

- **[NEW] [rust-test/src/utils.rs] (Symbolic Conversion)**
    - **Symbolic Conversion**: Logic to convert between boolean forms (ANF) and algebraic integer forms (for phase polynomial).
    - **Reduction**: Coefficient truncation logic (e.g., handling modulo arithmetic for phase gates).

### 2. Core: PathSum Structure
The `PathSum` struct will be the central state, mirroring the Python class.

- **[MODIFY] [rust-test/src/pathsum.rs] (Pure Rust implementation)**
    - **Rust Struct**: `pub struct PathSum { ... }` (Pure Rust implementation).
    - **Composition**: Implement `compose(other: &PathSum)` for circuit concatenation.
    - **Variable Management**: Efficient `fresh_var` generation.

### 3. Reduction Rules (The Optimizer)
Port the pattern matching and reduction logic from Python to Rust.

- **[NEW] [rust-test/src/reduction.rs] (Pattern Matching and Reduction) **
    - **Pattern Matchers**:
        - `match_elim`: Identify linear variables for elimination.
        - `match_hh`: Detect Hadamard-Hadamard cancellation patterns.
        - `match_omega`: Detect phase gadget patterns.
    - **apply_reduction**: Main loop applying rules until convergence.

### 4. Gates Implementation
Implement quantum gate logic directly on the `PathSum` structure.

- **[MODIFY] [rust-test/src/gates.rs] (Quantum Gate Logic) **
    - **Trait**: `QuantumGate` (standard interface).
    - **Implementations**:
        - Single Qubit: `H`, `X`, `Y`, `Z`, `S`, `T`, `P(theta)`, `Rz(theta)`.
        - Two Qubit: `CX`, `CZ`, `Swap`, `CS`, `CCZ`.
    - Logic uses the algebraic engine to update $P$ and $f$.

### 5. Python Integration (PyO3)
Expose the Rust implementation to Python to maintain API compatibility.

- **[MODIFY] [rust-test/Cargo.toml] (PyO3 Integration)**
    - Add `pyo3` with `extension-module` feature.
    - Set `crate-type = ["cdylib"]`.

- **[NEW] [rust-test/src/lib.rs] (Python Wrapper)**
    - **PyPathSum**: A Python wrapper struct `#[pyclass] struct PathSum(inner::PathSum)`.
    - **Methods**: Expose `__init__`, `apply_h`, `apply_cx`, `compose`, etc.
    - **Properties**: Expose `P`, `f`, `pathvars` as strings or Python objects for debugging.

## Verification Plan

### Automated Tests (Rust)
- **Unit Tests**: `cargo test` for algebra, reduction rules, and gate logic.

### Integration Tests (Python)
- Build the wheel using `maturin develop`.
- Create a Python test script `rust-test/tests/test_equivalence.py`.
- **Equivalence Check**:
    1. Construct a random circuit in Qiskit.
    2. Run it through the original Python `QuPRS.pathsum`.
    3. Run it through the new Rust `QuPRS_rust.PathSum`.
    4. Assert that the resulting Phase Polynomials and Boolean Functions are identical.

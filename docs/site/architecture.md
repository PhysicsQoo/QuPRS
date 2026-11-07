# Python and Rust architecture

QuPRS provides two execution interfaces built around Path-sum reduction and weighted model counting.

## Python integration

The Python entry point `QuPRS.check_equivalence()` accepts supported Qiskit `QuantumCircuit` objects and QASM inputs. The `backend` argument selects either the Python implementation or the Rust implementation exposed through PyO3.

With `backend="rust"` and `safe_mode=False` (the default), Python calls the Rust extension in-process. With `backend="rust"` and `safe_mode=True`, Python instead supervises an isolated worker that loads the same PyO3 extension. Isolation bounds worker communication and enforces a worker deadline, but parent-side Qiskit serialization is not forcibly preemptible. Memory enforcement depends on operating-system support.

For `backend="python"`, `safe_mode=True` uses the Python strategy's isolation mechanism; it does not run the standalone Rust CLI.

## Native Rust

The `pathsum` crate exposes a typed verification engine and public types for native callers. Its API is documented in the [Rust crate reference](reference.md). The separate Rust CLI provides command-line input and process execution.

## Verification paths

- **Reduction rules:** try to establish a verdict by simplifying Path-sum expressions.
- **Weighted model counting:** use an explicitly selected solver to classify a weighted count.
- **Hybrid:** pass the residual Path-sum to WMC if reduction is inconclusive.

GPMC and Ganak are independent solver choices; solver failures do not silently imply equivalence or inequivalence. WMC numerical verdicts must be interpreted separately from exact source semantics and certified accuracy.

See the [Python API](python-api.md) for parameters and return types, and [Verification](verification.md) for result classifications.

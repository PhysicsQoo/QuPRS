# Same emitted weighted-CNF solver conformance

The standalone source-scoped workflow builds existing native Rust and Python
implementations and invokes each selected GPMC and Ganak solver *twice* over
the identical small Rust WmcManager-emitted CNF: once from Rust, once through
the Python run_wmc adapter. Three nonempty one-qubit QASM fixtures (HH, X,
T) give six solver/fixture combinations. Source QASM, solver-specific CNF,
raw stdout and independent exact printed-decimal rational references are
included in the provenance artifact. Solver binary SHA256 and argv mode
are recorded for each Python invocation and pinned to the same binary
environment variables used by Rust.

Conformance is only an observation about these native solver invocations
over identical already-encoded CNFs. It cannot establish that Python and
Rust *source-QASM-to-CNF* encoders are semantically identical, that the
solver's rounded count is exact, or that the original quantum circuit
verdict is formally certified. Existing near-identity research remains
independent.

Keep incompatible native backends separate; do not introduce solver
fallback, output smoothing, or silent crash-to-skip behavior. The full
conformance milestone additionally needs independent Python-emitted source
CNFs, malformed/signal/timeout/missing-executable typed negative controls,
macOS Intel/ARM platform matrices, and binary version/provenance readback.

## Independent Python-source encoding control

A second source-scoped diagnostic now constructs an unreduced Python PathSum
directly from the same HH/X/T QASM files and emits *its own* Ganak/GPMC
weighted CNFs, rather than reusing Rust-emitted CNF bytes. Selected native
solvers run these Python files independently. The report retains both source
CNF hashes, both selected binary hashes, solver stdout, and the path-variable
normalizer. Each Python result is checked against both an exact-rational
interpretation of the printed decimal weights and an independently computed
Qiskit dense-operator normalized trace. Distinct CNF bytes are allowed:
equivalent weighted encodings need not be byte-identical.

This small diagnostic does **not** establish arbitrary Python/Rust source
encoder equivalence, formal exact gate semantics, or solver rounding
certificates. Numerical comparison thresholds are diagnostic only.

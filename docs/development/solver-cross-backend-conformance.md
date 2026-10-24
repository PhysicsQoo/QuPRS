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

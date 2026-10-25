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

## Bounded source-to-CNF interval bridge

The same conformance workflow now runs an **additional**, research-only bridge
after the Python-source CNFs have been generated and the native observations
recorded. It reuses the existing strict-rational interval reference rather
than introducing another encoder or a new model-counting algorithm.

For each HH/X/T source and GPMC/Ganak pair, the bridge independently checks
the canonical source-QASM fixture, source and Python/Rust CNF SHA256 hashes,
selected solver-executable SHA256, native process result and original
observational conformance status. It refuses inconsistent provenance before
evaluating any certificate. The bridge then checks the original source
grammar against the bounded one-qubit diagonal domain.

Only the **T** fixture belongs to that validated source grammar. For each
solver's *actual Python-emitted* T CNF, the reference verifies the unique
satisfying Boolean extension for each input bit, activation of phase-weight
literals, source-phase rational-pi interval, printed-decimal weights and their
outward interval hull. The strictly subunit upper magnitude bound supports a
**restricted source-model non-equivalence** observation for T versus identity.
This produces **2 supported certificates** (T x 2 independent emitted CNFs)
and **4 explicit unsupported-scope records** (HH and X x 2). An unsupported
record must never become a certified equivalence or inequivalence claim.

Run the combined workflow at its exact source HEAD, or after the existing
conformance runner has produced its evidence:

~~~sh
python -m pytest -q \
  .diagnostics/wmc_interval_reference/test_python_diagonal_source_certificate.py \
  .diagnostics/wmc_interval_reference/test_source_interval_bridge.py
python scripts/run_source_interval_bridge.py --out solver-conformance-evidence
~~~

The resulting source-interval-bridge-summary.json is attached alongside the
original raw CNFs, native stdout, JUnit and source fingerprints. These
certificates are deliberately limited to the independently audited one-qubit
diagonal source model and actual emitted CNF Boolean/weight activation. They
do **not** establish a general QASM compiler correctness theorem, that Rust
and Python emitted CNFs are extensionally equal on arbitrary circuits, or a
rounding bound on GPMC/Ganak numerical execution. No default method,
solver selection, reduction strategy, published verdict or numerical tolerance
is changed. The legacy near-identity strict-positive scientific RED remains
a separate open issue.

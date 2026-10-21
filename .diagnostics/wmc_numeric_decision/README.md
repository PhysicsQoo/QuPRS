# Near-Unity WMC Decision Audit — No Runtime Changes

Study six actual RZ(delta) pairs (0, 1e-6, 1e-4, 1e-3, 0.01, 0.2)
and one exact-global-phase XZXZ example. For a unitary d x d pair,
m=|Tr(U†V)|/d. Exact m=1 means equivalence up to global phase;
near-one alone does not establish equivalence. For a one-qubit
RZ(delta), m=|cos(delta/2)|. At delta=0.001 this is 0.999999875
and the circuits are not strictly equivalent.

An independent Qiskit 2x2 operator oracle and 100-decimal-digit
mpmath analytic traces anchor the physics. QuPRS Python/Rust WMC-only
methods each select GPMC and Ganak independently, never substituting
one solver for the other. Python solver instrumentation captures actual
selected executable hash, command, CNF digest, raw solver stdout and
parsed complex count. The Rust FFI does not expose raw solver stdout;
the audit correctly labels it unavailable. The Python and Rust CNF
encodings may differ and are not claimed identical.

7 circuit pairs x 2 backends x 2 solvers = 28 fresh bounded child checks.
Full individual JSON, JSONL, original subprocess streams, source/solver
hashes and a SHA256SUMS are retained on failure. A false strict
equivalence claim is SCIENCE_BLOCKED, not success, while artifacts are
still uploaded by a separate always-running step.

Independent analytic mpmath values are not automatically a certified
interval for the WMC solver's actual rounding/printing. Agreement
of both solvers is NOT an equivalence certificate. An unknown interval
must remain Unknown in a future strict policy; a separate explicit
user-selected approximate-equivalence mode would require a reliable
distance bound rather than silently changing strict Equivalent.

This PR never changes WMC magnitude/phase tolerance, solver selection,
scheduler, phase representation, public API or release gates.
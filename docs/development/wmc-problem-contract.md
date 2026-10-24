# Neutral weighted-CNF representation

A weighted counting problem has a declared nonnegative variable count,
an ordered collection of DIMACS clauses, and positive-variable complex
weights. Every negative weight defaults to 1+0i, matching the current
PathSum encodings. Empty clauses mean UNSAT; absence of clauses means
unconstrained SAT. The selected solver adapter owns the external weight
grammar and executable; unsupported capabilities fail explicitly. No
automatic fallback between Ganak and GPMC is permitted.

The Python WmcProblem stores numeric real/imag *objects* without float
conversion. This is required because the Python encoder can produce
SymEngine 113-bit evaluations, whereas Rust's existing phase encoding
currently uses f64; the two must not be advertised as bit-identical.
The Rust borrowed WmcProblem is now used by the existing native DIMACS
writer, retaining its iteration order, formatting and original f64
round-trip policy. Validation is separable from serialization so that
tests cannot accidentally substitute a permissive numeric tolerance.

The Python WmcProblem is an opt-in transport contract at this stage.
The historical Python to_DIMACS conversion has not been changed in this
PR; source-level parity must be tested before routing the live path
through the new representation. Existing typed Python SolverResult
continues to represent a numerical *observation*, not certified exact
equivalence. Rust typed invocation/error provenance and independent
cross-backend conformance are separate follow-up acceptance gates.

This contract does not change Reduction-first Hybrid, WMC classification
thresholds, source-angle semantics, solver binary versions, or public
check_equivalence behavior.

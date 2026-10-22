# Source-angle semantic diagnostics

This directory contains an angle-expression reference and native regression
tests. It does not alter production Path-sum reductions, residual WMC or
numerical tolerances.

The original and transpiled QPEexact8 inputs are close under Qiskit
double-precision numerical evaluation. A separate rigorous complex-ball
witness finds the *literal serialized QASM expressions* to be inequivalent
up to global phase; this does not disprove the intended Qiskit transpilation
parity experiment. Strict literal-QASM equality must not be inferred from
floating-point proximity.

Exact one-qubit decimal-radian addition remains a separate unresolved native
regression, alongside valid symbolic-pi and negative controls. These tests
are not part of default pytest collection. The known failing native studies
run only on explicit request; they are not mandatory PR correctness gates.
Historical exact-source findings remain in earlier commits and artifacts.

## Representational alternatives to evaluate before implementation

- **Dual exact expression domain:** preserve raw decimal radians as
  arbitrary precision \`BigRational\` independent of exact symbolic
  rational multiples of π. Preserve expression structure through gates
  and pathsum; do not convert to finite \`f64/π\` at parse time.
  Need exact composition, cancellation, modular phase, symbol and WMC
  serialization semantics. Avoid i64 cap/overflow and ensure complexity
  remains bounded.
- **Symbolic source-expression provenance:** retain numeric literals and
  parse-tree operations with a proof-preserving canonical form, enabling
  safe equalities only when exactly justified (not "close enough").
  Source syntax and Qiskit f64 evaluation semantics need a defined
  comparison contract.
- **Certified interval/precision escalation:** model interpretation
  error explicitly and only conclude equivalent/non-equivalent when
  certified; otherwise Unknown. This may avoid false definitive
  classification but is **not** itself a GREEN equivalence decision.
  Full operator/trace-based WMC must be independently certified because
  QOO-136 has a genuine near-identity false positive.

The existing \`FreeRational::from_f64\` continued-fraction map is not
additive. Increasing its denominator cap or decreasing epsilon only
shrinks errors; it **cannot** generally make independent rational
approximations additive for arbitrary decimal angles. Tolerance alone
is not a sound substitute for algebraic structure or an explicit
numerical-certification policy.

Near-identity WMC numerical false positives and empty-input edge cases are
separate problems; these diagnostics do not fix or conceal them.

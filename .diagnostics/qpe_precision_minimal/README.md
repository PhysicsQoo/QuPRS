# Small valid-gate QPE decimal-angle precision counterexamples

Scientific data only. No changes to production Rust/Python PathSum, solver
plugins, native scheduling, global-phase threshold or required performance CI.

The source accepted QPEexact8 pair contains decimal-angle literals such as
`-2.5802058126763807`, `1.6198837120072371` and
`1.3499030933393643`. Their native QASM parser converts f64/pi to
`FreeRational` using continued fractions, tolerance `1e-10` and maximum
denominator `1_000_000_000`. Those approximants need not be additive:
two angle literals converted separately can disagree with conversion of
their floating arithmetic sum, by tiny rational coefficients.

This independent pilot first certifies each genuine executable one-qubit
QASM pair through Qiskit dense `Operator` equality **modulo one global
phase**, not the native PathSum implementation:

- `qpe_decimal_double`: RZ(a); RZ(a) vs RZ(2a), with a from original QPE;
- `qpe_decimal_cross`: RZ(a); RZ(b) vs RZ(a+b), both from original QPE;
- `qpe_decimal_mixed`: source angle plus one unrelated decimal control;
- `exact_symbolic_pi`: RZ(pi/8); RZ(pi/8) vs RZ(pi/4);
- `genuine_unequal_rz`: RZ(0.125) vs RZ(0.126), **inequivalent**;
- `genuine_unequal_x`: I vs X, **inequivalent**.

Use both Rust and Python backends, both Naive/Proportional strategies,
all three `reduction_rules`, `hybrid`, `wmc_only` methods and only
the packaged GPMC binary. Total **72 independent child verifications**,
plus all six Qiskit matrix oracles. No synthetic PathSum fixtures. Source
QASM, exact-decimal strings, modeled rational coefficients, per-method
status, native Stage Ledger, final PathSum excerpt, Python result,
compiler/environment provenance and original child JSON all archived
with a SHA256SUMS manifest. Missing or mismatched data fail closed.

**Interpretation is intentionally conditional.** A one-qubit pair that is
Qiskit-equivalent but native `Not Equivalent` demonstrates an actual
semantic counterexample; the predicted rational mismatch alone is not
proof of the internal path that led to the original QPEexact8 x_7
residual. The true inequivalent controls MUST continue to be rejected;
a broad tolerance adjustment is unsafe without separately establishing
an error budget and soundness. `wmc_only` outcomes test the existing
fallback and must never quietly substitute another solver.

The experiment task can be **SCIENCE_BLOCKED** while still correctly
collecting source-pinned data. The original `probe.py` step is strict;
only evidence upload uses `if: always()`. Keep PR Draft until original
raw data and SHA256 have been independently audited.

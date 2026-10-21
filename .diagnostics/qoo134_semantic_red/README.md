# QOO-134: Minimal strict semantic RED → GREEN contract

This Draft research PR **does not implement a production fix**.

Three real QASM test categories:
1. **RED:** QPE-derived 1Q decimal-radian additivity and exact original 8Q
   QPEexact8 (source SHA256 pinned). Independent Qiskit unitary oracle
   certifies each up to one global phase; both native Rust Reduction-only
   and Hybrid under both strategies **must** report equivalent or
   equivalent-up-to-phase without invoking GPMC. Today's code does not.
2. **GREEN controls:** \`RZ(pi/8);RZ(pi/8)=RZ(pi/4)\`, genuinely inequivalent
   \`RZ(0.125)\` vs \`RZ(0.126)\`, and \`I\` vs \`X\`. Verify same real Rust
   Reduction/Hybrid paths. These prevent falsely "repairing" the bug by
   collapsing all small nonzero x-dependent phases.
3. **GREEN representation *reference only*:** a pure Python, exact
   \`AngleExpr = rational_pi * π + rational_decimal_radians\` model
   preserves exact addition of textual decimal QASM literals and exact
   rational multiples of π, and refuses to equate distinct decimal
   rotations. The model has **not** been integrated into PhaseCoeff,
   QASM parsing, or native verification, and does not prove the correct
   numerical acceptance policy.

The RED and GREEN checks run in dedicated, scoped GitHub Actions jobs.
The **strict RED job intentionally fails** until a production correction is
scientifically proven; it does not skip, xfail, use \`continue-on-error\`,
or silently switch to WMC. Each job archives original JUnit, source SHA,
solver-pinned original QPE input hashes and SHA256SUMS despite failure.
The normal dev pytest testpaths remain unchanged and are not polluted
with an already known failing scientific assertion.

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

QOO-136 (near-identity WMC false-positive band) and QOO-137 (empty
Python Proportional input) are separate from this precision-source
regression; neither is fixed or concealed by this research PR.

# Exact input-angle domain: design and migration contract

**Status (v0.13.4 candidate):** the supported Rust QASM2 angle/phase
representation has been integrated into `rational.rs`, `qasm.rs` and the
PathSum/WMC path. Exact decimal-radian input provenance is preserved through
symbolic phase operations. The solver complex-weight boundary and some
Qiskit-object input paths still use finite precision; this is not a
certificate of arbitrary-circuit strict equivalence.

## Historical failure mode (before the exact-decimal integration)

Earlier Rust builds converted QASM source angles through binary64 and
continued-fraction approximation to rational multiples of pi. This could
break algebraic identities even before WMC (see the original
[research regression](https://github.com/PhysicsQoo/QuPRS/pull/74)).
Those source-loss symptoms motivated the current split representation; do
not mistake the historical intentionally-red tests for the status of the
latest `dev` without rerunning the exact-HEAD source oracle. A new exact
source model need not reproduce a previous *approximate* benchmark verdict.

## Proposed expression and its semantics

For an accepted QASM angle `θ` represent
`θ = aπ + b` radians, where `a,b ∈ Q` are **independent,
arbitrary-precision** rational coefficients. Store symbolic π multiples
as `(a,0)`; store *literal decimal radian constants* as `(0,b)`
using an exact base-10 decimal-to-rational parse. Do not silently treat
`3.141592653589793` as symbolic `π`. Distinguish literal source
semantics from incoming already-rounded binary64 Qiskit parameters;
the latter require an explicit, documented conversion policy.

For expression addition/subtraction, operate componentwise. Scalar
integer/rational multiplication preserves exactness. For cancellation,
`(aπ+b)-(aπ+b)=0` exactly. Because π is transcendental,
`aπ+b=0` iff `a=b=0` over rational `a,b`.
Likewise `aπ+b ≡ 0 (mod 2π)` iff `b=0` and
`a∈2Z`. **Never** independently reduce the decimal-radian
coefficient `b` modulo 2π by floating approximation.

Path-sum phase exponents use factors `exp(2π i P)`; angle and phase
objects require a **typed, proof-preserving conversion**.
A rational multiple of π can become a rational phase coefficient;
a rational decimal-radian constant requires its own exact provenance
or a bounded transcendental evaluator, not a rational substitute for
`b/π`. Global-phase identity detection must distinguish an
input-independent phase from qubit-dependent relative phases.

## Conversion and resource safety

* Parse only explicitly supported QASM arithmetic (parentheses, signs,
  multiplication, division, π symbol and decimal/scientific literals);
  retain source provenance and reject malformed/unsupported expressions.
  Never silently ignore an unsupported gate or replace an unknown angle
  by zero in a new certified path.
* Use `num_bigint`/`num_rational` or equivalent checked
  arbitrary-precision types (both already declared in
  `rust/pathsum/Cargo.toml`); track bit-length, term counts and
  expression growth. Exceeding a finite resource cap means
  `unknown`/resource failure, never lossy fallback followed by a
  definitive verdict.
* Audit every `Rational`, `FreeRational`, `Angle`,
  `PhaseCoeff`, gate application, `full_reduce`, substitution,
  modulo phase, hashing/equality and WMC weight conversion boundary.
  Changing only `Angle::from_qasm_str` is insufficient.
* Gate patterns: exact decimal additivity; symbolic `π/8+π/8=π/4`;
  decimal-versus-symbolic π nonidentification; genuinely distinct
  `RZ(0.125)` versus `RZ(0.126)`; identity versus X;
  global phase and 8Q QPE source fixtures.
* Validate both `reduction_rules` and `hybrid`, both Naive and
  Proportional, with **zero solver subprocesses for the native RED
  identities**; measure memory and runtime growth independently.
  Keep WMC numerical soundness as a separate prerequisite.

## Integrated path and remaining validation

1. Supported QASM2 decimal-radian literals and symbolic pi coefficients have
   independent typed storage in Rust; unsupported expressions and gates must
   fail closed rather than synthesize a proof from approximated input.
2. Test cancellation, decimal-versus-pi provenance, CP/U2/global-phase
   matrices, the source-pinned QPE and Graphstate16 cases on the exact RC SHA.
   Distinguish strict source inequivalence from *approximate* transpilation
   equivalence and record a numerical oracle's metric explicitly.
3. Track finite-precision WMC complex-weight conversion and solver output
   separately (see WMC evidence policy). A floating-point numerical
   observation is not an MPFR or source-exact proof.
4. For Qiskit `QuantumCircuit` inputs already represented as binary64,
   document the input precision; no parser can reconstruct original unrounded
   source angles from those values.

This document specifies source semantics and current limitations; scientific
release qualification requires exact-head native and cross-backend evidence.


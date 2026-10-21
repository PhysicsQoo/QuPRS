# Exact input-angle domain: design and migration contract

**Status:** architecture specification only; not integrated into Rust
production. The native scientific regression remains red.

## Verified current failure mode

The QASM parser routes gate angles through
`rust/pathsum/src/qasm.rs::parse_gate_name_and_params` to
`rust/pathsum/src/rational.rs::Angle::from_qasm_str`. The latter
evaluates expressions as binary64, divides by a binary64 approximation
of π, and calls `FreeRational::from_f64`. Continued fractions have a
`10⁻¹⁰` cutoff and maximum denominator `10⁹`. Even later exact-looking
operations use `reduce_and_cap_i128`, which reapproximates with binary64
when the internal budget exceeds `10¹⁴`.

Therefore a decimal-radian identity such as
`RZ(-2.5802058126763807)·RZ(-2.5802058126763807)
 = RZ(-5.1604116253527614)`
can become unequal *after parsing*, prior to any WMC call.
The exact native regression
[PR #74](https://github.com/PhysicsQoo/QuPRS/pull/74)
retains the original 8Q QPE input hashes, 12 required positive
native cases and 12 independent controls. The reference model passes
while native RED is intentionally failing. Simply raising the
continued-fraction denominator or widening global-phase tolerance
cannot preserve algebraic identities in general.

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

## Staged migration

1. Freeze the source-pinned original RED/negative cases and the
   existing isolated expression-model GREEN. Preserve raw evidence.
2. Implement a typed exact angle/phase representation in an **isolated
   Draft PR** with property tests (associativity where defined,
   cancellation, modulo, hash/equality and overflow safeguards).
3. Thread it through QASM, gates, reductions and WMC encoding without
   changing default behavior prematurely; report unsupported terms
   honestly and verify Python/Rust semantic parity.
4. Require the actual native RED gate to become GREEN and all negative,
   symbolic and global-phase controls to remain GREEN at the **same
   exact head SHA**. Only then consider normal review/merge.

No release or default runtime promise is made by this document.

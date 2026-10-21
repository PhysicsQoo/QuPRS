# QOO-134 Rust exact-angle domain prototype

This is a standalone test-only Rust implementation of angle algebra. It does not modify production FreeRational, Angle, PhaseCoeff, QASM parsing, HH/Omega, solver or Scheduler.

Source: rust/pathsum/tests/qoo134_angle_domain.rs
Command: cargo test --locked --manifest-path rust/Cargo.toml -p pathsum --test qoo134_angle_domain -- --nocapture

## Exact representation

An input phase is represented as theta = r + p*pi with r and p exact BigRational coefficients. r represents a decimal literal in radians (not a float value divided by pi), p represents an exact symbolic multiple of pi. This keeps decimal addition/subtraction exact without rounding each token to a continued fraction. The test links to already installed workspace num-bigint, num-rational, num-integer and num-traits.

For RZ rotations up to GLOBAL PHASE, equal angles modulo 2*pi give equivalent RZ operators. Under the declared exact-literal interpretation and pi irrationality, the difference is equivalent exactly if its rational radian coefficient is zero and its rational-pi coefficient is divisible by two. This is a specific RZ-relative-phase theorem, not the general QuPRS pathsum global-phase normalization rule.

The prototype proves exact additivity for three original QPE-derived decimal-angle combinations, half-angle cancellation, symbolic pi/8 additions, modulo-two-pi controls, and genuine inequality of RZ(0.125) versus RZ(0.126) and other small deltas. It tests large denominators beyond the current 1e9 cap and 1024 repeated terms. It rejects invalid grammar and unreasonable input exponents instead of approximating.

**Critical limit**: Qiskit and other QASM producers can evaluate/round floating-point expressions. Exact decimal-text semantics do not imply bitwise float or numerical circuit semantic equivalence. The dedicated RoundedNumericUncertified branch deliberately returns Unknown, even if a textual symbolic identity holds. Also, the parser only handles a restricted set of QASM literals, not arbitrary expressions.

## Next production criteria, not included here

- Decide and document exact QASM expression contract versus rounded-f64 semantics, with an independently certifiable error model.
- Prove exact phase-domain operations for relative/global phase, path-variable polynomials, miter construction, HH/Omega, gate inverses and mixed phase coefficients.
- Verify modular arithmetic: rational-radian coefficients must NOT be reduced modulo 2*pi as if pi were rational; only the symbolic-pi coefficient admits exact 2*pi periodic shifts.
- Control BigRational resource growth, and preserve Linux/macOS, Rust/Python and independent solver semantics.
- Independently solve QOO-136 WMC false positive: an approximately unit-magnitude trace does not certify equivalence. No global magnitude tolerance adjustment or automatic solver substitution is authorized.

The existing strict original native RED contract in PR #74 remains unresolved: 12/12 source-pinned QPEexact8 and minimal-RZ checks fail against native Reduction/Hybrid while 12/12 real-inequivalent/symbolic controls pass. A standalone reference model passing does NOT mean QOO-134 is fixed. Keep both research PRs Draft until appropriate acceptance.

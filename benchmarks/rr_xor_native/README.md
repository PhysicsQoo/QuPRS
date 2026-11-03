# Isolated Rust XOR substitution comparison

This **experimental**, non-legacy benchmark compares production
`PhasePolynomial::substitute_var_with_poly` before and after the bounded
shared-expansion change. It does not measure GPMC, Ganak, Python, or I/O.

- Baseline: `2e3c5f1b160324445240db8ee204988c5d1aed70`.
- Candidate: experiment branch HEAD; both use bit-for-bit identical
  `src/lib.rs` and `benches/rr_xor_native.rs` (SHA256 verified in CI).
- Four fixture types: 12 affected phase terms, 3/5 XOR monomials with
  overlapping Boolean variables, exact half-cycle / exact decimal QASM
  radians / symbolic coefficients / mixed truncation orders.
- Each case hits the optimization precondition `extracted.len() > 1 &&
  sub_poly.len() <= 12`. Both versions run an exact legacy-reference test.
- The measured function is *only* the production substitution. Fixture
  construction and clone are Divan `with_inputs` setup outside the
  CodSpeed Simulation span.
- For unambiguous CodSpeed result identities, CI labels the identical
  benchmark source `rr_xor_native_base` and `rr_xor_native_head` by
  manifest-only bench renaming. Source implementation and fixtures do
  not change. Production paths and any legacy 32 identities remain intact.

The CI job performs the native measurements first. It then executes the
unchanged CodSpeed GPMC Solver-inclusive four-case ABBA WallTime for the
same two exact Rust source SHAs. The latter quantifies total runtime effect
including the external Solver and startup cost. A native-only improvement
does not certify an end-to-end improvement. In particular, upstream CodSpeed
non-Macro WallTime warnings continue to apply.

**Interpretation:** Only compare native CPU Simulation against native CPU
Simulation from the same run and same fixture; do not compare with historical
pytest Simulation or Solver-inclusive WallTime. If the rust-only benchmark
shows benefits absent end-to-end, preserve that distinction and avoid merging
a speculative production speedup.

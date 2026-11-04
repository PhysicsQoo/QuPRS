# QOO-157 — feature-gated Rust d4 native complex-WMC research

This branch is a **non-release** experiment based on the QOO-157 d4
complex-WMC research line. It introduces a compile-time, **default-off**
`experimental-d4` feature in the pathsum Rust package.

## Experimental adapter contract

- Selected only by `tool_name="d4-poc"` when the cargo feature is enabled.
  GPMC and Ganak keep their defaults, arguments, grammar and behavior.
- Uses `counter -i <temp.cnf>`, the same existing Rust `solver_process`
  supervision (deadline, process tree termination, stdout/stderr limits,
  private temp file cleanup) already used for GPMC/Ganak.
- Explicit external binary only: `QUPRS_D4_PATH`,
  `QUPRS_D4_BINARY_SHA256`, pinned
  `QUPRS_D4_UPSTREAM_SHA=be15f91f3e9769e1f5cb175fa27e3eca3a1ea690`,
  and `QUPRS_D4_GMP_PREPARSE_BITS>=256`. These are runtime research
  assertions; they are *not* a trusted proof of internal solver accuracy.
  A SHA mismatch or unsupported precision causes failure, not fallback.
- d4 emits `c s exact arb float` for complex weighted counts and
  `c s exact arb int` for integer/UNSAT counts. The research parser
  keeps decimal tokens as BigRational and records *printed-only*
  half-unit uncertainty; duplicates and SAT/UNSAT contradictions fail closed.
- The feature-enabled native CNF serialization accepts GPMC-compatible
  paired real/imaginary weights and can reuse QuPRS' existing opt-in
  high-precision source-weight strings without silently changing defaults.
- With the feature absent, no `d4-poc` registration is compiled, and
  existing Rust Adapter tests keep their previously supported paths.

## Bounded CI and evidence

`.github/workflows/qoo157-d4-rust-adapter-poc.yml` first tests
`d4_poc_tests`, existing `solver_adapter::tests` with the feature
enabled and disabled, then compiles an ephemeral pinned upstream counter
with the already-studied pre-parse 426-bit initialization. A pinned six-file
SHA256 manifest anchors the original Rust-emitted QuPRS f64/MPFR256 CNFs.
The test invokes the *actual* external binary through Rust `WmcManager`,
and an independent stdlib Fraction oracle checks its decimal transcript.

No custom Rust FFI, no bundled d4 binary, no wheel/release changes, no
new application-level performance assertions. This is a correctness study;
the only approved speed measurements are eventual CodSpeed base/HEAD
solver-inclusive comparisons on identical host and source cohort.

## Stop conditions

No production merge or user-facing `tool_name="d4"` until external
license/redistribution review, upstream-maintained GMP precision fix,
proper precision provenance and solver arithmetic diagnostics, both
Python/Rust EQ/NEQ boundary/unknown parity, and same-SHA CodSpeed evidence
are complete. `precision_certified=false` remains mandatory for this PoC.

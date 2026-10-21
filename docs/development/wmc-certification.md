# Numerical certification boundary for weighted model counting

**Status:** decision design / independent evidence, not a deployed algorithm.
No tolerance, solver-selection, or public status change is introduced here.

## What was actually verified

The solver-specific 28-case experiment
[PR #77](https://github.com/PhysicsQoo/QuPRS/pull/77),
[run #39588515523](https://github.com/PhysicsQoo/QuPRS/actions/runs/39588515523),
saved artifact `wmc-near-unity-solver-audit` (ID 12341103088; original
SHA256 recorded by the workflow). The cases use
`δ∈{0,10⁻⁶,10⁻⁴,10⁻³,10⁻²,0.2}` and one exact global-phase control,
each with Rust/Python × Ganak/GPMC. Source-pinned numerical and operator
references are independent of QuPRS outcomes. The experiment intentionally
exits nonzero upon a semantic discrepancy.

For `δ=10⁻⁶,10⁻⁴,10⁻³`, all four backend/solver combinations classified
non-equivalent `I` and `RZ(δ)` as `equivalent`. For `δ=0.01,0.2`,
all four classified them as `not_equivalent`; `δ=0` and the global-phase
control were classified correctly. Agreement among solvers is not
independent proof because both use floating weighted counts and downstream
magnitude bands.

Source inspection: Python
`src/QuPRS/utils/wmc_solvers.py::classify_weighted_count` accepts a
normalized magnitude with absolute deviation less than
`WMC_MAGNITUDE_TOLERANCE=10⁻⁶`
(`src/QuPRS/config.py`); Rust
`rust/pathsum/src/lib.rs::check_equivalence` likewise checks
`abs(final_amplitude.norm()-1.0)<10⁻⁶`. The threshold intentionally
does not imply an upper bound on the true trace-magnitude defect.

## Impossibility of proof from closeness alone

Set `m=|Tr(U†V)|/d` and `g=1-m≥0`. For every strictly positive
decision band `ε` there are inequivalent one-qubit rotations with
`0<g<ε`. Consequently, `m>1-ε` can at most be a closeness
observation. Decreasing `ε`, changing solver, or increasing decimal
precision without a rigorous result-bound cannot turn this observation
into an exact equivalence certificate.

With rounded counts, errors may come from source-angle conversion, phase
weights, CNF encoding, solver output truncation, floating cancellation,
normalization and status conversion. They require separate provenance
and error accounting. Ganak mode 6 prints rounded complex counts.
Rust currently does not expose the native solver stdout at the Python
boundary; do not manufacture that evidence.

## Proposed proof-preserving decision procedure

1. Preserve the exact input domain and transformation provenance. Use a
   symbolic reduction identity certificate, exact cyclotomic/arithmetic
   proof or equivalent verified method to return `equivalent` or
   `equivalent*`. Determine zero versus nonzero global phase using
   equally sound arithmetic.
2. For an independent **sound negative** decision, construct a
   certified enclosure `m∈[L,U]` for the *true* normalized trace
   magnitude, including encoding, solver and arithmetic error.
   If `U<1`, then global-phase inequivalence is proved. A validated
   basis-vector or matrix-entry witness with certified nonzero residual
   is an alternative.
3. If the enclosure contains 1 and there is no independent positive
   certificate, return `unknown` (reason: numerical uncertainty).
   Never promote an approximate value to `equivalent`.
4. If bounds are inconsistent, nonfinite, unavailable, or fail
   verification, return `unknown` or a scoped computation error.
   Respect existing timeout and resource statuses.
5. Only after specifying a **separate**, explicit approximate-equivalence
   API with user-selected distance and sound error bounds may a
   distance-based acceptance rule be introduced; it must not reuse the
   exact-equivalence labels.

A `float64→MPFR` escalation *without enclosure/certification* is
a useful diagnostic, not a proof. A valid end-to-end interval pipeline
must account for all transformations (including QASM angle parsing),
rounding and cancellation, and use directed rounding or a separately
verified analytic bound. Ganak and GPMC remain independent adapters.

## Minimal acceptance and non-goals

Keep pinned one-qubit oracle tests, exact phase controls, the QPE family,
both backends, both solvers, all user-facing strategies and real invocation
provenance. Check monotonic behavior only as a diagnostic; do not enforce
a fabricated monotonic theorem over inaccurate solver outputs.

The next production change is blocked until a candidate has tests showing:
(a) no false-positive equivalence at small nonzero δ;
(b) true identities stay provably equivalent when the certificate is present;
(c) unsupported/inconclusive cases stay Unknown rather than negative;
(d) no cross-solver fallback or phase-policy regression; and
(e) exact-head cross-platform CI and raw evidence.

This design deliberately makes **no claims** that an exact/interval WMC
certificate already exists in QuPRS.

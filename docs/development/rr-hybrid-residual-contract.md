# Hybrid RR → WMC residual semantics (v0.14.0)

This document records the Python-first numerical policy validated on
`experiment/rr-tolerance-parity`. It is not a new decision mode.

## Residual handoff

1. RR runs with the per-call `rr_tolerance` (default `1e-10` in phase cycles).
   Set `rr_tolerance=0` for strict coefficient matching.
2. If RR decides the result, retain the existing `equivalent`, `equivalent*`,
   or `not_equivalent` semantics, including the independent phase threshold.
3. If Hybrid RR is inconclusive, WMC receives the **current reduced residual
   PathSum**. Neither Python nor Rust replays the source circuit at this point.
4. WMC applies the single projective-distance classifier with independent
   `approximate_distance_tolerance` (default `1e-8`). No hidden magnitude
   classifier, fixed distance guard, new `unknown`, or second solver invocation
   is introduced by the residual handoff.
5. If numerical RR matching modified the residual and Hybrid subsequently
   invokes WMC, the Python public API (including its Rust backend) emits a
   `RuntimeWarning`. The verdict remains a classification of the residual.
   The internal Rust FFI retains the `rr_residual_approximate` provenance bit,
   while the existing public `rr_approximate` describes RR-decided positives.

## Independent near-boundary source oracle

For one-qubit `Rz(a) H H Rz(b)` versus identity, `H²=I`. Thus the exact
source projective distance is `|sin((a+b)/2)|`. If RR removes the tiny
angle `a` before residual WMC, its nominal distance is `|sin(b/2)|`.

At `rr_tolerance=1e-10` cycles and distance tolerance `1e-8`:

| a (rad) | b (rad) | Source analytic + strict/WMC-only | RR-residual Hybrid |
|---:|---:|---|---|
| `0.0000000004` | `0.0000000198` | `not_equivalent` (1.01e-8) | `equivalent` (9.90e-9) |
| `-0.0000000004` | `0.0000000202` | `equivalent` (9.90e-9) | `not_equivalent` (1.01e-8) |

Both Python and Rust reproduced these outcomes with actual GPMC in
[experiment #41263305644](https://github.com/PhysicsQoo/QuPRS/actions/runs/41263305644).
The matching scientific oracle and warnings passed the subsequent
[focused gate #41263683160](https://github.com/PhysicsQoo/QuPRS/actions/runs/41263683160).
This is an **approximate-residual** limitation, not a Solver defect.

For original-source projective-distance classification, use either
`rr_tolerance=0` with Hybrid or `method="wmc_only"`.

## Performance evidence and scope

The Rust exact-source replay was removed to honor the Python-first RR
residual contract. QFT16, Graphstate16 and tolerance parity passed the
focused scientific gates. In solver-inclusive same-host CodSpeed WallTime
[A/B/A run #41264144234](https://github.com/PhysicsQoo/QuPRS/actions/runs/41264144234),
the QFT16/GPMC median was 1.052599 s (dev A1), 1.025623 s
(candidate B), and 1.062180 s (dev A2), each from five rounds.
The candidate's observed reduction in median WallTime relative to the
two baseline medians' average is about 3.0%. CodSpeed warns that WallTime
on a hosted non-Macro runner may not be reliable. These numbers are
**diagnostic**, not a certified fixed Mac mini performance acceptance.

The scientific warnings do not modify Solver or public distance verdicts.
PR #131 remains Draft until controlled performance and complete release
checks support integration.

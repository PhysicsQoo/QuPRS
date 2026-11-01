# Hybrid RR → WMC: source-faithful residual contract (v0.14.0)

## Two-stage RR, one gate stream, one Solver

1. **Single exact-RR gate pass.** In Hybrid, the gate stream is processed
   with strict RR coefficient matching (`rr_tolerance=0`) to obtain a
   source-faithful reduced PathSum, preserving small non-global phases.
2. **Tolerant RR proof probe.** If the caller specifies a positive
   `rr_tolerance` (default `1e-10` phase cycles), clone the strict residual
   and apply the requested RR tolerance to that *temporary proof state*.
   RR success may still report `equivalent` or `equivalent*` with
   `rr_approximate` provenance. `phase_tolerance` remains independent.
3. **WMC fallback.** If the RR proof remains inconclusive, discard the
   temporary probe and pass the strict reduced PathSum directly to WMC.
   There is **no source-gate replay** and only **one Solver invocation**.
   The existing single `approximate_distance_tolerance` (default `1e-8`)
   determines the Solver's projective-distance classification.
4. The numeric WMC classifier is unchanged: no hidden magnitude criterion,
   fixed distance guard or new `unknown` branch. Since WMC receives the
   source-faithful residual, the former source-vs-rounded-residual warning
   is not emitted on this path. Python and Rust use the same policy.

### Source-distance boundary oracle

Source circuits: identity versus `Rz(a) H H Rz(b)`, so
`D_source = |sin((a+b)/2)|`. If an approximate RR removes `a`, the
hypothetical **incorrect** residual distance is `|sin(b/2)|`.

Using `rr_tolerance=1e-10` cycles and
`approximate_distance_tolerance=1e-8`:

| a (rad) | b (rad) | Source D | Hybrid = WMC-only = source oracle |
|---:|---:|---:|---|
| `4e-10` | `1.98e-8` | `1.01e-8` | `not_equivalent` |
| `-4e-10` | `2.02e-8` | `9.90e-9` | `equivalent` |

The strict/tolerant Hybrid verdicts and WMC-only verdicts match the
independent analytic source oracle for both cases on both backends
in [focused experiment #41264999212](https://github.com/PhysicsQoo/QuPRS/actions/runs/41264999212).
Both cases invoke the real GPMC exactly once and retain the strict-RR
residual as the WMC input. Strict source RR and RR-only tolerant
behavior remain independently testable. This scientific contract applies
when the RR stage remains inconclusive and WMC is invoked; a *successful*
approximate RR proof is governed independently by `rr_tolerance` and
is not a source-exact projective-distance certificate.

### Performance acceptance

An earlier approximate-residual experiment showed a diagnostic 3.0%
QFT16/GPMC Solver-inclusive CodSpeed WallTime median improvement over
the two same-host dev baseline groups, but the **current two-stage RR**
design needs its own matched CodSpeed A/B/A result. Hosted-runner WallTime
is exploratory; do not confuse it with the fixed Mac mini formal gate.
Do not use a standalone local walltime to declare a performance gain.

PR #131 remains Draft until full scientific regression and controlled
CodSpeed verification support promotion.

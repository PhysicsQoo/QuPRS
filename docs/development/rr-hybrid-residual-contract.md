# Hybrid RR → WMC: final-residual handoff (v0.14.0)

## Shared reduction, one residual, one solver

1. **Common RR stage.** RR-only and Hybrid apply identical per-gate
   Elim/HH/omega matching and non-global normalization under the same
   per-call `rr_tolerance`. `rr_tolerance=0` disables numerical RR
   approximation. There is no terminal approximate proof probe.
2. **RR result.** When RR decides equivalence, both modes return that
   verdict; Hybrid does not invoke WMC. RR-only can return an inconclusive
   verdict that Hybrid resolves through WMC.
3. **Final residual.** If Hybrid needs WMC, it **directly converts the
   final tolerance-reduced PathSum to CNF/WMC**. It never replays source
   gates, rebuilds a strict-RR shadow, or substitutes a different PathSum.
   The selected GPMC or Ganak solver runs at most once.
4. **Numerical classification.** The single
   `approximate_distance_tolerance` applies to the WMC result on the
   **actual reduced residual**. `phase_tolerance` separately classifies
   global phase. No extra magnitude guard, distance veto or approximation-
   dependent `unknown` branch is introduced. An approximate RR rewrite
   may change the residual's distance from the distance of the original
   circuit: report approximation provenance/a warning rather than silently
   changing the solver's verdict.

### Boundary oracle: source versus reduced residual

For identity versus `Rz(a) H H Rz(b)`, the source distance is
`D_source = |sin((a+b)/2)|`. If tolerant RR discards the small `a`,
the WMC input instead has distance `D_residual = |sin(b/2)|`.
At `rr_tolerance=1e-10` cycles and
`approximate_distance_tolerance=1e-8`:

| a (rad) | b (rad) | source distance / source verdict | reduced distance / Hybrid WMC verdict |
|---:|---:|---|---|
| `4e-10` | `1.98e-8` | `1.01e-8` / `not_equivalent` | `9.90e-9` / `equivalent` |
| `-4e-10` | `2.02e-8` | `9.90e-9` / `equivalent` | `1.01e-8` / `not_equivalent` |

This divergence reflects the user-configured RR approximation, not
a second WMC distance standard. For a distance check on unmodified
source phases, set `rr_tolerance=0` or select `wmc_only`.
RR-only and WMC-only are not required to return the same verdict.

### Acceptance

Verify that Hybrid and RR-only produce the same final RR PathSum under
each tolerance on Python and Rust, including unresolved cases. Validate
source and residual boundary oracles independently, plus solver
invocation counts, approximation warnings, phase semantics, Graphstate16,
and cross-platform correctness. Compare performance with source-pinned
CodSpeed WallTime (including solver subprocesses), Simulation, and Memory.
Keep PR #131 Draft until these gates have passed.

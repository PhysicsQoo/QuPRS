# Hybrid RR → WMC: RR-only parity and source-faithful fallback (v0.14.0)

## One RR algorithm, on-demand faithful WMC residual

1. **Common RR stage.** RR-only and Hybrid process the same gate stream with
   the same per-call `rr_tolerance` at **every** Elim/HH/omega reduction and
   non-global normalization step. There is no strict-first / terminal-tolerant
   proof probe. `rr_tolerance=0` selects strict coefficient matching.
2. **RR decisive.** Both methods use the same RR proof state, phase
   classification, and `rr_approximate` evidence. If RR decides equivalence,
   Hybrid returns immediately, with no WMC solver.
3. **RR inconclusive.** RR-only returns its RR result. Hybrid proceeds to
   WMC. If no approximate rewrite occurred, the already-reduced RR residual
   is source-faithful and can go straight to CNF. If an approximate rewrite
   occurred, Hybrid **lazily reconstructs a strictly reduced residual**
   from the source gate stream, so WMC never mistakes an approximate
   PathSum for the exact source. This replay occurs only when necessary,
   not in the common case and not in a second solver call.
4. **WMC verdict.** The existing single `approximate_distance_tolerance`
   (default `1e-8`) controls source-distance classification. Independent
   `phase_tolerance` controls the global-phase label. No additional
   magnitude, printed-resolution, or RR-bound distance veto is introduced.
   GPMC and Ganak remain independently selected and called at most once
   per verification.

### Boundary oracle

For identity versus `Rz(a) H H Rz(b)`,
`D_source = |sin((a+b)/2)|`. Near the distance threshold, a tolerant
rewrite may remove `a` without making the whole RR proof conclusive.
The WMC fallback must not then classify `|sin(b/2)|` as the source
distance.

With `rr_tolerance=1e-10` cycles and
`approximate_distance_tolerance=1e-8`:

| a (rad) | b (rad) | source distance | Hybrid/WMC-only |
|---:|---:|---:|---|
| `4e-10` | `1.98e-8` | `1.01e-8` | `not_equivalent` |
| `-4e-10` | `2.02e-8` | `9.90e-9` | `equivalent` |

An RR-only verdict can differ from WMC: independent reduction and
distance thresholds are intentionally not conflated.

### Acceptance

Verify exact per-step RR reduction behavior and RR outcomes across
RR-only and Hybrid for the same Python or Rust backend; verify faithful
WMC fallback with real GPMC/Ganak, source-analytic boundary cases,
Graphstate16, and cross-platform gates. Evaluate the conditional replay
with solver-inclusive CodSpeed WallTime, Simulation, and Memory. Do not
promote PR #131 before science and performance gates pass.

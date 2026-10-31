# Per-verification numerical tolerances (v0.14.0 candidate)

QuPRS exposes three independent per-verification numerical thresholds:

| Option | Role | Units | Default |
| --- | --- | --- | --- |
| `rr_tolerance` | Local Path-sum matching and bounded reduced diagonal residual | phase-polynomial cycles | `1e-10` |
| `phase_tolerance` | Label an accepted up-to-global-phase relation `equivalent` or `equivalent*` | radians | `1e-8` |
| `approximate_distance_tolerance` | WMC acceptance by projective Hilbert–Schmidt distance | dimensionless | `1e-8` |

The projective distance is
`D_proj(U,V) = sqrt(1 - |Tr(U†V)|²/4^n)`. An explicit `None`
for the distance threshold selects the documented `1e-8` default;
it does **not** select a magnitude classifier. The public
`wmc_magnitude_tolerance`, `wmc_policy`, mutable Python
`config.TOLERANCE`, `set_tolerance()` and `get_tolerance()` APIs
have been removed.

```python
from QuPRS import check_equivalence

result = check_equivalence(
    circuit1, circuit2, backend="rust", method="hybrid",
    rr_tolerance=1e-10,
    phase_tolerance=1e-8,
    approximate_distance_tolerance=1e-8,
    gpmc_precision_digits=30,
)
```

Python RR tolerances are scoped to a single verification and included
in relevant reduction cache keys. The native Rust verifier also
accepts a custom positive `rr_tolerance`: a fully reduced diagonal
residual may be accepted under a conservative *aggregate* upper bound,
without modifying source angles or the original exact HH/omega rules.
RR-only and Hybrid share the same local RR acceptance criterion;
`approximate_distance_tolerance` applies if WMC runs, and is not an
independent cap on RR success.

A nonzero global phase smaller than `phase_tolerance` can be labeled
`equivalent` after the up-to-global-phase relation is established,
while the original residual phase remains intact. The
`wmc_phase_tolerance` keyword remains a phase-label compatibility
alias. A resource timeout, Solver failure or unsupported input must
not be reported as `not_equivalent` or an invented positive verdict.

## Printed count and scientific evidence

For finite weighted counts, both GPMC and Ganak apply **one**
central printed-count projective-distance threshold. GPMC uses
30 significant digits by default, with an explicit 90-digit option;
Ganak retains mode-6's own numerical/printing precision. Printed
rounding intervals, out-of-unit-magnitude overshoot and unbounded
Solver arithmetic remain independent diagnostics; they do not
change a determinate finite-count distance verdict into `unknown`.
Thus `wmc_printed_verdict` may be `unknown` even when the
operational result is `equivalent`, `equivalent*`, or
`not_equivalent`. No implicit second solve or Solver fallback occurs.

This is a numerical observation, **not** a source-exact
mathematical certificate. At `D_proj=1e-8`, the ideal normalized
trace magnitude defect is about `5e-17`; independent source-pinned
oracles and Solver conformance remain essential. The optional
`gpmc_distance_budget.py` research model is not a production
acceptance policy and cannot override the public numerical verdict.

## Performance acceptance

Formal performance comparisons use CodSpeed. Simulation results on
different CI processors cannot isolate a source regression in
external Solver work. A same-host hosted-VM WallTime experiment
is exploratory, not a bare-metal Macro Runner guarantee.
For main/dev/PR attribution, compare exact pinned source versions,
track `wmc_solver_invoked`, and separate Graphstate16 cases where
the reduction/WMC execution path differs across versions.

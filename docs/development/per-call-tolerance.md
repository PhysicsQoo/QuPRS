# Per-verification numerical tolerances (v0.14.0 candidate)

QuPRS exposes three independent tolerance concepts:

| Option | Mathematical role | Units | Default currently under review |
| --- | --- | --- | --- |
| `rr_tolerance` | Local Path-sum rule coefficient matching (Elim/HH/omega) | phase-polynomial cycles, not circuit distance | `1e-10` |
| `phase_tolerance` | Distinguish zero versus nonzero residual global phase **after** verifying the up-to-phase relation | radians (wrapped modulo `2*pi`) | `1e-8` |
| `approximate_distance_tolerance` | Allow an explicit projective Hilbert–Schmidt distance `D_proj(U,V) <= epsilon` | dimensionless | `None` pending TACAS benchmark decision |

`D_proj(U,V)=sqrt(1-|Tr(U†V)|²/4^n)` is insensitive to global phase.
A numerical acceptance threshold is not an exact equivalence proof.
`None` currently preserves the historical WMC magnitude classifier rather
than automatically certifying strict equality; the default migration requires
separate benchmark acceptance. Solver rounding and printer uncertainty belong
to an internal evidence budget, not to user-defined `rr_tolerance`.

The public Python API accepts:

```python
from QuPRS import check_equivalence
result = check_equivalence(
    circuit1, circuit2, backend="python", method="hybrid",
    rr_tolerance=1e-10, phase_tolerance=1e-8,
    approximate_distance_tolerance=1.4e-4,
)
```

The Python setting is **per call** and is also passed to spawned `safe_mode`
workers. Phase normalization caches use the chosen RR threshold in their key;
no mutable process-global RR setting remains.

The Rust public API, PyO3 and native `VerificationOptions` expose the same
parameters. **Important current limitation:** Rust's reduction rules use exact
rational and symbolic phase identities. Until a safe numerical rule-matching
implementation exists, Rust rejects any nondefault custom `rr_tolerance`
rather than silently ignoring it or replacing an exact proof by a heuristic.
The Rust symbolic reduction still preserves the exact residual phase. Once
the *up-to-global-phase relation* has been proven, however, a nonzero phase
smaller than `phase_tolerance` is intentionally labeled `equivalent`,
consistent with the Python backend. the absence of a WMC stage (`wmc_time=None`) identifies a reduction
verdict. This does not assert an exactly zero global phase: the
residual phase remains in the PathSum. Phases at or beyond the
threshold are labeled `equivalent*`, and unbound symbolic phases
are not silently approximated.

The old Python `config.TOLERANCE`, `set_tolerance()`, and `get_tolerance()`
were removed without compatibility aliases as a deliberate v0.14.0 breaking
change. The historical TACAS'26 v0.9.1 archive remains unchanged.
`wmc_magnitude_tolerance` and `wmc_phase_tolerance` remain compatibility
controls in the candidate; do not confuse them with the new three-way design.

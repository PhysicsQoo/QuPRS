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
    approximate_distance_tolerance=1e-8,  # experimental QCEC-scale setting
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

### Solver execution failures

A user-selected `approximate_distance_tolerance` is a **numerical acceptance
threshold**, not a solver-process failure policy. Both legacy magnitude mode
and distance mode distinguish:

- Timed-out verification or external counter: `Timeout`.
- Solver process nonzero exit, unavailable executable, malformed/nonfinite
  output or unsupported executable: explicit solver-specific exception with
  available diagnostic context; never `not_equivalent` or `unknown`.
- A successfully completed WMC whose *valid* numeric output cannot resolve
  the distance acceptance boundary may still return `unknown`; this is not
  an execution failure. Its prevalence must be measured before choosing the
  shipped default, rather than blindly accepting uncertain evidence.

For a starting point, a `1e-8` normalized-magnitude defect corresponds to
`D_proj=sqrt(2e-8-1e-16)\u22481.4142e-4`. This is a compatibility candidate,
**not yet a validated v0.14.0 default**. The release gate requires real
GPMC/Ganak positive and labeled-negative benchmarks, Python/Rust parity,
near-threshold precision checks, and no unnecessary extra solver invocation.

### Production classification versus research-only precision models

GPMC and Ganak now use the same single-pass printed-complex-count comparator.
The printed decimal count is parsed as exact rational components, and its
squared magnitude is compared against the requested projective-distance
threshold. The existing printed-format rounding interval remains relevant at
the boundary, but no conjectural CNF-size error budget is added to the
production verdict. The original residual phase and phase_tolerance remain
separate.

The experimental gpmc_distance_budget.py is research-only and no longer
called by the public verifier. Its CNF-size operation-error formula was
never a formally proven GPMC solver bound. These results are numerical
observations, not certificates of source-exact equivalence or solver
arithmetic accuracy.

### Target release resolution and performance acceptance

QCEC currently defaults to non-approximate equivalence checking. Its explicitly
enabled projective Hilbert--Schmidt approximate checker has a documented
distance threshold of `1e-8`; its regular DD trace threshold is a different
criterion. The **QuPRS v0.14.0 resolution goal** is a default projective
distance at most `1e-8`, while retaining the original three public result
labels and resource/error handling. This goal is NOT yet verified across
every GPMC/Ganak and Python/Rust combination.

At `eps_D=1e-8`, the normalized trace-magnitude defect is about `5e-17`.
Successful classification may require more than binary64 input weights and
the solver's native short printed decimal count. GPMC's optional MPFR path,
Rust weight conversion, and Ganak output precision need real solver-specific
acceptance evidence. Do not claim this epsilon is reliable merely by setting
the API default or by allowing solver failures to return equivalence.

Negative controls include `I` vs `Rz(0.00010)`, `Rz(0.00020)`, and
`Rz(2.5e-8)`: their projective distances are *strictly greater* than
`1e-8` and must not be accepted as `equivalent` in WMC-only mode.
Positive controls include true identities, the source-pinned Graphstate16
pair (known bounded approximate distance), and representative original
paper families. Compare Python/Rust and Ganak/GPMC. Any remaining
`unknown` due to print precision must be documented, not hidden.

Performance acceptance is separate. CodSpeed Simulation across different
CI CPUs is not a same-hardware causal regression test. Verify the whole
suite and representative Python QAOA7/QFT16/VQE4/Grover4 with matched-runner
A/B walltime and checks that default Hybrid does not perform a second WMC
solve. Optimization must preserve all RR, phase, and cache correctness tests.

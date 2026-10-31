# WMC projective-distance tolerance (v0.14.0)

QuPRS exposes **one** WMC numerical acceptance metric in its Python,
PyO3 and native Rust verification APIs:

\[
D_{\mathrm{proj}}(U,V)
 = \sqrt{1 - |\operatorname{Tr}(U^\dagger V)|^2/4^n}.
\]

The default is `approximate_distance_tolerance=1e-8`; `None`
also selects this default. An explicit finite number in (0, 1) changes
the threshold for one verification. The old
`wmc_magnitude_tolerance` parameter and normalized-magnitude
classifier have been removed rather than retained as a conflicting policy.

```python
from QuPRS import check_equivalence

result = check_equivalence(
    original, optimized,
    method="hybrid", backend="rust", tool_name="gpmc",
    approximate_distance_tolerance=1e-8,  # public default
    phase_tolerance=1e-8,                 # independent global-phase labeling
    rr_tolerance=1e-10,                   # independent Python RR matching
)
print(result.equivalent, result.approximate_distance_tolerance)
```

## Meaning and numerical transport

The source-angle representation is preserved where supported; in the
native GPMC distance path, 192-bit MPFR evaluates complex source-phase
weights and serializes 48 significant decimal digits. GPMC reads these
weights without a solver-source patch. Python can emit supported
SymEngine 113-bit weights without an intermediate binary64 conversion.

For a reported normalized trace magnitude `m`, the stable magnitude
defect corresponding to projective `epsilon` is

\[
1 - \sqrt{1 - \epsilon^2}
  = \frac{\epsilon^2}{1 + \sqrt{1 - \epsilon^2}}.
\]

At `epsilon=1e-8`, the defect is approximately `5e-17`,
not `1e-8`. Binary64 normalized magnitudes cannot reliably resolve
that threshold, which is why the API uses the originally **printed**
complex WMC count and rational interval comparisons, rather than a
binary64 normalized `m` or a fixed empirical guard.

GPMC uses 30 significant decimal working/output digits by default,
with an explicit 90-digit option, in **one** solver invocation.
Ganak retains mode-6 output precision. For finite counts, **both**
Solvers classify the central printed count against the same projective-
distance threshold. Printed rounding intervals and normalized magnitude
overshoots remain **diagnostics**: an independently inconclusive printed
interval does not override a determinate operational distance verdict.
Malformed/nonfinite counts and actual solver failures remain errors.

**Ganak warning:** the parser extracts the rounding half-units for
the actual printed real and imaginary count. It computes the span
of possible squared magnitudes and normalizes by the trace square,
`2**normalization_twice_log2`. Its square root is the observed
projective-distance *printing granularity*. If this exceeds the
requested `approximate_distance_tolerance`, Python emits
`RuntimeWarning`, Rust CLI emits a warning on **stderr** (also in
`--quiet` mode), and result metadata records
`wmc_print_resolution_distance` with
`wmc_precision_reason="ganak_point_estimate_resolution_limited"`.
The printed rounding interval can still report `wmc_printed_verdict=
"unknown"` even when the operational numeric verdict is
`equivalent` or `not_equivalent`. This deliberately distinguishes
the center-point estimate from the unresolved output precision.
No fixed `1e-4` threshold or extra solver execution is used. The
warning is **not** a bound on Ganak's internal arithmetic error.

## Exact unweighted CNF cases

A structurally unweighted CNF whose every clause is tautological has
**exactly** `2**variables` satisfying assignments, regardless of how many
digits an external solver can print. QuPRS verifies this against the
expected trace normalization exponent and directly returns `equivalent`
when they match. This is a restricted, exact WMC counting proof, not an
RR fallback, approximate magnitude threshold, general SAT simplifier or
unchecked identity assumption. It also applies when `method="wmc_only"`.

For example, comparing a one-qubit identity against itself is a
definitive `equivalent` for Python, PyO3/native Rust, GPMC and Ganak.
The exact counting shortcut records
`wmc_precision_reason="analytic_unweighted_tautology"`,
`wmc_solver_invoked=False`, and no printed solver verdict/time.
CNFs with nontrivial weighted phases, any nontautological clause, or a
normalization mismatch **must** continue through the requested solver
and normal finite-precision classification. Identity versus X or Z
must never be classified positive by this shortcut.

## Separate knobs and no solver retry

- `phase_tolerance` / `wmc_phase_tolerance`: labels a proven
  up-to-global-phase relation as `equivalent` or `equivalent*`.
- `rr_tolerance`: per-verification RR coefficient tolerance in
  Python and native Rust. Native RR-only also uses a conservative
  aggregate bound for nonzero diagonal residual phase in cycles;
  it does not enforce a separate exact-nonzero rejection rule.
  Hybrid applies that same RR criterion, without consulting WMC's
  projective-distance tolerance during the RR stage. Neither mode
  rewrites the original source phase.
- `approximate_distance_tolerance`: numerical projective-distance
  acceptance, now the sole WMC metric.

Hybrid retains reduction-first operation and calls WMC only if RR is
inconclusive. An approximate RR success satisfies the configured RR
acceptance criterion, **not** an independent guarantee of
`approximate_distance_tolerance`. This avoids treating the two tolerances
as interchangeable. There is no second solver invocation for higher
precision, no implicit solver fallback, and no modification of
Ganak/GPMC source.

The classifier's printed-output interval is a **conditional numerical
observation**, not a certified bound on solver arithmetic, CNF
preprocessing, input conversion, or the symbolic reduction engine.
A definitive WMC numerical verdict must not be advertised as an
unconditional source-exact equivalence certificate. A stricter threshold
may increase uncertainty in the **printed-output evidence**. For
Ganak, a midpoint-based operational verdict remains explicitly
uncertified when that evidence is unresolved, and users receive the
dynamic resolution warning. Release acceptance must include
source-pinned physical oracles and CodSpeed regression checks
on both native and Python execution paths.

## Breaking API migration

Replace historical magnitude-threshold calls with a *physical*
projective-distance target. There is no general equality mapping from
the old tolerance to the new metric for all numerical/error states.
For an ideal normalized trace value and a chosen defect `t`, the
algebraic distance threshold is `sqrt(2*t - t*t)`. Treat this as a
metric conversion, **not** as an error guarantee.

The legacy public keyword `wmc_magnitude_tolerance` raises
`TypeError` in Python/PyO3; typed native Rust options no longer
contain that field. Existing callers must choose a distance threshold
or use the new default. The old `wmc_policy` API is also absent.

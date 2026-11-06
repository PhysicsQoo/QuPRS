# Weighted model counting and solver contracts

## From a residual Path-sum to weighted counting

When reduction cannot complete a comparison, QuPRS can encode the remaining symbolic expression into a weighted Boolean formula. A generic weighted model count is

$$
\operatorname{WMC}(F)=
\sum_{\sigma\models F}\;\prod_{\ell\in\sigma}w(\ell),
$$

where \(F\) is a Boolean formula, \(\sigma\) ranges over satisfying assignments, and the literal weights \(w\) may be complex. The circuit-specific encoding and trace normalization determine how the count contributes to the comparison; the generic formula alone is not a full circuit verification algorithm.

The default numerical equivalence metric is the **projective Hilbert–Schmidt distance**:

$$
D_{\mathrm{proj}}(U,V)=
\sqrt{1-\frac{|\operatorname{Tr}(U^\dagger V)|^2}{4^n}},
$$

for two unitary operators on `n` qubits. It is unchanged by a global phase. The default `approximate_distance_tolerance=1e-8` applies to this distance, **not** to a raw trace-magnitude defect or an angle in radians.

## Supported external solvers

| User selection | Weight format | Numerical characteristics |
| --- | --- | --- |
| `tool_name="gpmc"` | Paired complex real/imaginary weights | Default 30 decimal working/output digits; 90 may be explicitly requested using `gpmc_precision_digits=90` |
| `tool_name="ganak"` | Signed complex weights | Native printed precision; may be too coarse for some tight distance thresholds |

Solver selection is explicit, and unsupported choices, missing executables, malformed or nonfinite results, and failed processes must **not** silently fall back to a different solver. The exact invocation and count parser depend on the backend.

The phase classification threshold `phase_tolerance` (or `wmc_phase_tolerance`) is in radians, while `rr_tolerance` governs reduction coefficient matching. The **three user-facing tolerances**—reduction matching, global-phase classification, and projective-distance acceptance—serve different purposes and are independently configurable. `gpmc_precision_digits` is a separate numerical solver setting; there is no supported process-global mutable WMC policy.

## Understanding the returned evidence

The following Python result fields have distinct meanings:

| Field | Interpretation |
| --- | --- |
| `equivalent` | Operational status: `equivalent`, `equivalent*`, `not_equivalent`, `unknown`, `Timeout`, `MemoryOut` |
| `wmc_time` | WMC stage timing, if that stage was reached |
| `wmc_solver_invoked` | Whether an external weighted counter actually ran |
| `wmc_numerical_verdict` | Solver-derived numerical classification where available |
| `wmc_print_resolution_distance` | Printed-output granularity diagnostic, not an internal solver-error certificate |
| `rr_approximate` | Whether an accepted reduction was tolerance-dependent where reported |

A weighted formula admitting an exact unweighted tautology shortcut can be counted analytically without launching a solver. For that reason, `wmc_time` alone is not proof that GPMC or Ganak ran.

**Caution:** finite-precision complex counts do not generally certify source-exact operator equality. A near-threshold observation may require an independent unitary oracle, algebraic proof, or tighter evidence. An execution error, `unknown` or resource limit is not a proof of inequality.

See [executable examples](examples.md), [Path-sum rules](path-sum.md), [Python API](python-api.md), and the published [numerical evidence description](https://github.com/PhysicsQoo/QuPRS/blob/dev/docs/development/wmc-evidence-policy.md).

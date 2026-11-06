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

Writing \(d=2^n\) and \(m=|\operatorname{Tr}(U^\dagger V)|/d\), exact global-phase equivalence requires \(m=1\). The two commonly used distances are distinct:

$$
\begin{aligned}
D_{\mathrm{proj}}^2 &= 1-m^2,\\
D_{\mathrm{gp}}^2 &= 2-2m,\\
D_{\mathrm{proj}}^2 &= D_{\mathrm{gp}}^2-\frac{D_{\mathrm{gp}}^4}{4}.
\end{aligned}
$$

For the single-qubit Qiskit rotation \(R_z(\theta)\), the analytic control is

$$
D_{\mathrm{proj}}(I,R_z(\theta))=
|\sin(\theta/2)|.
$$

These are mathematical properties of unitary matrices, **not** certificates of external solver arithmetic. The actual WMC stage uses a finite-precision complex count; source semantics, numeric verdicts, and printed-count resolution remain separate.

## Supported external solvers

| User selection | Weight format | Numerical characteristics |
| --- | --- | --- |
| `tool_name="gpmc"` | Paired complex real/imaginary weights | Default 30 decimal working/output digits; 90 may be explicitly requested using `gpmc_precision_digits=90` |
| `tool_name="ganak"` | Signed complex weights | Native printed precision; may be too coarse for some tight distance thresholds |

Solver selection is explicit, and unsupported choices, missing executables, malformed or nonfinite results, and failed processes must **not** silently fall back to a different solver. The exact invocation and count parser depend on the backend.

The phase classification threshold `phase_tolerance` (or `wmc_phase_tolerance`) is in radians, while `rr_tolerance` governs reduction coefficient matching. The **three user-facing tolerances**—reduction matching, global-phase classification, and projective-distance acceptance—serve different purposes and are independently configurable. `gpmc_precision_digits` is a separate numerical solver setting; there is no supported process-global mutable WMC policy.

## Implemented adapter boundary versus future extensions

The current Python solver-neutral transport lives in
[`utils/solver_adapter.py`](https://github.com/PhysicsQoo/QuPRS/blob/dev/src/QuPRS/utils/solver_adapter.py),
with the weighted-CNF representation in
[`utils/wmc_problem.py`](https://github.com/PhysicsQoo/QuPRS/blob/dev/src/QuPRS/utils/wmc_problem.py).
These are **implementation-level extension contracts**, not an unconditional
promise of long-term public API stability. The supported user-facing
`tool_name` choices remain `"gpmc"` and `"ganak"`.

| Component / capability | Currently implemented | Not guaranteed by this contract |
| --- | --- | --- |
| `SolverAdapter`, `get_solver_adapter` | Explicit solver ID, fixed argument tuple, resource resolver, output parsing, and selected-process execution | Automatic solver discovery, transparent fallback, or arbitrary third-party solver support across Rust/Python |
| `SolverCapabilities` | `weight_format`, `complex_weights`, `exact_count_certificate` fields; both built-in solvers currently advertise `exact_count_certificate=False` | A certified exact count from a solver that prints decimals |
| `SolverResult` | `solver_id`, numerical `count`, invoked `arguments`, `returncode`, and `elapsed_seconds` | Cross-platform binary SHA, solver version, or source provenance in the result dataclass |
| `WmcProblem` / `WmcWeight` | Bounded CNF clause/variable validation and source-preserving real/imaginary weight objects | Arbitrary negative-literal weights: the current serializer gives the negative literal weight `1+0i` |
| `registered_solver_adapter` | Scoped Python-only registration with duplicate/built-in override rejection, useful for isolated extension tests | A supported production plugin discovery or native Rust solver registration protocol |
| Error and resource handling | Unknown solver: `ValueError`; unsupported complex weights: `ValueError`; nonzero exit: `SolverExecutionError`; malformed/conflicting counts: `SolverResultError`; deadline: `SolverTimeout` | Treating failures, resource limits or inconclusive counts as `not_equivalent` |

The Python adapter executes the **selected** solver with an explicit
remaining time budget under its process lock. Ganak performs additional
binary diagnostics. `GpmcAdapter` uses paired real/imaginary weight
components; `GanakAdapter` uses signed complex-`i` syntax.
Their differing printed precision is not resolved by a common
`SolverCapabilities` flag: see the [numerical evidence policy](https://github.com/PhysicsQoo/QuPRS/blob/dev/docs/development/wmc-evidence-policy.md).

The separate Rust solver manager and Python `check_equivalence` route have
their own established integration boundaries. A Python-registered mock third
adapter is a **test of extensibility**, not proof that a new solver has the
same portable Rust CLI, error, timeout, packaging, and numerical guarantees
as GPMC/Ganak. A new official backend requires independent cross-platform
and complex-count conformance before public support is advertised.

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

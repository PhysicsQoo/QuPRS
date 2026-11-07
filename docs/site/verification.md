# Verification methods and results

The public Python `QuPRS.check_equivalence()` interface supports three methods.

| Method | What runs | When it can be inconclusive |
| --- | --- | --- |
| `hybrid` | Path-sum reduction, then WMC on the final residual when reduction is inconclusive | A solver failure or resource limit is not a negative proof |
| `reduction_rules` | Reduction rules without an external WMC solver | An irreducible or unsupported symbolic residual may yield `unknown` |
| `wmc_only` | WMC path without reduction-rule matching | Finite solver arithmetic and unsupported inputs can limit reliability |

Use `tool_name="gpmc"` or `tool_name="ganak"` for an explicit WMC backend. No implicit fallback changes the chosen solver.

## Result meanings

| Status | Interpretation |
| --- | --- |
| `equivalent` | An accepted exact or tolerance-dependent identity under the selected method |
| `equivalent*` | An accepted result up to global phase, distinct from exact matrix equality |
| `not_equivalent` | A supported symbolic counterexample or numerical WMC rejection |
| `unknown` | No conclusive answer from the selected path |
| `Timeout` / `MemoryOut` | A resource-limited run, **not** non-equivalence |
| Exception | Invalid input, unsupported operations or failed solver/parse, **not** non-equivalence |

Check `wmc_solver_invoked` instead of assuming that a non-null `wmc_time` means an external solver ran. Numerical classifications may contain separately reported precision diagnostics; their presence does not amount to certified solver error bounds.

## Independent tolerances

- `rr_tolerance` defaults to `1e-10` and influences reduction coefficient matching.
- `phase_tolerance` (alias `wmc_phase_tolerance`) distinguishes a negligible global phase, in **radians**.
- `approximate_distance_tolerance` defaults to `1e-8` and applies to the projective Hilbert–Schmidt distance.
- `gpmc_precision_digits` is 30 by default; an explicit value of 90 is supported for GPMC, not Ganak.

Do not confuse a projective distance threshold with an angular tolerance or solver decimal output precision.

## Input and execution boundaries

QuPRS verifies **unitary** circuit behavior, not measurement outcomes, reset channels or open-system semantics. QASM versions and gate sets have documented, backend-dependent limits.

`backend="python"` selects the Python implementation; `backend="rust"` uses PyO3. With the Rust backend, `safe_mode=True` supervises a child process that invokes the same Rust extension. It is not a call to the standalone CLI, and parent-side serialization remains outside the worker's hard deadline.

See the [executable examples](examples.md), [Path-sum theory](path-sum.md), [WMC contract](weighted-model-counting.md), [architecture](architecture.md), and [Python API](python-api.md).

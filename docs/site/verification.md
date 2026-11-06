# Verification

QuPRS supports three verification methods through its Python `check_equivalence()` interface.

| Method | Description |
| --- | --- |
| `hybrid` | Apply Path-sum reduction rules, then invoke WMC if reduction is inconclusive. |
| `reduction_rules` | Use reduction rules without calling an external WMC solver. |
| `wmc_only` | Evaluate the WMC path without reduction-rule matching. |

The solver selection is independent of the verification method. GPMC and Ganak are separate WMC backends.

## Interpreting results

- `equivalent`: equivalent according to the selected verification semantics.
- `equivalent*`: equivalent up to global phase.
- `not_equivalent`: classified as non-equivalent.
- `unknown`: the selected method did not establish a verdict.
- `Timeout` or `MemoryOut`: execution could not complete within the corresponding resource constraints.

A solver error, timeout, or unknown result is **not** evidence of non-equivalence. Numerical WMC acceptance should not be interpreted as an unconditional mathematical certificate.

For precise numerical definitions and supported source semantics, see the [equivalence semantics reference](https://github.com/PhysicsQoo/QuPRS/blob/dev/docs/development/equivalence-semantics.md).

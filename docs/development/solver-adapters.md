# Weighted model counting solver adapters

QuPRS supports the explicitly selected external weighted model counters
**GPMC** and **Ganak**, using separate adapters for their input grammars,
process invocation and printed complex-count parsing.

| Solver | Mode | Input weights | Precision |
| --- | --- | --- | --- |
| GPMC | `-mode=1` | Paired real/imaginary values | 30 decimal digits by default; `gpmc_precision_digits=90` is supported |
| Ganak | `--mode=6` | Signed complex-`i` values | Native solver printing precision (approximately nine significant digits) |

Select the solver with `tool_name="gpmc"` or `tool_name="ganak"`
when calling `check_equivalence`. An unknown solver name, missing
executable, failed launch, timeout, nonzero exit, conflicting count,
malformed output or nonfinite count cannot silently produce a valid
equivalence result. A failure never causes an implicit retry with
the other solver.

Python uses `QuPRS.utils.solver_adapter` for typed solver capabilities,
result parsing, and scoped optional adapter registration. Native Rust uses
a separate solver-adapter interface; neither backend automatically routes
through a newly registered Python adapter. These extension mechanisms
do not imply that arbitrary third-party solvers are supported by the
public verification API.

Weighted complex counts are numerical observations, not general
source-exact equivalence certificates. Both public backends apply the
documented projective-distance classifier to finite counts; printed
precision diagnostics remain separate from the operational verdict.
See [WMC numerical tolerance](wmc-numerical-tolerance.md) and
[WMC evidence policy](wmc-evidence-policy.md).

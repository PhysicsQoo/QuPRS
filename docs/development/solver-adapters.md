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

The Python and native Rust backends both honor an explicit
`QUPRS_GPMC_PATH` executable override. With an override, that path is
used as requested; a missing or failing executable is an error, not a
request to retry the packaged GPMC or Ganak. The packaged executable
comes from the GPMC source pinned by the repository submodule Gitlink;
`branch` in `.gitmodules` is a checkout preference, not an immutable
version identifier. An override is not thereby certified as the pinned
binary. For source and artifact attribution, record the actual executable
SHA-256, platform/architecture, selected command arguments and source
commit separately. An upstream/source commit alone does not prove an
installed binary has identical bytes or numerical behavior.

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

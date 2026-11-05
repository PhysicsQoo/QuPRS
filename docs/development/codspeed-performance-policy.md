# CodSpeed performance evidence and interpretation

QuPRS uses official CodSpeed results for algorithmic and solver-inclusive
performance analysis. The canonical routine workflow and measured identities
are defined by [CodSpeed source and instrument contract](codspeed-experiment-architecture.md)
and [benchmark compatibility policy](codspeed-compatibility-policy.md).

**Simulation** measures modeled CPU work and does not include the actual
GPMC/Ganak external process time when subprocess tracking is disabled.
**Solver-inclusive WallTime** measures the full subprocess path. They are
different instruments and must not be subtracted, summed, or called directly
comparable. A green upload is not proof of no performance regression.

For each comparison verify the exact source/fixture SHA, runner CPU cohort,
toolchain, method, backend, strategy, solver, precision, tolerance, stage,
direction, verdict and instrument. Preserve A/A and B/B drift if repeating
measurements. Historical numbers from other runner cohorts are observational
only, even when CodSpeed displays a percentage delta.

A solver-invoked scientific status must be established separately from the
timing measurement. Missing/unknown verdicts, incomplete source provenance,
timeout, instrument mismatch or unverified solver invocation invalidate
an algorithmic performance claim. An absent new measurement is not a zero
regression; evidence reused by source-impact routing keeps its original SHA.

No universal percentage merge veto is certified on shared GitHub-hosted
runners. A strong regression threshold requires controlled and repeated
matched-host evidence, or a separately qualified fixed CodSpeed Macro runner.

## Optional true single-invocation ABBA diagnostic

The opt-in `p5-abba` job in `.github/workflows/codspeed.yml` is requested
by editing a PR description while the following exact marker is present:

`<!-- quprs-codspeed-v3-abba -->`

Remove the marker before later edits to avoid unintended repeats. It is not
part of routine PR validation. The source-pinned benchmark uses Rust/GPMC,
QAOA7 Random_Rotation NEQ, Hybrid and WMC-only, and four alternating
`ABBA/BAAB/BAAB/ABBA` blocks with distinct untimed prewarms. Each measured
position must invoke the solver exactly once and satisfy strict scientific
provenance checks.

Reports retain per-position observations and within-pair drift, but remain
**OBSERVATION_ONLY / NOT_CERTIFIED** without qualified stable hardware and
independent noise calibration. Do not infer a source-caused speedup or
regression from small host-noisy median changes.

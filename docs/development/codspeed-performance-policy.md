# CodSpeed v3 formal performance strategy (QOO-170)

## QOO-106 review closeout (2026-11-04): runner cohorts, provenance and conclusions

This section is the **current interpretation** of performance evidence. The
older research run described below remains genuine, but was superseded by
the second (four-block) opt-in study; do **not** mix their measurements,
rename their identities, or reuse old values as new-run samples.

### Tested evidence, not a performance claim

- **True per-position ABBA:** [CodSpeed 6ae9e347](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6ae9e3477e595669fd0e0644),
  [GitHub Actions 41645323941](https://github.com/PhysicsQoo/QuPRS/actions/runs/41645323941).
  Two QAOA7 Random_Rotation NEQ source-pinned GPMC cases (Rust Hybrid and
  Rust WMC-only, 90 digits, same request tolerances), each with four
  `ABBA/BAAB/BAAB/ABBA` blocks. All 32 single-position official
  CodSpeed WallTime samples had exactly one real GPMC call, a real NEQ
  verdict, correct SHA/source hashes, and four separate **untimed** prewarms.
  The final four-block medians were **Hybrid -0.294%** and **WMC-only -0.564%**;
  maximum within-block base A2/A1 drifts were **7.78%** and **17.58%**,
  respectively. Block effects had mixed signs for **both** methods.
  **Decision: PERFORMANCE_INCONCLUSIVE / NOT_CERTIFIED.** Neither result
  establishes a speedup, regression or release-gate threshold.
- **Historical cross-run mismatch:** [official CodSpeed comparison b197f0a
  vs 3ca0a48](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/compare/6ae9b6bee8d2afdb6648a642..6ae9b8d6f4f68feb946a843e)
  reports 20 affected WallTime measurements across **AMD EPYC 7763 ->
  AMD EPYC 9V74**, and affected Simulation measurements across **AMD EPYC
  9V45 -> AMD EPYC 7763**. A different VM, CPU cache/flags or system
  load can alter both CodSpeed modes; cross-run delta is not a controlled
  algorithmic comparison.
- **Post-v0.14.0 main vs dev:** [official CodSpeed comparison
  6aeaa53..6aeab183](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/compare/6aeaa53f224486181d0f0798..6aeab1831009698cbc8b589f)
  identifies **Intel Xeon Platinum 8573C vs AMD EPYC 7763** and
  **Python 3.12.16 vs 3.12.15**. This is a hardware/toolchain cohort
  mismatch, even when source is largely unchanged. Preserve raw values and
  the comparison URL, but do not publish a speedup or regression number
  as if measured under controlled conditions.

### Evidence admission (never infer absent measurements)

| Evidence | Accepted interpretation | Rejected interpretation |
| --- | --- | --- |
| Exact source/fixture SHA, method, backend, direction, requested precision, Solver-invoked stage and verdict verified; same job/runner but separate grouped rounds | Real **observed** paired WallTime and direction, with CV and source notes | Statistically certified percentage, fixed performance merge/release gate |
| Same pinned science contract and one true CodSpeed round per position, ABBA/BAAB on one host, independent A/A samples | Observational blocked effect; report A/A and B/B drift, sign consistency, limited sample count | Significance or speedup inferred merely from a small median shift |
| Different Actions runs/CPUs, flags, Python/instrument versions, or unresolved load/VM cohort | `CROSS_RUN_ENVIRONMENT_MISMATCH`; preserve raw run IDs and milliseconds | Arithmetic across unrelated runs claimed as algorithm performance delta |
| Different QASM, Solver calls, tolerance/printed digits, backend, RR-termination stage, or unknown/incorrect verdict | `WORKLOAD_NOT_COMPARABLE` or fail science provenance; **no percentage** | Invented baseline, zero/timeout-as-time, or equivalence from Ganak coarse print |
| Exact SHAs/content trees reused from earlier successful tests, but no measurement on current SHA | Prior successful scientific *evidence* may be reused under CI impact rules; identify original measured SHA | Treat carried-forward instrument values as fresh current-SHA measurements |

**Fixed policy:** In-process CodSpeed Simulation does not include real
GPMC/Ganak child work; complete Solver-inclusive WallTime is the appropriate
end-to-end instrument. Do not subtract or combine Simulation and WallTime.
The numerical science verdict and source integrity remain strict fail-closed,
while performance remains `OBSERVATION_ONLY_NO_FIXED_THRESHOLD`.
Only consider promoting a performance gate after fixed/dedicated CodSpeed
Macro Runner (or independently qualified identical CPU cohort), sufficient
repeated A/A controls, matched toolchain/solver/input and budgeted
counterbalanced samples. GitHub-hosted runner reproducibility does **not**
meet that threshold today.

**Cost and duplication:** The 32-position opt-in study costs 32 actual
measured Solver invocations + four untimed prewarms (and two separate
verifier installs). It already ran successfully, and additional hosted
repeats do not fix the observed runner instability. The routine 10-case
paired job and 5+30 Simulation/Native suite remain unchanged, along with
historical records in QOO-170. Do not spawn another ABBA implementation
or another recurring costly job. **QOO-13** owns ongoing runner/baseline
observation; **QOO-106** owns the source-impact and evidence-interpretation
resolution. Version-only PR routing is treated separately from
main/dev release baseline creation, and never weakens correctness or packaging.


For every PR keep all **five Simulation shards** with 32 legacy benchmark identities + 12 newer QASM261 CPU identities, 30 Rust Native/core identities, and **10** source-pinned paired Solver-inclusive WallTime cases including QAOA7 Rust/GPMC WMC-only at 90 printed digits. These remain the authoritative CI coverage for actual stages/verdicts/cost; the existing ten-case and five-shard jobs are not modified by the P5 opt-in experiment.

**Timing is not science correctness.** The 10 routine base/HEAD pairs run within the same GitHub job/runner but are not per-invocation ABBA samples. Different hosted CPUs/VMs or run dates cannot produce certified regression percentages. CodSpeed CPU Simulation excludes actual external Solver child cost. The P5 statistical interpretation stays `NOT_CERTIFIED`, with **no fixed performance threshold** blocking merges. Source QASM, Solver stage, numerical precision, EQ/NEQ and timeout science guards remain strict.

## On-demand true ABBA/BAAB

The only active `p5-abba` job in `.github/workflows/codspeed.yml` is activated **only** when a PR description is edited while including exactly:

`<!-- quprs-codspeed-v3-abba -->`

Remove this marker before later description edits to avoid unintended repeat jobs. Routine PR opens, synchronizes and ordinary edits without the marker never run this opt-in diagnostic.

The superseded three-block/five-round P5 test, reporter, and unit suite
are intentionally removed from the active repository; original research
records remain accessible in Git history.

The opt-in job uses exact SHA-pinned base and HEAD in two independent Python/Rust environments on the same hosted runner, a shared QAOA7 Random_Rotation NEQ QASM pair, Rust/GPMC with RR `1e-10`, distance/phase `1e-8`, and **90 printed GPMC digits**. For **Hybrid and WMC-only**, it runs **ABBA, BAAB, BAAB, ABBA** (4 blocks ×4 positions per method; **32 official single-round CodSpeed WallTime measurements**). Each timed position runs an actual GPMC subprocess once; four additional prewarms (two methods × two revisions) are separately recorded. `pytest-codspeed==5.0.4` `pedantic(rounds=1, iterations=1, warmup_rounds=0)` makes an extra, untimed target call to retrieve a return value; the proven post-timing cache blocks a duplicate Solver execution and fails closed if plugin behavior changes.

The independent reporter rejects wrong SHA/inputs, missing measured URI, multiple rounds or invocations, wrong Solver/NEQ/precision, and incomplete warmup. It reports the paired block ratios and A1/A2 drift with **observational-only** status. Never claim a ~1% speedup or regression without fixed hardware or qualified CodSpeed Macro Runner and independent multi-execution A/A noise cohorts.

The [successful research Actions #41639205283](https://github.com/PhysicsQoo/QuPRS/actions/runs/41639205283) and [first-party CodSpeed run](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6ae9d9bd1f5d556dd9cce4af) validated 32/32 real Solver-calling measurements, source-pinned NEQ, and ABBA/BAAB order. Hybrid median effect was -1.10% with max A1/A2 drift 3.81%; WMC-only median +0.75% with drift 4.33%. Both are **PERFORMANCE_INCONCLUSIVE**; no research branch or workflow was merged wholesale into dev.

# CodSpeed v3 formal performance strategy (QOO-170)

For every PR keep all **five Simulation shards** with 32 legacy benchmark identities + 12 newer QASM261 CPU identities, 30 Rust Native/core identities, and **10** source-pinned paired Solver-inclusive WallTime cases including QAOA7 Rust/GPMC WMC-only at 90 printed digits. These remain the authoritative CI coverage for actual stages/verdicts/cost; the existing ten-case and five-shard jobs are not modified by the P5 opt-in experiment.

**Timing is not science correctness.** The 10 routine base/HEAD pairs run within the same GitHub job/runner but are not per-invocation ABBA samples. Different hosted CPUs/VMs or run dates cannot produce certified regression percentages. CodSpeed CPU Simulation excludes actual external Solver child cost. The P5 statistical interpretation stays \`NOT_CERTIFIED\`, with **no fixed performance threshold** blocking merges. Source QASM, Solver stage, numerical precision, EQ/NEQ and timeout science guards remain strict.

## On-demand true ABBA/BAAB

The pre-existing \`p5-abba\` job in \`.github/workflows/codspeed.yml\` is activated **only** when a PR description is edited while including exactly:

\`<!-- quprs-codspeed-v3-abba -->\`

Remove this marker before later description edits to avoid unintended repeat jobs. Routine PR opens, synchronizes and ordinary edits without the marker never run this opt-in diagnostic.

The opt-in job uses exact SHA-pinned base and HEAD in two independent Python/Rust environments on the same hosted runner, a shared QAOA7 Random_Rotation NEQ QASM pair, Rust/GPMC with RR \`1e-10\`, distance/phase \`1e-8\`, and **90 printed GPMC digits**. For **Hybrid and WMC-only**, it runs **ABBA, BAAB, BAAB, ABBA** (4 blocks ×4 positions per method; **32 official single-round CodSpeed WallTime measurements**). Each timed position runs an actual GPMC subprocess once; four additional prewarms (two methods × two revisions) are separately recorded. \`pytest-codspeed==5.0.4\` \`pedantic(rounds=1, iterations=1, warmup_rounds=0)\` makes an extra, untimed target call to retrieve a return value; the proven post-timing cache blocks a duplicate Solver execution and fails closed if plugin behavior changes.

The independent reporter rejects wrong SHA/inputs, missing measured URI, multiple rounds or invocations, wrong Solver/NEQ/precision, and incomplete warmup. It reports the paired block ratios and A1/A2 drift with **observational-only** status. Never claim a ~1% speedup or regression without fixed hardware or qualified CodSpeed Macro Runner and independent multi-execution A/A noise cohorts.

The [successful research Actions #41639205283](https://github.com/PhysicsQoo/QuPRS/actions/runs/41639205283) and [first-party CodSpeed run](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6ae9d9bd1f5d556dd9cce4af) validated 32/32 real Solver-calling measurements, source-pinned NEQ, and ABBA/BAAB order. Hybrid median effect was -1.10% with max A1/A2 drift 3.81%; WMC-only median +0.75% with drift 4.33%. Both are **PERFORMANCE_INCONCLUSIVE**; no research branch or workflow was merged wholesale into dev.

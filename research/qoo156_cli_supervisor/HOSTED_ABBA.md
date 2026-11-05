# QOO-156 interim performance admission: hosted paired ABBA

Status: **controlled interim CLI-specific gate, NOT CodSpeed Macro**.

CodSpeed Macro scheduling is currently unavailable. QOO-156 must not indefinitely block its CLI-safety implementation while preserving the project's scientific and native-algorithm performance rules. This one-purpose gate runs on a **single GitHub-hosted Ubuntu 24.04 x86-64 runner**, compiling the baseline dev CLI and the staging HEAD CLI from exact SHAs with separate target directories and the **same unchanged rust/pathsum Git tree**. It does not replace regular CodSpeed for other project performance comparisons.

## Measurement and integrity

- Test the fully public base and HEAD CLI, not the hidden worker bypass.
- Identical source-locked input QASM, toolchain, source tree for native algorithm, one runner and an OS CPU-affinity record. Do not conflate source identity with binary equality.
- 8 interleaved warmups followed by **30 paired blocks per case**, alternating **ABBA / BAAB**. Cases: single H, GHZ32 RR, QPE-exact8 RR. Record **every subprocess elapsed perf_counter_ns**, raw stdout and stderr hashes, scientific output identity, fixture hashes, both binary hashes, runner name, OS/CPU/affinity, and source SHAs.
- For each block, calculate mean(HEAD pair) minus mean(BASE pair); bootstrap the median of the 30 paired deltas with 4000 fixed-seed samples for an approximate 95% interval. Measure within-variant paired jitter separately; a high jitter or borderline confidence interval must produce **INCONCLUSIVE**, not PASS.
- Require both revisions to exit 0 with byte-identical full scientific stdout on every warmup and test. Do not use a real solver in this **RR-only CLI process-overhead** comparison; memory/OOM/cancellation real solver safety already has separately archived P0 evidence.
- **Provisional engineering envelope**, subject to explicit release review: upper 95% bootstrap endpoint for extra fixed CLI overhead at most **3.0 milliseconds** for each case; median within-variant paired jitter at most **1.5 milliseconds**. This is an acceptance of **bounded additive CLI overhead**, NOT a claim of no regression. A high/noisy runner or exceeded budget returns nonzero and archives its raw evidence.
- Why 3.0 ms: earlier non-Macro official CodSpeed hosted WallTime observations clustered around **+1.19 to +1.20 ms**; the 3 ms ceiling is a preliminary engineering tolerance for the mandatory safety wrapper rather than a statistically derived release SLO. No sub-3 ms relative percentage guarantee for a 1 ms circuit can be claimed.

## Triggers and costs

The staging-scoped workflow [qoo156-cli-hosted-abba.yml](../../.github/workflows/qoo156-cli-hosted-abba.yml) builds exactly two CLI binaries and runs one CPU-constrained paired experiment on source/benchmark/experiment-workflow changes, **never on docs-only changes**. The complete five-shard CodSpeed matrix, GPMC/Ganak real-solver binaries and other science suites are not repeated. Store JSON raw samples and a Markdown summary as GitHub Actions artifacts and retain the exact GitHub run URL.

If the hosted runner is noisy or source identity differs, report **NOT_ADMITTED** or **INCONCLUSIVE** and do not infer speedup/regression from the resulting point estimates. Measurements on different hosted runners/days have distinct hardware/system-load environments and must not be pooled without a demonstrated common environment.

## Release decision

This workflow is a **temporary QOO-156-specific alternative**, not an automatic general project policy change. With the P0 cancellation/cgroup/science proof and a valid hosted ABBA **bounded-overhead** result, the feature can proceed to review, with documented fixed CLI startup cost. The final choice of a 3 ms release threshold remains subject to maintainer agreement. Native Rust algorithm performance still follows the established official CodSpeed provenance.

Mac mini/OrbStack guest cgroup controller delegation is an independent deployment qualification, not something this elapsed-time benchmark can prove. CodSpeed Macro may be reintroduced when the runner is actually provisioned without invalidating the provisional evidence.

## First source-pinned execution — 2026-11-05

[GitHub Actions #41930775591](https://github.com/PhysicsQoo/QuPRS/actions/runs/41930775591) **SUCCESS**, tested exact source commit [a2b997c](https://github.com/PhysicsQoo/QuPRS/commit/a2b997c156aa9bebc08db485768e03fbab0d3d28), with [raw per-invocation JSON and report artifact #13372131499](https://github.com/PhysicsQoo/QuPRS/actions/runs/41930775591/artifacts/13372131499). Both binaries were built as Release from the same Rust native pathsum tree on the same Ubuntu 24.04 x86-64 runner.

| RR / CLI case | Paired median additive HEAD overhead | 95% bootstrap interval | Same-variant pair jitter median | Budget classification |
|---|---:|---:|---:|---|
| Single H, single-circuit | +1.331 ms | +1.311 to +1.387 ms | 0.039 ms | WITHIN_PROVISIONAL_FIXED_COST_BUDGET |
| GHZ32, EQ dual | +1.297 ms | +1.289 to +1.335 ms | 0.032 ms | WITHIN_PROVISIONAL_FIXED_COST_BUDGET |
| QPE-exact8, EQ dual | +1.596 ms | +1.309 to +1.683 ms | 0.069 ms | WITHIN_PROVISIONAL_FIXED_COST_BUDGET |

All three completed 30 alternating ABBA/BAAB blocks each and matched full scientific stdout hashes. The predeclared provisional ceiling of **+3.0 ms additive overhead** was met for these cases. **This is not evidence of zero performance regression**, nor is it a verified threshold for solver-intensive workloads or a hardware-independent confidence interval. The bounded absolute latency may represent a very large *relative* overhead on sub-2ms CLI tasks. A maintainer must still decide whether this safety wrapper tradeoff is acceptable for release.

The original [Macro job #41825389124](https://github.com/PhysicsQoo/QuPRS/actions/runs/41825389124) remains unassigned, and an unrelated [official CodSpeed hosted run](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aeb4b9d09f1ddb2bf501af8) is observational only. **No Macro result is necessary for this temporary, explicitly scoped CLI-cost evidence**; normal CodSpeed requirements for core Rust algorithmic changes are not changed.

## Final staged P1 performance evidence — 2026-11-05

Clean [staging source `56c8205`](https://github.com/PhysicsQoo/QuPRS/commit/56c8205e8be396b8677e762f93b4a8d3e04f2f68)
contains only verified CLI `supervisor.rs` and `supervisor`
integration tests plus documentation; native Rust `rust/pathsum`
and solver code are identical to the pinned dev baseline.
All research-only Docker/cgroup-pilot workflows remained on the experiment
branch. The CI [hosted ABBA run #41943543958](https://github.com/PhysicsQoo/QuPRS/actions/runs/41943543958)
**SUCCESS** and [raw timing artifact #13377816518](https://github.com/PhysicsQoo/QuPRS/actions/runs/41943543958/artifacts/13377816518)
preserve 30 alternating ABBA/BAAB paired blocks per case:

| Case | Median paired extra CLI latency | 95% bootstrap interval | Paired control jitter | Classification |
|---|---:|---:|---:|---|
| Single H | +1.961 ms | [1.949,1.991] ms | 0.042 ms | WITHIN_PROVISIONAL_FIXED_COST_BUDGET |
| GHZ32 RR | +1.954 ms | [1.933,1.980] ms | 0.067 ms | WITHIN_PROVISIONAL_FIXED_COST_BUDGET |
| QPE-exact8 RR | +1.877 ms | [1.862,1.895] ms | 0.022 ms | WITHIN_PROVISIONAL_FIXED_COST_BUDGET |

The temporary **3ms additive CLI overhead** engineering envelope
holds for these three cases on a single runner; this is not proof of
zero regression, no guarantee for different hardware, not CodSpeed Macro
and not a final release-SLO approval. Previous QOO-156 P0-only data
(+1.5–1.6ms) came from a different hosted execution and must not be
subtracted as though it were a directly controlled P1 A/B comparison.

Native [P1 process and actual OOM CI #41942991745](https://github.com/PhysicsQoo/QuPRS/actions/runs/41942991745)
independently passed on the exact source blobs that staging copied:
Linux 11 unit +20 integration; macOS14 ARM64 8 unit +16 integration;
both Release compiled; nonroot UID65534 cgroup positive/negative
admitted, with no residual child cgroups. The user-visible CLI continues
to have real startup overhead, now roughly +1.9–2.0ms.

## Tested final staging source: P0 signal/oom changes + P1 budget

P0 source [experiment commit `5930fdf`](https://github.com/PhysicsQoo/QuPRS/commit/5930fdfbf8161b436614d819fcc1dddc1ff94445)
was accepted in [native scoped CI #41940690787](https://github.com/PhysicsQoo/QuPRS/actions/runs/41940690787):
Linux **9 unit +17 integration**, macOS14 ARM64 **7 unit +13 integration**,
all tests and both Release builds PASS. Verified external SIGINT/SIGTERM,
Linux direct worker parent SIGKILL, real detached-session helper on timeout
and on signal cancellation, and cgroup OOM event fail-closed parsing.
The scientific Rust pathsum tree remains unchanged.

The exact tested changes entered [staging commit `61460eb`](https://github.com/PhysicsQoo/QuPRS/commit/61460ebe60fde8768abfbfd4422e9e953d2db158).
The scoped hosted ABBA [#41941084754](https://github.com/PhysicsQoo/QuPRS/actions/runs/41941084754)
**SUCCESS**, with complete [raw artifact #13376437268](https://github.com/PhysicsQoo/QuPRS/actions/runs/41941084754/artifacts/13376437268):

| RR / CLI case | Median additive overhead | 95% bootstrap CI | Median paired control jitter | Result |
|---|---:|---:|---:|---|
| Single H | +1.579 ms | [1.565, 1.587] ms | 0.040 ms | WITHIN_PROVISIONAL_FIXED_COST_BUDGET |
| GHZ32 | +1.558 ms | [1.545, 1.572] ms | 0.049 ms | WITHIN_PROVISIONAL_FIXED_COST_BUDGET |
| QPE-exact8 | +1.502 ms | [1.493, 1.513] ms | 0.031 ms | WITHIN_PROVISIONAL_FIXED_COST_BUDGET |

A **3ms provisional absolute CLI overhead budget** holds in this one same-runner
source-paired observation; it is neither zero regression nor a CodSpeed
Macro certification. The Linux PDEATHSIG directly protects the worker,
**not arbitrary daemonized grandchildren after supervisor SIGKILL**. macOS
does not have Linux subreaper, cgroup v2 or PDEATHSIG. Parent-owned private
temp directories, cgroup Drop cleanup diagnostics, and independent Mac mini
OrbStack runtime qualification remain separate follow-up topics.


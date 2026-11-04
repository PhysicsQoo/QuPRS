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

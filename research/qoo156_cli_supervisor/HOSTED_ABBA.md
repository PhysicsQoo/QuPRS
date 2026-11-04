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

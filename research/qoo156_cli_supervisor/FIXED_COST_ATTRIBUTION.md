# QOO-156 — CLI fixed-cost attribution (2026-11-05)

**Decision: no additional Rust CLI hot-path optimization for v0.14.0 on current evidence.** Worker process launch is the major fixed cost. The additional P1 private-temp cleanup is only 0.07–0.10 ms per CLI request, and reverting it would weaken forced-cancellation protection. The stage probe remains on an independent research branch, not in staging.

## Exact-source evidence and method

- [Successful same-runner controlled experiment #41945871411](https://github.com/PhysicsQoo/QuPRS/actions/runs/41945871411); [full raw sample and stage artifact #13377634261](https://github.com/PhysicsQoo/QuPRS/actions/runs/41945871411/artifacts/13377634261).
- Dev: 79e975b0b21c0c650db7a76fe6e35b926c67c2c8
- P0: 61460ebe60fde8768abfbfd4422e9e953d2db158, supervisor with signal/timeout safety before P1 private TMPDIR.
- P1: 56c8205e8be396b8677e762f93b4a8d3e04f2f68, final verified cleanup code copied to clean staging.
- Research-only stage probe: d390529cecf7deafdb91eeccacea7b85492a17e8 on [experiment/qoo156-cli-fixed-cost-attribution](https://github.com/PhysicsQoo/QuPRS/tree/experiment/qoo156-cli-fixed-cost-attribution). Do not merge the instrumentation.
- All four source trees have identical native rust/pathsum Git identity. Three QASM fixtures, exact scientific stdout hashes, separate Release binaries. One Ubuntu 24.04 x86-64 GitHub-hosted runner, same CPU affinity.
- Each uninstrumented production pair uses 24 alternating ABBA/BAAB 4-call blocks, eight warmups and a per-pair median difference with 95% bootstrap CI. Probe study uses 48 per-case samples and 20 probe-on/off controlled blocks. The three pairwise median deltas are independent and do not exactly add.

## Incremental CLI cost, paired median HEAD minus BASE (ms)

| Case | Dev -> P0 | P0 -> P1 | Dev -> P1 |
|---|---:|---:|---:|
| Single H | +1.538 [1.520,1.556] | +0.103 [0.060,0.117] | +1.640 [1.609,1.664] |
| GHZ32 RR | +1.530 [1.506,1.550] | +0.067 [0.053,0.098] | +1.625 [1.616,1.665] |
| QPE-exact8 RR | +1.540 [1.527,1.561] | +0.082 [0.053,0.117] | +1.652 [1.621,1.696] |

The P0 supervisor dominates. P1 private cleanup is about +0.07 to +0.10 ms, not +0.4 ms inferred by subtracting results from different runners. In this run, the complete P1 CLI remained materially slower for very short circuits (~50–76% relative to dev), despite meeting the provisional +3 ms absolute-cost envelope. No unmeasured Solver-inclusive or cgroup-enabled performance claim is implied.

## Source-instrumented monotonic-clock partitions (medians, ms)

Phase intervals partition the parent supervisor entry through final result publication. Native engine work is shown separately and is **not** part of the added supervisor cost.

| Stage | Single H | GHZ32 RR | QPE8 RR |
|---|---:|---:|---:|
| Parent setup before worker spawn | 0.072 | 0.071 | 0.080 |
| **Worker bootstrap / process launch / admission** | **1.100** | **1.093** | **1.149** |
| Native RR calculation (not overhead) | 0.042 | 0.168 | 1.027 |
| Worker exit and both output EOF | 0.304 | 0.308 | 0.342 |
| Parent cleanup and result publish | 0.072 | 0.073 | 0.083 |

### Microstages (median ms; some intervals overlap)

| Substage | Single H | GHZ32 | QPE8 |
|---|---:|---:|---:|
| Process guard setup | 0.0014 | 0.0014 | 0.0014 |
| **Private TMPDIR creation** | **0.0362** | **0.0358** | **0.0399** |
| Parent output spool-file creation | 0.0207 | 0.0208 | 0.0218 |
| Command configuration | 0.0118 | 0.0122 | 0.0140 |
| **Command::spawn() process creation handshake** | **0.3530** | **0.3416** | **0.3646** |
| Worker CLI argument parsing + admission | 0.0670 | 0.0727 | 0.0752 |
| Capture/wait thread launch | 0.0688 | 0.0653 | 0.0946 |
| Adopted-child cleanup | 0.0179 | 0.0175 | 0.0192 |
| **Private TMPDIR disposal** | **0.0392** | **0.0404** | **0.0438** |
| Final join + result copy | 0.0150 | 0.0149 | 0.0161 |

TMPDIR creation plus disposal (~0.075–0.084 ms) closely matches the independently measured P0-to-P1 +0.067–0.103 ms. Physical cgroup limits were not enabled in these RR cases; no cgroup cleanup timing is inferred.

**Observer effect:** the instrumented worker writes a trace after its engine finishes, inflating the worker-exit/EOF phase. Probe-on versus off for the same binary adds +0.097 ms [0.080,0.119] Single H; +0.121 ms [0.113,0.132] GHZ32; +0.121 ms [0.096,0.145] QPE8. In contrast, compiling the research profiling feature with the probe *disabled*, versus the exact unmodified P1 binary, showed +0.007 ms [−0.035,+0.062], +0.013 ms [−0.021,+0.049] and −0.025 ms [−0.068,+0.008]. Do not treat the whole 0.30–0.34 ms exit figure as intrinsic production cost. Median phase times are not additive; Python-observed external wall includes initial exec, process exit, scheduling and profile I/O.

## Engineering decision

| Idea | Expected reward and safety cost | Decision |
|---|---|---|
| Remove private TMPDIR | Saves only about 0.08 ms while risking sensitive CNF/solver remnants on worker SIGKILL | **Reject** |
| Bypass worker / weaken signal, timeout, result isolation | Could remove process startup but invalidates user-facing safety contract | **Reject** |
| Drop spool output or atomic verdict commit | Small cost, risks partial scientific output | **Reject** |
| Replace three reader/wait threads with complex event loop | Startup about 0.065–0.095 ms; new deadlock/EOF cross-platform risk | **Defer** |
| Optimize full worker bootstrap | About 1.1 ms, including spawn syscall around 0.34 ms and process/runtime startup | **Only meaningful structural opportunity** |
| Persistent worker broker or request-batching interface | Could amortize startup for many tiny circuits but creates new cancellation and resource-isolation semantics | **Future separate design if such workload matters** |

**Decision:** Keep the existing P0/P1 supervisor, do not introduce new timing-sensitive code changes before v0.14.0 merge review. The incremental P1 safety cleanup is not a worthwhile optimization target. If users frequently launch many tiny CLI checks, scope a separate persistent broker / multi-circuit batch API with strict per-request timeout and failure isolation; validate with CodSpeed where supported, not by bypassing safety. Native Path-sum/RR/WMC benchmarks do not incur this CLI wrapper.

## Open release gates / limits

The +3 ms additive CLI threshold is still *provisional*, not accepted release SLO. Hosted same-runner ABBA does not replace CodSpeed Macro or normal native algorithm CodSpeed. Cross-day/cross-host performance is not certified; Mac mini/OrbStack cgroup delegation remains a separate deployment acceptance. Supervisor SIGKILL is uncatchable; full job tree and temp cleanup then require an external job/container manager. No dev/main merge or native Rust algorithm change was made by this study.

# QOO-156 P1 — private worker files and cgroup cleanup (controlled experiment)

Source: [experiment/qoo156-p1-private-temp-cgroup-cleanup](https://github.com/PhysicsQoo/QuPRS/tree/experiment/qoo156-p1-private-temp-cgroup-cleanup).
**Not dev/main; CI and performance certification are source-SHA specific.**

## Safety boundary and implementation

The Rust CLI supervisor creates one mode-0700 private `tempfile::TempDir` per invocation and passes that directory as the **worker-only** `TMPDIR`. The unchanged Rust Path-sum WMC implementation writes `temp_eqcheck_*.cnf` and `quprs-solver-*.tmp` using `std::env::temp_dir()`, so the files are nested inside this parent-owned directory. The parent does not change its global `TMPDIR` or modify native Rust RR/WMC code.

After the direct worker is reaped and the supervisor's tracked descendants are cleaned, and before **any successful verification stdout** can be published, the supervisor removes the entire private directory with `TempDir::close()`. On a failure to close, return typed `ResourceSupervisorCleanupError`, exit **125**, and **no science verdict**. The ordinary `QUPRS_KEEP_FAILED_CNF=1` explicit debugging contract is retained **only** for a worker that returns a normal nonzero exit and leaves a failed CNF; its mode-0700 private directory is then deliberately retained and its path reported to stderr. Cancellation, timeout, OOM and successful requests do **not** preserve it, even if the debug flag is set.

Important limits: the parent must still be alive to finalize files; an external `SIGKILL` delivered directly to the **supervisor** prevents the parent from running cleanup, and a separate host/VM/container job-lifetime manager is necessary for guaranteed whole-job teardown. Arbitrary external solvers that deliberately ignore `TMPDIR` are outside this file-namespace contract. The mode-0700 directory is *not* a same-user attacker sandbox.

For Linux `--max-memory-mib`, after reaping the worker and before stdout commit, the supervisor reads `memory.events` for OOM attribution, then reads the cgroup-v2 `cgroup.events` `populated` witness. Any remaining populated worker cgroup is killed via `cgroup.kill` and `rmdir` is retried at most 1 second. Missing, duplicated or malformed `populated`, kernel I/O errors or a still-unremoved group return typed **125** with no science verdict. The `Drop` fallback also logs failures; it can no longer silently discard them. This extra I/O occurs **only** when physical cgroup limiting was explicitly requested; it is not in native RR/WMC calculation paths.

## P1 verification evidence

- [Scoped native Linux/macOS + true delegated memory CI](https://github.com/PhysicsQoo/QuPRS/actions/runs/41942991745) **SUCCESS**: Linux Ubuntu24.04 **11 unit + 20 integration + Release**, macOS14 ARM64 **8 unit + 16 integration + Release**. It tests deterministic debug-only CNF and Solver temp remnants created **inside the actual inherited TMPDIR**, then sends SIGTERM or forces timeout. It also checks explicit failed-CNF retention and constructs invalid fake `cgroup.events` witnesses.
- Linux *positive* kernel OOM (64 MiB, exit 125, kernel oom_kill=2, no stdout) + high-cap correctness (256 MiB, exit0, valid Path-sum) in the dedicated CI job use a **test-only privileged container to create cgroup delegation**, but the CLI runs as nonroot **UID65534**. The adapted [tested pilot](https://github.com/PhysicsQoo/QuPRS/blob/experiment/qoo156-p1-private-temp-cgroup-cleanup/scripts/qoo156_p1_cgroup/pilot.py) requires `worker_cgroup_removed_at_return=true` on both cases; both are **PASS** in raw [run #41942991745](https://github.com/PhysicsQoo/QuPRS/actions/runs/41942991745) evidence. Privileged Docker is **not** a production deployment requirement.
- Source-paired hosted ABBA/BAAB on the final staged CLI remains the interim cost instrument while CodSpeed Macro is unavailable; the provisional budget of **3ms additional CLI startup overhead** must be checked again after this change, and its approval for release remains a separate maintainer decision.

## Explicitly not covered by this P1 fix

This does not create a strict wall-clock guarantee for terminal stdout copying, nor solve detached daemon survival after **supervisor** SIGKILL or complete macOS subreaping. It does not modify native Path-sum, GPMC or Ganak original algorithms. The Mac mini/OrbStack guest environment's cgroup delegation remains a separate deployment qualification.

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


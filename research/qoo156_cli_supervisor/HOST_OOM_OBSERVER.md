# QOO-156 — host-side external cgroup OOM witness (2026-11-04)

This is an **isolated controller-observability gate** in `experiment/qoo156-oom-host-observer`, not a QuPRS native-solver or in-process CLI memory-limit certificate.

## Positive source-pinned observation

[GitHub Actions #41853874574](https://github.com/PhysicsQoo/QuPRS/actions/runs/41853874574) SUCCESS, source [`7c45558`](https://github.com/PhysicsQoo/QuPRS/commit/7c45558f8a1f9f47e99f01c90d1fb2fb60091d6d), [artifact #13335623704](https://github.com/PhysicsQoo/QuPRS/actions/runs/41853874574/artifacts/13335623704). Container image ID `sha256:ae4e8b7c575fabea88a029b6cae757f342ca2525e07f7c22272d5105c346b35e` (resolved by the actual runner; do not assume an evergreen tag is immutable).

A host Python recorder started **outside** the Docker memory-limited container, found its host PID and cgroup-v2 path from `/proc/<pid>/cgroup`, read and verified `memory.max` **before** creating an external start marker, and persisted append-only fsync-backed `memory.events` journal lines. The actual container driver touched 192 MiB of pages and was never allowed to change the host ledger.

| Cap | Host memory.max | Host kernel oom_kill delta | Container exit | Docker OOMKilled | memory.peak | Result |
|---|---:|---:|---:|---|---:|---|
| 128 MiB | 134,217,728 bytes | +1 | 137 | true | 134,217,728 bytes | **PASS: kernel OOM retained after container died** |
| 320 MiB | 335,544,320 bytes | 0 | 0 | false | 211,656,704 bytes | **PASS: source-backed high-cap control finished** |

The 128 MiB recorder's `kernel_oom_observed` event was fsync-persisted while the host cgroup existed. The 320 MiB control later recorded `observation_lost` after its container had already exited successfully; the immediately preceding complete scientific-control marker (page touch), exit=0 and no OOM state were preserved. A disappearing cgroup after normal container completion must not be called an OOM.

The first [pilot #41853514789](https://github.com/PhysicsQoo/QuPRS/actions/runs/41853514789) failed before test pressure: the host temporary control directory was 0700, inaccessible to the rootless/cap-drop container process. The correction in `7c45558` makes the marker directory traversable (0755); it is a **fixture permission repair**, not a numerical or memory-usage change.

## Remaining assertions NOT certified

- The experiment does **not** execute QuPRS CLI, GPMC, Ganak, CNF, RR or WMC. It proves host-side `memory.events` durability when a resource-limited container driver disappears.
- It does **not** prove which PID the Linux kernel selected in a real solver OOM; a solver-specific identity and mode must be witnessed *before* pressure and its actual exit must be reconciled with the host kernel event and absence of harness kill. Previously observed GPMC [#41849006978](https://github.com/PhysicsQoo/QuPRS/actions/runs/41849006978) had a true kernel-event subcase but combined GPMC/Ganak workflow failed; Ganak remained NOT_ADMITTED.
- This does **not** certify internal `QuPRS_cli --max-memory-mib` under delegated cgroup; GitHub-hosted runners could not supply writable child-cgroup delegation. It does not certify Mac mini/OrbStack ARM64 parity.
- The resource experiment provides no CodSpeed timings and does not change the `rust/pathsum` hot path.

## Next targeted real-solver handoff

Use this host observer as an independent outer witness around one source-pinned real GPMC/Ganak Docker run. Add an early, flushed and source-locked solver PID + start-time + ELF SHA + argv milestone *before* test-only pressure; preserve native CLI stdout/exit/error without assuming a complete in-container JSON record survives OOM. Maintain a bounded high-cap complete control. Classify results strictly into: `REAL_SOLVER_KERNEL_OOM_CERTIFIED` (only with matching PID identity, kernel event, authentic solver SIGKILL and no harness kill), `CONTAINER_OOM_VICTIM_UNATTRIBUTED`, `SOLVER_TIMEOUT_CLEANUP`, `HARNESS_KILL`, `NO_KERNEL_OOM`, `NOT_ADMITTED`.

Do **not** rerun the unchanged failing in-container-only victim harness. Run only a scoped controlled source-pinned experiment and preserve the artifact whether positive or negative. No `dev` merge until resource and formal CodSpeed gates are admitted.

## 2026-11-04 authentic real GPMC/Ganak host-attributed OOM: PASS

The follow-up **has now been executed**: [GitHub Actions #41855049422](https://github.com/PhysicsQoo/QuPRS/actions/runs/41855049422) SUCCESS, exact source `96500fa1cabd2e4db8bd1bc481a62fcae77229fc`, [artifact #13335529621](https://github.com/PhysicsQoo/QuPRS/actions/runs/41855049422/artifacts/13335529621). This **supersedes the previous pending host-recorder/real-solver handoff**, not the separate internal delegated-cgroup gate. Both solver binaries are genuine and unchanged; Rust `rust/pathsum` tree unchanged. One compiled release CLI SHA256 `8319636e21d88a4b559a054fb0f4ffafd642158fe728ed93f2336eab78e67f0d`. Host reader was armed **before** container was released through its start barrier; test driver printed flushed real solver identity/PID/ELF/argv and `oom_score_adj=1000` **before** applying test-only page pressure.

| Solver | Genuine invoked mode | 1024MiB complete high-cap control | 256MiB host oom_kill delta | Real solver signal | Harness killed real solver? | CLI science stdout |
|---|---|---|---:|---|---|---|
| GPMC, ELF SHA `507919b9...` | `-mode=1` | `REAL_WMC_COMPLETE_PASS`, `not_equivalent` | +1 | SIGKILL, PID absent afterwards | no | empty |
| Ganak 2.8.0, ELF SHA `934a79a3...` | `--mode=6` | `REAL_WMC_COMPLETE_PASS`, `not_equivalent` | +1 | SIGKILL, PID absent afterwards | no | empty |

Both 256MiB cgroups reported `memory.peak=268435456` bytes, and the **external host** independently persisted `host_kernel_oom` events to fsync-backed journals. The inner test also independently reported `kernel_oom_kill_delta=+1`, exact genuine solver SIGKILL in the CLI's error, `test_harness_killed_solver=false`, and `worker_reports_authentic_solver_sigkill=true`. Pressure helper exit -9 is **not** proof it was the kernel victim; the test driver intentionally terminates pressure after detecting kernel OOM. The real Solver's SIGKILL coinciding with the authenticated OOM event and no harness kill is the admitted target. Both outer **container** processes exited 0 because their supervising Python drivers successfully classified the simulated resource incident; Docker `OOMKilled=true` records a kernel child kill. **Do not** interpret container exit0 as normal scientific success in the low-cap case: no EQ/NEQ was emitted by QuPRS there and Rust CLI returned nonzero (code1, generic WorkerFailed).

The scientific high-cap control and the adversarial low-cap experiment are **different executions on the same pinned release binary**. This result certifies only that a *kernel-enforced external Docker memory cap* can kill a real GPMC/Ganak worker while the CLI avoids a false EQ/NEQ result in these bounded Linux x86-64 workloads. It does **not** establish natural minimum solver memory, cross-architecture footprint, an internal typed `MemoryLimitExceeded`, or a true hard wall-clock guarantee for a non-cooperative detached process outside containment. Numerical WMC parity between GPMC/Ganak is likewise not claimed; both high-cap control verdicts were `not_equivalent`.

The source-locked scripts are `scripts/qoo156_host_oom_probe/{host_ledger,real_solver_host_ledger}.py` and `scripts/qoo156_solver_oom_victim/driver.py`; the workflow is `.github/workflows/qoo156-host-real-solver-oom.yml`. Do not rerun high-cost authentic solver witnesses just for documentation changes. Separate Linux delegated child-cgroup `--max-memory-mib` positive gate and Mac/OrbStack Linux ARM64 remain **NOT_ADMITTED / NOT_TESTED**. Formal CLI performance on CodSpeed Macro remains **NOT_ADMITTED**.


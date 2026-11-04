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

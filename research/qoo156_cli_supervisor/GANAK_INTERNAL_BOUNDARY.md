# QOO-156 — Ganak 2.8.0 native internal cgroup boundary (2026-11-04)

**Result:** one source-pinned, bounded **71/72 MiB outcome bracket** for the exercised Linux x86-64 release CLI and exact VQE4 QASM pair. [GitHub Actions #41860152162](https://github.com/PhysicsQoo/QuPRS/actions/runs/41860152162) **SUCCESS**, source [`87ab32b470841145c861b200dfcafe064e9ab49d`](https://github.com/PhysicsQoo/QuPRS/commit/87ab32b470841145c861b200dfcafe064e9ab49d), [artifact #13340100534](https://github.com/PhysicsQoo/QuPRS/actions/runs/41860152162/artifacts/13340100534).

This deliberately makes **no changes** to `rust/cli`, `rust/pathsum`, `GPMC`, or the Ganak binary: relative to pre-pilot `7c9372dd4a81ec0b2ceb8ef540d30e6c27055404`, the experiment only added `scripts/qoo156_internal_cgroup/ganak_boundary.py` and `.github/workflows/qoo156-ganak-internal-boundary.yml`.

## Source and execution provenance

- CLI release executable SHA256: `2242188d29056c5cc6db1d91bc6132bee1c91a212cf35fd54dacee6d2f5c3d50`.
- Genuine Ganak 2.8.0 ELF SHA256: `934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd`, authentic `--mode=6` process witnessed for completed cases.
- VQE4 source SHA256: `757e5714303e731bebc156c230024480b1d72df503d70dd0a9eb76d112ffdd62`; same QASM with an additional X mutation, WMC-only and proportional; expected complete verdict `not_equivalent`.
- Ephemeral test-only elevated Docker cgroup-v2 setup, CLI **UID 65534**, true delegated CLI-child `memory.max` (not RLIMIT_AS), actual kernel `memory.events` counters. Container outer cap 512 MiB. This does **not** prove a normal end-user host already delegates writable cgroups.
- All comparisons on one pinned release binary in a single runner job. Memory peak is **CLI-created worker cgroup, including Ganak and child tasks**, not Solver-only RSS. All timing is observational and not CodSpeed.

## Measured cases

| Internal memory.max | Exact byte cap | cgroup memory.peak | oom_kill events | Ganak mode6 PID witness | CLI exit | Science stdout | Classification |
|---|---:|---:|---:|---|---:|---|---|
| 71 MiB | 74,448,896 | 74,448,896 | 2 | No | 125 | empty | `INTERNAL_CGROUP_OOM_NO_GANAK_PID_WITNESS` |
| 72 MiB | 75,497,472 | 74,964,992 | 0 | Yes | 0 | `not_equivalent` | `REAL_GANAK_COMPLETE_WITHIN_INTERNAL_CAP` |
| 73 MiB | 76,546,048 | 74,969,088 | 0 | Yes | 0 | `not_equivalent` | `REAL_GANAK_COMPLETE_WITHIN_INTERNAL_CAP` |
| 74 MiB | 77,594,624 | 74,969,088 | 0 | Yes | 0 | `not_equivalent` | `REAL_GANAK_COMPLETE_WITHIN_INTERNAL_CAP` |
| 80 MiB | 83,886,080 | 74,964,992 | 0 | Yes | 0 | `not_equivalent` | `REAL_GANAK_COMPLETE_WITHIN_INTERNAL_CAP` |
| 256 MiB | 268,435,456 | 74,969,088 | 0 | Yes | 0 | `not_equivalent` | high-cap control PASS |

- At 71 MiB the kernel physically enforced the exact cap and emitted two `oom_kill` events. QuPRS CLI returned **125 `MemoryLimitExceeded`**, and withheld scientific output. No test harness kill was used. The live Ganak PID was **not captured**, so this **cannot certify Ganak as the kernel victim** or prove that the solver never began. An unobserved short-lived process is possible.
- From 72 MiB through 256 MiB the genuine Ganak `--mode=6` ELF, PID and argv were captured; it completed and emitted the same full `not_equivalent` science verdict, with zero OOM events and repeatably near-71.5-MiB peak.
- **Classification detail:** the reused low-cap `release_solver.run_case(..., high_cap=False)` naturally labels successful 72/73/74/80 MiB executions `original_harness_admitted=false`, because that old harness *expected OOM* for a “low” case. The dedicated `ganak_boundary.py` **independently reclassifies** each case from actual kernel cap, events, PID and complete science stdout. The final dedicated workflow gate `QOO156_GANAK_CGROUP_BOUNDARY_SAFETY=PASS` is correctly distinct from `QOO156_GANAK_INTERNAL_PID_OOM_ATTRIBUTION=NOT_ADMITTED`.

## Admission boundary and next action

- For this **one source-pinned x86-64 run**, the observed failure/success bracket is **71 MiB OOM / 72 MiB complete**. This is **not** a universal recommended minimum, a margin guarantee, or a binary-search proof across platforms and workload mixes. Real production limits need headroom for allocator peaks, circuits, input sizes and solver variations.
- The exercised internal CLI child cgroup does enforce a true memory cap and report a typed failure without false EQ/NEQ, even when no Solver PID can be captured. Combined with earlier [#41857419941](https://github.com/PhysicsQoo/QuPRS/actions/runs/41857419941) debug allocation certification, the mechanism is supported in a delegated environment.
- **Do not** change the supervisor just to label the 71 MiB run as Ganak-specific kernel victim. A real-solver victim witness under *adversarial post-PID* pressure was independently demonstrated for external Docker in [#41855049422](https://github.com/PhysicsQoo/QuPRS/actions/runs/41855049422), but not inside the new child cgroup. If a strictly solver-attributed internal OOM is ever a release gate, build a separate deterministic post-PID harness with preserved pre-pressure PID identity and explicit low-cap physical kernel events; do not conflate its memory demand with the natural threshold.
- **P1 still separate:** true CodSpeed Macro source-paired admission is blocked on runner assignment. Hosted WallTime observed a ~1.2-ms fixed CLI overhead but was flagged non-Macro; no claim of zero performance regression. Do not rerun costly solver studies for Markdown-only updates.

# Rust CLI resource supervision (QOO-156) — integration candidate

**Status: staging only. NOT merged into dev/main; performance admission pending.**

## Contract

The Rust executable supervises a separate worker from before QASM loading. The default `--timeout 600` is monotonic and covers both single/dual CLI modes. On a timeout, exit is **124**; `--quiet` emits `Timeout`, not a verification verdict. Completion/cleanup or publishing to a blocked downstream consumer may extend beyond the deadline: not a hard real-time guarantee. No Rust pathsum library fast-path changes are included.

Parent captures stdout and stderr concurrently with an active 16MiB per-stream limit. The worker cannot publish partial EQ/NEQ before successful completion; output-limit/resource failures exit **125**. The internal `--__quprs-worker` launch requires a parent and inherited admission pipe (misuse-resistant, not a same-user security sandbox). Legitimate external solver errors remain errors.

`--max-memory-mib MIB` is **opt-in physical memory control** ONLY on Linux with a writable delegated cgroup v2. The supervisor must live in a leaf sibling of the worker under an **empty memory-enabled delegated ancestor**, respecting the cgroup v2 no-internal-process rule. The CLI joins the worker to its own `memory.max`/`memory.oom.group=1` cgroup before exec, verifies exact cap readback, and returns typed `MemoryLimitExceeded` (exit **125**, no scientific verdict) for observed cgroup OOM. Without delegation, the command fails closed rather than running without the requested physical cap.

`--max-address-space-mib` instead uses Unix RLIMIT_AS, bounding virtual address space, **not physical RSS**; it must not be silently substituted for the physical cap. Native macOS lacks Linux cgroup-v2, so `--max-memory-mib` is unsupported there. Native macOS also lacks the Linux child-subreaper guarantee for detached solver grandchildren.

Usage, **only on a correctly delegated Linux host**:

```bash
QuPRS_cli left.qasm right.qasm --timeout 120 --max-memory-mib 2048 --quiet
```

The host/container manager must arrange writable cgroup v2 controller delegation. Do not deploy a privileged CLI or `docker --privileged` merely to bypass an unavailable delegation. A separate external Docker/VM memory cap constrains the entire process container but is **not** evidence of the internal CLI flag. The tested privileged Docker wrapper was only an isolated CI fixture; QuPRS_cli itself ran as UID65534. Mac mini + OrbStack Linux ARM64 must be qualified on that VM; a hosted ARM64 test is not environment equivalence.

## Source and qualification

Only CLI code, exact workspace lockfile, focused tests, a single CodSpeed CLI benchmark and this file were copied from the [QOO-156 experiment branch](https://github.com/PhysicsQoo/QuPRS/tree/experiment/qoo156-internal-cgroup-p0). No experimental Docker OOM scripts, upstream Solver source, full CI matrices or native Rust RR/CNF changes are included.

- Linux x86-64 delegated cgroup: [Actions #41857419941](https://github.com/PhysicsQoo/QuPRS/actions/runs/41857419941) PASS. Native Linux ARM64: [#41861084404](https://github.com/PhysicsQoo/QuPRS/actions/runs/41861084404) PASS, both with cap64MiB typed OOM and cap256MiB complete PathSum. These validate a *constructed* delegation, not ordinary host availability.
- Authentic GPMC `-mode=1` QFT16 high-cap science and low-cap PID-witnessed typed OOM within an internal cgroup: [#41858651234](https://github.com/PhysicsQoo/QuPRS/actions/runs/41858651234) scoped subcases PASS; overall workflow FAIL because a separate natural Ganak low-cap PID was not witnessed.
- Authentic Ganak 2.8 `--mode=6` VQE4 high-cap complete science and artificial pressure under the **same CLI-owned** internal cgroup with real PID pre-witnessed: [#41860226028](https://github.com/PhysicsQoo/QuPRS/actions/runs/41860226028) PASS. This is **not Ganak natural memory minimum**; historical 64/70MiB runs retain NOT_ADMITTED solver-victim attribution.
- Final EOF-timestamped CLI source was verified on the **actual native macOS 14 ARM64 runner** (GitHub image `macos-14-arm64`, `Darwin arm64`) alongside Ubuntu 24.04 x86-64: [#41927422324](https://github.com/PhysicsQoo/QuPRS/actions/runs/41927422324) **SUCCESS**, exact source commit `9e2246f8b9f5e1e070a6c6deab0d36b99f24fcf1`. macOS 7 unit + 10 integration tests PASS, Ubuntu 8 unit + 13 integration tests PASS, both release compiles PASS. The staged `rust/cli/src/supervisor.rs` blob is copied byte-for-byte from that tested source; all other staged CLI scientific source files remain the earlier tested originals. This is **macOS 14 Apple Silicon**, not macOS 15, and NOT OrbStack Linux ARM64.
- Prior scoped Linux/macOS14 CLI package test: [#41857895087](https://github.com/PhysicsQoo/QuPRS/actions/runs/41857895087) PASS. MacOS15 arm64 workflow [#41858819331](https://github.com/PhysicsQoo/QuPRS/actions/runs/41858819331) was cancelled before runner assignment in both attempts; **not a macOS15 code failure and not a PASS**.
- The [source-paired Macro workflow](https://github.com/PhysicsQoo/QuPRS/blob/staging/qoo156-cli-resource-admission/.github/workflows/qoo156-cli-macro-pr-admission.yml) now supports an **opt-in staging push before a dev PR**, as well as a source-impacting dev PR. A repository administrator must first provision the actual Macro runner and set `QOO156_MACRO_ENABLED=true`; without the variable the [staging run #41927682370](https://github.com/PhysicsQoo/QuPRS/actions/runs/41927682370) correctly reports **SKIPPED**, not a performance PASS. The same test records exact dev/base and staging/HEAD SHA and requires identical native Rust Path-sum tree. Never mistake an unassigned/queued or skipped job for formal CodSpeed admission.
- Official CodSpeed hosted, non-Macro [run 6aeb4b9d](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aeb4b9d09f1ddb2bf501af8) observed roughly **+1.19 to +1.20 ms** fixed CLI overhead for tiny Single H/GHZ32/QPE8, but CodSpeed flags WallTime reliability outside Macro Runners. The true [Macro job #41825389124](https://github.com/PhysicsQoo/QuPRS/actions/runs/41825389124) is queued, unassigned and source-stale. **P1 is NOT_MET**; do not claim zero CLI overhead or merge until a final-source Macro ABBA admits its costs.

Do not trigger full CodSpeed/release matrices on Markdown-only modifications. A staging Macro admission can precede a `dev` PR; do not merge until performance and platform requirements are resolved. A draft PR is not itself scientific or performance admission.

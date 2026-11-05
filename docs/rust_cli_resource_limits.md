# Rust CLI resource supervision (QOO-156) — integration candidate

**Status: staging only. NOT merged into dev/main. Final-source interim hosted CLI-cost pilot PASSED its provisional engineering budget; CodSpeed Macro unavailable and not claimed.**

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

## External signals, sudden parent death and fail-closed OOM

The native POSIX supervisor now traps **SIGINT** and **SIGTERM**. It wakes
within a bounded receive interval and performs the normal worker-tree
termination and reaping path. Before successful result publication it checks
again for a pending signal, returning exit **130** for SIGINT or **143** for
SIGTERM and **no partial scientific stdout**. This is a CLI control-plane
operation, not a cooperative cancellation check inside Path-sum.

For **Linux only**, the direct worker also installs
`PR_SET_PDEATHSIG(SIGKILL)` before exec, with a parent-PID race check.
This covers abrupt supervisor death for the **direct worker** but not
arbitrary daemonized solver grandchildren outside its process group.
**SIGKILL cannot be caught or cleaned up synchronously by the supervisor.**
For guaranteed whole-job teardown under forced parent death, use a
separately managed Linux container/job cgroup that constrains the whole CLI
invocation (independent of the optional internal `--max-memory-mib`).

On **macOS**, signal cancellation and deadline cleanup have focused
tests with a real detached-session `sleep` child while its worker is alive.
macOS cannot claim Linux subreaper, PDEATHSIG or cgroup-v2 semantics:
orphan/daemon escape after worker exit and forced supervisor SIGKILL remain
**outside the guaranteed whole-descendant cleanup contract**. Never
advertise this behavior as complete macOS process-tree containment.

If `--max-memory-mib` is requested, a missing/unreadable/malformed
`memory.events` or `oom_kill` field is a typed
`ResourceSupervisorError` (exit **125** with no successful stdout), **not**
`oom_kill=false`. This check runs only in the explicitly capped Linux
CLI path and does not modify the native RR/WMC calculation path.

## Source-pinned P0 and final-stage P1 admission — 2026-11-05

The final P0 control-plane code (Unix SIGINT/SIGTERM cancellation, Linux
direct-worker `PR_SET_PDEATHSIG`, fail-closed Linux `memory.events`, detached
session helper timeout/cancel tests) was validated at experiment source
`5930fdfbf8161b436614d819fcc1dddc1ff94445` on
[scoped native Linux/macOS #41940690787](https://github.com/PhysicsQoo/QuPRS/actions/runs/41940690787):
**Ubuntu24.04 9 unit + 17 integration**, **macOS14 ARM64 7 unit + 13
integration**, both **Release build PASS**. The exact supervisor and test
file blobs were then copied to [clean staging source
`61460ebe60fde8768abfbfd4422e9e953d2db158`](https://github.com/PhysicsQoo/QuPRS/commit/61460ebe60fde8768abfbfd4422e9e953d2db158);
native `rust/pathsum` remains source-identical to `dev`.

[Final-source hosted ABBA #41941084754](https://github.com/PhysicsQoo/QuPRS/actions/runs/41941084754)
**SUCCESS**, [raw artifact #13376437268](https://github.com/PhysicsQoo/QuPRS/actions/runs/41941084754/artifacts/13376437268).
Exact same-runner paired extra CLI latency: Single H **+1.579 ms** (95%
bootstrap CI [1.565,1.587]), GHZ32 RR **+1.558 ms** ([1.545,1.572]),
QPE8 RR **+1.502 ms** ([1.493,1.513]); 30 alternating ABBA/BAAB
blocks/case. All three are within the **3.0 ms provisional additive safety
overhead budget**, not a claim of zero regression or CodSpeed Macro equivalence.
The 3 ms engineering envelope still requires explicit release acceptance.
Neither `dev` nor `main` was merged by this evidence.

## Source and qualification

Only CLI code, exact workspace lockfile, focused tests, a single CodSpeed CLI benchmark and this file were copied from the [QOO-156 experiment branch](https://github.com/PhysicsQoo/QuPRS/tree/experiment/qoo156-internal-cgroup-p0). No experimental Docker OOM scripts, upstream Solver source, full CI matrices or native Rust RR/CNF changes are included.

- Linux x86-64 delegated cgroup: [Actions #41857419941](https://github.com/PhysicsQoo/QuPRS/actions/runs/41857419941) PASS. Native Linux ARM64: [#41861084404](https://github.com/PhysicsQoo/QuPRS/actions/runs/41861084404) PASS, both with cap64MiB typed OOM and cap256MiB complete PathSum. These validate a *constructed* delegation, not ordinary host availability.
- Authentic GPMC `-mode=1` QFT16 high-cap science and low-cap PID-witnessed typed OOM within an internal cgroup: [#41858651234](https://github.com/PhysicsQoo/QuPRS/actions/runs/41858651234) scoped subcases PASS; overall workflow FAIL because a separate natural Ganak low-cap PID was not witnessed.
- Authentic Ganak 2.8 `--mode=6` VQE4 high-cap complete science and artificial pressure under the **same CLI-owned** internal cgroup with real PID pre-witnessed: [#41860226028](https://github.com/PhysicsQoo/QuPRS/actions/runs/41860226028) PASS. This is **not Ganak natural memory minimum**; historical 64/70MiB runs retain NOT_ADMITTED solver-victim attribution.
- Final EOF-timestamped CLI source was verified on the **actual native macOS 14 ARM64 runner** (GitHub image `macos-14-arm64`, `Darwin arm64`) alongside Ubuntu 24.04 x86-64: [#41927422324](https://github.com/PhysicsQoo/QuPRS/actions/runs/41927422324) **SUCCESS**, exact source commit `9e2246f8b9f5e1e070a6c6deab0d36b99f24fcf1`. macOS 7 unit + 10 integration tests PASS, Ubuntu 8 unit + 13 integration tests PASS, both release compiles PASS. The staged `rust/cli/src/supervisor.rs` blob is copied byte-for-byte from that tested source; all other staged CLI scientific source files remain the earlier tested originals. This is **macOS 14 Apple Silicon**, not macOS 15, and NOT OrbStack Linux ARM64.
- Prior scoped Linux/macOS14 CLI package test: [#41857895087](https://github.com/PhysicsQoo/QuPRS/actions/runs/41857895087) PASS. MacOS15 arm64 workflow [#41858819331](https://github.com/PhysicsQoo/QuPRS/actions/runs/41858819331) was cancelled before runner assignment in both attempts; **not a macOS15 code failure and not a PASS**.
- The [source-paired Macro workflow](https://github.com/PhysicsQoo/QuPRS/blob/staging/qoo156-cli-resource-admission/.github/workflows/qoo156-cli-macro-pr-admission.yml) now supports an **opt-in staging push before a dev PR**, as well as a source-impacting dev PR. A repository administrator must first provision the actual Macro runner and set `QOO156_MACRO_ENABLED=true`; without the variable the [staging run #41927682370](https://github.com/PhysicsQoo/QuPRS/actions/runs/41927682370) correctly reports **SKIPPED**, not a performance PASS. The same test records exact dev/base and staging/HEAD SHA and requires identical native Rust Path-sum tree. Never mistake an unassigned/queued or skipped job for formal CodSpeed admission.
- **Approved measurement instrument for this QOO-156 interim pilot is source-paired, same-runner hosted ABBA/BAAB WallTime, not a CodSpeed Macro substitute in precision.** The [method and provisional budget](../research/qoo156_cli_supervisor/HOSTED_ABBA.md) are documented and implemented in [CI workflow](../.github/workflows/qoo156-cli-hosted-abba.yml) and [measurement script](../scripts/qoo156_cli_abba.py). Both complete Release CLIs run from exact Git SHAs on Ubuntu 24.04 x86-64, same `rust/pathsum` tree. Each of three RR-only cases has 8 warmups + 30 alternating 4-invocation blocks; byte-identical science output, sample/fixture/binary hashes and environment metadata are captured. Provisional 95% bootstrap upper-bound budget is **3.0 ms extra fixed CLI latency**, plus median pair jitter <=1.5 ms; this explicitly allows some safety-wrapper overhead, **not zero regression**.
- [GitHub Actions #41930775591](https://github.com/PhysicsQoo/QuPRS/actions/runs/41930775591) **SUCCESS** at source [a2b997c](https://github.com/PhysicsQoo/QuPRS/commit/a2b997c156aa9bebc08db485768e03fbab0d3d28) and [raw artifact #13372131499](https://github.com/PhysicsQoo/QuPRS/actions/runs/41930775591/artifacts/13372131499). Exact paired median extra CLI cost: **Single H +1.331 ms** (95% bootstrap CI [1.311,1.387]), **GHZ32 +1.297 ms** ([1.289,1.335]), **QPE-exact8 +1.596 ms** ([1.309,1.683]). Same-variant paired control jitter medians <=0.069 ms. All cases `WITHIN_PROVISIONAL_FIXED_COST_BUDGET`; full stdout science hashes agree. This is a **one-run, shared-host observation**; variation between different runners or days is not certified, and the budget is subject to release review.
- Prior connected official CodSpeed hosted, non-Macro [run 6aeb4b9d](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aeb4b9d09f1ddb2bf501af8) independently observed roughly +1.19–1.20 ms fixed CLI overhead on earlier source and is **OBSERVATIONAL_ONLY**. The [Macro queue #41825389124](https://github.com/PhysicsQoo/QuPRS/actions/runs/41825389124) remained unassigned/source-stale; the [staging Macro workflow](../.github/workflows/qoo156-cli-macro-pr-admission.yml) remains opt-in/off. **Do not block this interim QOO-156 pilot on unknown Macro runner provisioning**, and do not generalize this exception to the project's formal CodSpeed requirements for native RR/WMC algorithmic performance.

Do not trigger full CodSpeed/release matrices on Markdown-only modifications. The bounded additive CLI cost pilot now supports an integration review decision without Macro, but the **3 ms provisional release envelope must be explicitly reviewed** and Mac mini/OrbStack cgroup delegation remains a separate deployment-specific gate. A draft PR does not itself establish acceptance.

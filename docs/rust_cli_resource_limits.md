# Rust CLI resource supervision (QOO-156) — integration candidate

**Status (2026-11-05): PR #144 is OPEN and unmerged. Exact tested code `df0a554bf` passed all required 12-platform Native, CodSpeed (9 required jobs), Python, Dev Fast, Docker and same-runner hosted ABBA checks. The +3 ms additive CLI budget is provisional and not maintainer-approved; CodSpeed Macro is SKIPPED/not certified. Documentation-only revisions do not constitute new Rust/Python code admission. See [current PR review](../research/qoo156_cli_supervisor/PR144_REVIEW.md).**

## Contract

The Rust executable supervises a separate worker from before QASM loading. The default `--timeout 600` is monotonic and covers both single/dual CLI modes. On a timeout, exit is **124**; `--quiet` emits `Timeout`, not a verification verdict. Completion/cleanup or publishing to a blocked downstream consumer may extend beyond the deadline: not a hard real-time guarantee. No Rust pathsum library fast-path changes are included.

Parent captures stdout and stderr concurrently with an active 16MiB per-stream limit. The worker cannot publish partial EQ/NEQ before successful completion; output-limit/resource failures exit **125**. The internal `--__quprs-worker` launch requires a parent and inherited admission pipe (misuse-resistant, not a same-user security sandbox). Legitimate external solver errors remain errors.

`--max-memory-mib MIB` is **opt-in physical memory control** ONLY on Linux with a writable delegated cgroup v2. The supervisor must live in a leaf sibling of the worker under an **empty memory-enabled delegated ancestor**, respecting the cgroup v2 no-internal-process rule. The CLI joins the worker to its own `memory.max`/`memory.oom.group=1` cgroup before exec, verifies exact cap readback, and returns typed `MemoryLimitExceeded` (exit **125**, no scientific verdict) for observed cgroup OOM. Without delegation, the command fails closed rather than running without the requested physical cap.

`--max-address-space-mib` instead uses Unix RLIMIT_AS, bounding virtual address space, **not physical RSS**; it must not be silently substituted for the physical cap. A nonzero worker exit while RLIMIT_AS is active may be ENOMEM or a normal solver error; the supervisor cannot distinguish the two from an OS counter. The public exit classification is unchanged, but **failed-CNF opt-in retention is refused for such ambiguous capped failures**. Native macOS lacks Linux cgroup-v2, so `--max-memory-mib` is unsupported there. Native macOS also lacks the Linux child-subreaper guarantee for detached solver grandchildren.

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

If `--max-memory-mib` is requested, `memory.events` must provide valid, distinct `oom` **and** `oom_kill` counters. A positive **either** counter means observed resource OOM (exit **125**, no scientific verdict), including a kernel OOM allocation failure without a killed task (`oom>0`, `oom_kill=0`). A positive `max` pressure counter **alone** is not an OOM: successful reclaim may allow science to complete. Missing/unreadable/malformed or duplicate mandatory fields are typed `ResourceSupervisorError` (exit **125**, no successful stdout), not silently treated as zero. These checks run only in the explicitly capped Linux CLI supervisor and do not modify the native RR/WMC calculation path. Linux kernel semantics: [cgroup v2 memory.events](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html).

## P1: parent-owned solver temporary files and verified cgroup removal

The CLI supervisor creates an independent **mode-0700 temporary directory for
each invocation** and passes its path as **worker-only** `TMPDIR`. Native
Path-sum WMC creates `temp_eqcheck_*.cnf` and
`quprs-solver-*.tmp` using `std::env::temp_dir()`; the parent
therefore owns the containing directory even when SIGKILL prevents the worker
from running Rust destructors. After the worker and observable descendants
are reaped, the supervisor removes the directory **before publishing
successful stdout**. A removal error is typed
`ResourceSupervisorCleanupError` (exit **125**, no scientific verdict).
Existing `QUPRS_KEEP_FAILED_CNF=1` preserves the **mode-0700** private directory **containing only regular `temp_eqcheck_*.cnf` files** on an **ordinary uncapped worker failure**, not on any failure under `--max-memory-mib` or `--max-address-space-mib`. Linux `memory.events.oom=0` is not a complete negative witness: some allocation failures do not invoke the OOM killer or increment the counter. Even a worker that fails normally with `oom=0` and `oom_kill=0` therefore does **not** retain CNF when a memory cap is requested. Unrelated solver captures, nested directories and symlinks are removed without following symlinks. Timeout, signals, any capped failed worker, and success never preserve CNF. The existing uncapped opt-in debug mode is unchanged. Cleanup errors fail closed without publishing a scientific result.

For Linux `--max-memory-mib`, the supervisor now reads the final
`memory.events` OOM witness, checks `cgroup.events populated`, kills
any remaining worker-cgroup tasks, and retries `rmdir` for at most one
second. Missing/malformed controller evidence or an unremoved worker cgroup
returns **125** with a cleanup error. If the explicit cgroup cleanup fails, the supervisor **still invokes private TMPDIR cleanup explicitly** with retention disabled before returning exit125, reporting any secondary filesystem cleanup error. The `Drop` fallback remains a last resort and is **not** a guarantee when unkillable descendants remain. This extra controller check occurs only when the physical cgroup memory cap was requested.

[Independent source-scoped P1 CI #41942991745](https://github.com/PhysicsQoo/QuPRS/actions/runs/41942991745)
**SUCCESS**: Ubuntu24.04 x86-64 **11 unit + 20 integration + Release**,
native macOS14 ARM64 **8 unit + 16 integration + Release**. Tests
actually killed a worker holding both temporary filename families and
confirmed no residual parent-owned directory after timeout/SIGTERM;
explicit failed-CNF opt-in remained testable. In a separate isolated
test-only privilege-assisted cgroup v2 environment, **unprivileged
UID65534** CLI verified **64 MiB kernel OOM, exit125, no stdout** and
**256 MiB valid science, exit0**; the kernel worker cgroup was **absent
at CLI return in both cases**. The privileged container bootstraps the
test delegation only; it does not authorize privileged production CLI.

**Limits:** If the supervisor itself receives an uncatchable SIGKILL, its
cleanup cannot execute; the host/container process manager must own
whole-job lifetime and residual temporary-directory housekeeping.
macOS cannot claim Linux cgroup/subreaper behavior, and arbitrary solver
processes ignoring TMPDIR are outside this scoped temp-file contract.
The provisional **3 ms** source-paired hosted CLI overhead budget
**passed on the earlier source `56c8205`** at [Actions #41943543958](https://github.com/PhysicsQoo/QuPRS/actions/runs/41943543958)
and [raw artifact #13377816518](https://github.com/PhysicsQoo/QuPRS/actions/runs/41943543958/artifacts/13377816518).
Exact paired median extra CLI latency vs pinned dev: **Single H +1.961 ms**
(95% bootstrap CI [1.949,1.991]), **GHZ32 RR +1.954 ms**
([1.933,1.980]), **QPE8 RR +1.877 ms** ([1.862,1.895]).
All are **within the predeclared provisional +3ms absolute overhead budget**,
but this is not a zero-regression or CodSpeed Macro certification; formal
release acceptance remains a distinct decision.

## 2026-11-05 OOM-event and RLIMIT_AS retention safety qualification

- Isolated test source: [experiment/qoo156-oom-events-rlimit-retention@8b456a5](https://github.com/PhysicsQoo/QuPRS/commit/8b456a52f45ec2fce9a3813cf59008f5ddac66af). [Actions #41954784814](https://github.com/PhysicsQoo/QuPRS/actions/runs/41954784814) **three jobs SUCCESS**: Ubuntu24.04 full CLI package unit/integration + Release, macOS14 ARM64 same, and Linux non-root UID65534 real delegated cgroup positive test. Test-only privileged Docker created cgroup delegation; no production privileged CLI or Docker harness was transferred.
- **64 MiB true kernel OOM:** `oom=1`, `oom_kill=2`, worker exit125, empty stdout, no retained private CNF despite opt-in, worker cgroup removed; **256 MiB complete science:** `oom=0`, `oom_kill=0`, worker exit0, valid output and no residual worker cgroup. [Raw evidence artifact #13382318866](https://github.com/PhysicsQoo/QuPRS/actions/runs/41954784814/artifacts/13382318866).
- Pure parser tests additionally cover `oom>0,oom_kill=0` (fail closed), `oom=0,oom_kill>0`, positive `max` alone (not OOM), absent/duplicate/malformed fields; the **no-kill OOM counter combination was synthetically unit tested, not physically induced in this workflow**. RLIMIT_AS + explicit failed-CNF opt-in has focused Unix integration coverage; normal uncapped opt-in remains supported.
- Same-runner hosted ABBA for earlier fully tested `e6956a7` [#41952943600](https://github.com/PhysicsQoo/QuPRS/actions/runs/41952943600) passed provisional +3 ms additive cost: Single H +2.096 ms, GHZ32 RR +2.085 ms, QPE8 RR +2.048 ms. Full native 12-platform and CodSpeed [#41952952980](https://github.com/PhysicsQoo/QuPRS/actions/runs/41952952980) / [#41952952986](https://github.com/PhysicsQoo/QuPRS/actions/runs/41952952986) succeeded on that earlier source. **Any newly staged **code-changing** SHA requires its own integration CI; Markdown-only edits can reuse previously verified code evidence under the CI source-impact policy.** No CodSpeed Macro PASS or zero-regression claim.

## 2026-11-05 P1 final capped-failure and exceptional-cleanup admission

* Upstream [Linux cgroup-v2 `memory.max` and `memory.events` documentation](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html) explicitly notes that some failed allocations do **not** invoke the OOM killer, and `oom` is not always raised. A failed CLI request under a physical `memory.max` cap can therefore have `oom=0, oom_kill=0`. The CLI now withholds `QUPRS_KEEP_FAILED_CNF=1` retention for **all capped worker failures**, independent of those observed counters. This is an intentional loss of opted-in CNF diagnosis under memory caps in exchange for fail-closed cleanup; **uncapped ordinary failed-solver debugging remains enabled**.
* [Source-scoped pilot `bdc3b2e48`](https://github.com/PhysicsQoo/QuPRS/commit/bdc3b2e48eb2563669e5be61ed444a008097e0f1), [Actions #41957629230](https://github.com/PhysicsQoo/QuPRS/actions/runs/41957629230) **ALL THREE JOBS PASS**: complete CLI unit/integration and Release on Ubuntu24.04 and native macOS14 ARM64; test-only Docker-delegated cgroup + **unprivileged UID65534 CLI** real Linux positive cases:
  * 64 MiB real OOM: `oom=1,oom_kill=2`, exit125, no science stdout, retained CNF **false**, worker cgroup removed.
  * 256 MiB **ordinary failed request** (missing QASM) with explicit retention opt-in: `oom=0,oom_kill=0`, exit1, no science stdout, **private CNF deleted**, worker cgroup removed.
  * 256 MiB successful science: `oom=0,oom_kill=0`, exit0, valid Path-sum output, worker cgroup removed.
* Exceptional cgroup cleanup error now **explicitly attempts** private-TMPDIR disposal without retention and reports any second cleanup error before exit125. A synthetic non-kernel controller error and private files are unit-tested; an **unkillable real cgroup failure was not reproduced**. This is an improved guaranteed *attempt*, **not** a proof of successful filesystem cleanup in every unrecoverable kernel state. No worker-science code was changed; this protection runs only on the error path and introduces no added process or algorithm hot-path instrumentation.
* Experimental privilege-assisted Docker, Python pilot, and workflow belong exclusively to the research branch; none are for production deployment or staging integration. A new code-changing staging HEAD needs SHA-specific CI/ABBA; docs-only updates preserve qualified executable provenance.

## Adopted-child cleanup error path — isolated Linux qualification

The parent checks and reaps adopted worker descendants **before** explicit
kernel-cgroup and private-TMPDIR disposal. If the adopted-child cleanup
routine itself fails, the supervisor now takes an **exception-only** path:
terminate the remaining worker process group, attempt cgroup cleanup if
available, **explicitly attempt private TMPDIR removal without CNF
retention**, report any secondary cleanup errors, then return a typed
resource error (exit **125**, with **no scientific stdout**).
This is stricter than returning an untyped Rust `Result` error and relying
only on destructors. Destructors still provide last-resort best effort;
**a genuinely unkillable kernel/daemon child remains outside a universal
filesystem-removal guarantee**.

[Isolated branch commit `dd7f263d`](https://github.com/PhysicsQoo/QuPRS/commit/dd7f263d6246fbbfc0379870ae7a74c6d3cc0558)
and [focused Linux Actions #41959156390](https://github.com/PhysicsQoo/QuPRS/actions/runs/41959156390)
**SUCCESS**: CLI 13 unit tests; debug-only post-worker cleanup failure
integration **1 PASS** asserting exit125, no scientific stdout, no CNF
retention even with `QUPRS_KEEP_FAILED_CNF=1`, no residual private
directory; ordinary uncapped opt-in and forced timeout focused controls
both **PASS**; Release build **PASS** and test-injection marker absent.
This uses **synthetic exception injection**, not a real unkillable kernel
cgroup. The debug-only injection is not compiled into Release. No native
`rust/pathsum`, solver, or worker-science implementation changes.

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

## Current tested code-head admission and merge policy
 At [`df0a554bf`](https://github.com/PhysicsQoo/QuPRS/commit/df0a554bf936b836769f72db27eb816bee4cb730), [Native 13/13 #41964905814](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964905814), [CodSpeed 9 required PASS / 11 optional skipped #41964905799](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964905799), [Python #41964905770](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964905770), [Dev Fast #41964905787](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964905787), and [Docker #41964905768](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964905768) all succeeded. [Hosted ABBA #41964899052](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964899052) passed the provisional +3 ms budget with Single H +2.136 ms, GHZ32 RR +2.068 ms and QPE-exact8 RR +2.073 ms; exact dual-circuit EQ guards 18/18 PASS. Only the baseline/HEAD **full-output parity** and a structural marker are checked for Single H; this is not an independent state oracle. Maintainer +3 ms policy acceptance and independent review are still outstanding. CodSpeed Macro and Mac mini/OrbStack delegated-cgroup qualification are not established.

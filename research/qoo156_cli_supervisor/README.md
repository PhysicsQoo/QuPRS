# QOO-156 — Rust CLI outer process supervisor (experimental)

Base source: `dev@79e975b0b21c0c650db7a76fe6e35b926c67c2c8`.
Branch: `experiment/qoo156-cli-supervisor`. No changes to the native `rust/pathsum` library.

## Resource contract

- CLI parent process parses flags only, then spawns the same Rust executable as an internal worker. The worker performs QASM input, miter/pathsum, RR, Hybrid, WMC and rendering.
- Parent's monotonic `--timeout` starts before worker startup and QASM parsing, applies to single- and dual-circuit CLI modes and cancels the worker on timeout. Timeout reports `Timeout` in quiet mode and exits 124; worker errors cannot publish partial success stdout.
- Parent waits for an OS exit event via a blocking wait thread (no 20ms polling tail) and buffers the child's stdout and stderr in anonymous files (max 16 MiB committed stdout). On a successful worker exit, the parent publishes the complete output; otherwise error diagnostics only. Parent worker-exit and OOM are not silently mapped to EQ/NEQ.
- Linux `--max-memory-mib` is explicitly hard-cgroup-v2-only. A writable/delegated cgroup is required; otherwise abort before worker start. It sets `memory.max`, `memory.oom.group`, and uses an async-signal-safe `pre_exec` write to `cgroup.procs` BEFORE the worker executable starts (including loader/QASM allocations); on timeout attempts `cgroup.kill`. The parent retains the writable descriptor until `Command::spawn` finishes. **Positive delegated-cgroup/OOM evidence still required**: hosted Linux CI commonly denies cgroup delegation. No unsupported host is silently treated as memory-limited.
- Unix `--max-address-space-mib` sets `RLIMIT_AS` in the worker's pre-exec hook. This is a virtual-address limit, **not** an RSS/physical-memory limit; it must never be silently advertised as `memory.max`.
- Without a writable cgroup, best-effort descendant enumeration + Unix process-group kill is used to terminate the worker tree. A subprocess that re-sessions at exactly the wrong time may evade a snapshot. The Linux unit suite now explicitly exercises a detached solver-like process group; no race-free unconfined descendant guarantee yet without a cgroup/other OS containment primitive. Existing solver-specific QOO-6 child supervision remains unchanged.

## Scoped execution

[Linux and macOS CI #41815417254](https://github.com/PhysicsQoo/QuPRS/actions/runs/41815417254) PASS:

- Rust CLI unit tests 6/6 on each platform.
- Experimental integration tests 7/7 Linux, 6/6 macOS (including deterministic debug-only timeout during pre-QASM worker initialization, single/dual modes, no partial success output, insufficient resource limit error, worker process-group cleanup).
- Release compilation passes both targets.

## Performance admission

The Rust algorithm implementation `rust/pathsum` is intentionally identical to `dev` for this experiment. Native algorithmic CodSpeed CPU Simulation regression from this branch is **not expected**, but the new CLI is not free: process creation, context switching, spooled I/O, polling and result forwarding add fixed costs.

[First source-paired CodSpeed WallTime #41815845054](https://github.com/PhysicsQoo/QuPRS/actions/runs/41815845054) measured unchanged dev CLI (1.4–3.1ms) vs initial 20ms-polled supervisor (22.0–22.2ms) vs direct HEAD worker (1.4–3.1ms), source pinned same runner, hosted WallTime **observation only**. This confirmed the fixed 20ms polling tail, not a Rust computational regression. The parent has since moved to event-driven worker wait; new paired CodSpeed data is required. External Macro Runner admission remains open.

## Evidence update (2026-11-04)

- [Linux/macOS scoped CI #41822076967](https://github.com/PhysicsQoo/QuPRS/actions/runs/41822076967) PASS: runtime and unit/integration tests. The **new positive OOM test** prints `QOO156_MEMORY_POSITIVE_NOT_ADMITTED` on hosted Ubuntu 24.04, where writable delegated cgroup v2 is absent. This is a *correct fail-closed result*, not proof of memory.max enforcement.
- [CodSpeed same-runner observational WallTime #41817512390](https://github.com/PhysicsQoo/QuPRS/actions/runs/41817512390): event-driven supervisor adds approximately **1.5–2.7 ms** over the unchanged dev CLI. Direct HEAD worker matches the dev native algorithm behavior. The new process isolation has a significant relative cost for 1–3 ms jobs; a near-constant few milliseconds can be relatively small for long requests. CodSpeed explicitly warns this hosted run is not a Macro Runner, so no performance admission is claimed.
- [Real solver attempt #41822744791](https://github.com/PhysicsQoo/QuPRS/actions/runs/41822744791) and [debugging run #41823482984](https://github.com/PhysicsQoo/QuPRS/actions/runs/41823482984): both **NOT_ADMITTED**. GPMC wrapper launched a child but SIGSTOP arrived **before exec**, when `/proc/<pid>/exe` still resolved to `/usr/bin/dash`; CLI did return Timeout without observed live orphan, but this does not certify a real GPMC executable was canceled. Ganak ran its actual pinned binary and returned a verdict, yet its mode-6 counting process had already exited before a controlled freeze was observed. Both remain open. The current pilot requires actual GPMC ELF `/proc/<pid>/exe` before pausing and never credits Ganak preflight in place of mode-6 counting.
- No source or release changes were merged to `dev`/`main`. No strict memory guarantee on macOS or nondelegated Linux is claimed.

## Ganak forced-cancellation evidence correction (2026-11-04)

- [Actual pinned Ganak mode-6 experiment #41828065057](https://github.com/PhysicsQoo/QuPRS/actions/runs/41828065057) successfully observed the unmodified, **statically linked** Ganak executable (`sha256=934a79a3...`), verified `--mode=6` argv and CLI descendant ancestry, and SIGSTOP'ed the genuine solver PID on VQE4, QAOA7, Graphstate16 and QFT16. CLI returned Timeout/124 in all four cases. **However, the original claim that all four solvers leaked was wrong.** The test's `still_active()` helper incorrectly returned True on `psutil.NoSuchProcess` as well as AccessDenied, so its `live_orphan_after_cli=true` field could mark successfully removed processes as survivors.
- [Focused process-parentage run #41830778778](https://github.com/PhysicsQoo/QuPRS/actions/runs/41830778778) captured before/after snapshots of a stopped Ganak mode-6 process: immediately after CLI exit124, and again after three seconds, the original PID was **NoSuchProcess**. This directly contradicts the false orphan claim. **Treat every earlier `live_orphan_after_cli=true` value as invalid evidence, not a proven leak.** The timeout and exact real-Ganak process identities remain valid.
- [Test bug fix `eacf649`](https://github.com/PhysicsQoo/QuPRS/commit/eacf64952be78724959007454c1c783a5de29ce5) correctly classifies `NoSuchProcess` and `ZombieProcess` as terminated, and treats AccessDenied conservatively as unverified. A separate self-test now explicitly guards the missing-PID behavior before replaying Ganak. Actual real-Ganak PASS requires a fresh run of this corrected harness.
- [Experimental Linux child-subreaper hardening `fe912f3`](https://github.com/PhysicsQoo/QuPRS/commit/fe912f3be7300eac4552372089dad39fe7295e08) passed synthetic exited-worker/detached-solver CI [#41829351680](https://github.com/PhysicsQoo/QuPRS/actions/runs/41829351680), but **must not be credited as a demonstrated fix for real Ganak leaks**, because those leak observations were erroneous. The subreaper may still protect against legitimate orphan races but needs independent admission and CodSpeed overhead measurements before merge.

## Static Ganak ELF provenance

- [Read-only pinned Ganak ELF audit #41827070084](https://github.com/PhysicsQoo/QuPRS/actions/runs/41827070084): 2.8.0 Linux x86-64 binary `sha256=934a79a3...` **statically linked, without PT_INTERP or DT_NEEDED**. Consequently `LD_PRELOAD` constructors cannot instrument this binary. All earlier LD_PRELOAD tests were NOT_ADMITTED and are not proof of cancellation behavior.

## Remaining acceptance

1. Confirm event-driven CodSpeed CLI overhead across short and realistic workloads; hosted WallTime is non-Macro observational until fixed runner acceptance.
2. Rerun the corrected true Ganak mode-6 stopped-process test. Do not treat earlier false orphan flags as failures. Keep GPMC actual cancellation PASS separately, assess Linux subreaper benefit and macOS process-tree containment.
3. Positive physical-memory enforcement test on a delegated Linux cgroup, forced OOM, cgroup event provenance, and process-start containment confirmation. Pre-exec placement is now implemented but lacks a delegated-runner positive gate.
4. Repeat science and performance gates on final source SHA. Do not merge or release from this experimental branch until admitted.

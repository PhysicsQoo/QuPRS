# QOO-156 — PR #144 scoped integration review (2026-11-05)

## Latest findings and scope

- This is the clean QOO-156 PR [#144](https://github.com/PhysicsQoo/QuPRS/pull/144) targeting `dev`. No source or algorithm changes under native `rust/pathsum`; only Rust CLI supervisor/arguments/dependencies, tests, benchmark scope, research reports and relevant docs. Neither `dev` nor `main` has been merged.
- The previous code HEAD `e6956a7f99720d9706833aa58fe311b00672999a` has **all required formal CI PASS**: [native 12-platform #41952952980](https://github.com/PhysicsQoo/QuPRS/actions/runs/41952952980), [five-shard / Rust CPU / solver-inclusive / cross-instrument CodSpeed #41952952986](https://github.com/PhysicsQoo/QuPRS/actions/runs/41952952986), Dev Fast, Python CI and Docker. [Hosted ABBA #41952943600](https://github.com/PhysicsQoo/QuPRS/actions/runs/41952943600) also PASS under the **provisional +3ms additive CLI budget**, with new-source paired overhead Single H +2.096ms, GHZ32 RR +2.085ms and QPE8 RR +2.048ms. These are not zero regressions and not CodSpeed Macro certification.
- Current `c201a51969430fc9870ac9bb1bd77b7c5e20fb61` **has all required CI PASS**: [Native 12/12 #41955447323](https://github.com/PhysicsQoo/QuPRS/actions/runs/41955447323), [five-shard + Rust CPU + solver-inclusive CodSpeed #41955447264](https://github.com/PhysicsQoo/QuPRS/actions/runs/41955447264), Dev Fast/Python/Docker PASS, [source-paired ABBA #41955439091](https://github.com/PhysicsQoo/QuPRS/actions/runs/41955439091) provisional +3ms PASS (Single H +1.623ms, GHZ32 RR +1.607ms, QPE8 RR +1.593ms). CodSpeed Macro is SKIPPED and must not be claimed as certified. This `c201a519` proof becomes **previous-HEAD evidence** once a new staging code commit is made.

## P0/P1 safety corrections

1. Whole-call timeout, worker process/tree cancellation, bounded 16MiB stdout/stderr, fail-closed scientific result publication and Linux cgroup memory.max are the existing verified control-plane implementation. SIGINT/SIGTERM exits 130/143; timeout 124; resource failures 125.
2. Confirmed kernel `oom_kill` and unreadable evidence block `QUPRS_KEEP_FAILED_CNF=1` on resource failures. [Real Linux/macOS + privileged-test-only cgroup pilot #41950595305](https://github.com/PhysicsQoo/QuPRS/actions/runs/41950595305) PASS (64MiB kernel OOM with opt-in had no remnant; 256MiB valid science).
3. On an ordinary opted-in failed solve, preserve only regular matching `temp_eqcheck_*.cnf` files; remove solver output captures and unrelated entries. [Scoped Linux/macOS pilot #41952489722](https://github.com/PhysicsQoo/QuPRS/actions/runs/41952489722) PASS; minimal fix landed as [e6956a7](https://github.com/PhysicsQoo/QuPRS/commit/e6956a7f99720d9706833aa58fe311b00672999a).
4. **New finding:** Linux `memory.events.oom` can record cgroup allocation failure even when `oom_kill=0`; the previous supervisor only checked `oom_kill`, permitting a resource failure to be classified as ordinary worker failure. Corrected predicate requires independently valid `oom` and `oom_kill`, treats either nonzero as resource OOM; `max` pressure alone is NOT OOM. Reference: [upstream cgroup v2 documentation](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html).
5. **New finding:** `RLIMIT_AS` cannot provide unambiguous per-invocation ENOMEM status. For an explicitly address-space-capped worker with a nonzero exit, failed-CNF opt-in is now withheld conservatively. This preserves the existing public worker exit classification and uncapped debug behavior.

## Exact source pilot for new OOM/RLIMIT boundary

[Experiment `8b456a52`](https://github.com/PhysicsQoo/QuPRS/commit/8b456a52f45ec2fce9a3813cf59008f5ddac66af) and [Actions #41954784814](https://github.com/PhysicsQoo/QuPRS/actions/runs/41954784814) **ALL THREE JOBS SUCCESS**:
- Ubuntu24.04 Linux CLI complete package unit/integration + release build PASS.
- macOS14 native ARM64 CLI complete package unit/integration + release build PASS.
- Linux actual delegated cgroup under CLI UID65534 (test-only privilege-assisted Docker bootstrap): 64MiB cap `oom=1`, `oom_kill=2`, exit125, empty science stdout, no retained CNF, no worker cgroup; 256MiB cap `oom=0`, `oom_kill=0`, valid science exit0, no residual child cgroup. [Raw artifact #13382318866](https://github.com/PhysicsQoo/QuPRS/actions/runs/41954784814/artifacts/13382318866).
- Synthetic unit counter combinations also verify `oom>0,oom_kill=0` and `max>0,oom=0,oom_kill=0`. **Do not claim a genuine kernel no-kill OOM test; actual positive OOM had victim kills.** Unix RLIMIT_AS + opt-in fail cleanup is exercised in CLI integration tests.
- Experiment-only privileged Docker, Python pilot and workflow must **not** enter staging/production. Transfer only verified supervisor source, tests and updated docs/review.

## New P1 cap-failure and cleanup-error research pilot

- **Cause:** `memory.events.oom=0` and `oom_kill=0` cannot prove that all Linux memory-limit allocation errors are absent. Consequently the original cap-specific opt-in CNF retention condition was not universally safe; a cgroup-enabled failed worker with no recorded OOM could preserve CNF.
- **Minimal source-only policy:** If physical `--max-memory-mib` OR virtual `--max-address-space-mib` is requested, a nonzero worker exit never retains opted-in CNF, whether counters are zero, positive, or unreadable. Default uncapped ordinary failure retains only matching CNF files as before. No native RR/WMC/solver changes.
- **Failure-path cleanup:** Even when worker-cgroup `cleanup()` errors, explicitly attempt removal of private TMPDIR before exit125; show both resource and filesystem errors when appropriate. Hard unkillable kernel tasks and unexpected adopted-child cleanup errors remain outside an absolute artifact-lifetime guarantee.
- **Exact pilot `bdc3b2e48eb2563669e5be61ed444a008097e0f1`** [Actions #41957629230](https://github.com/PhysicsQoo/QuPRS/actions/runs/41957629230): Ubuntu24.04 full native CLI suite/Release PASS, native macOS14 ARM64 full suite/Release PASS, genuine delegated Linux cgroup CLI UID65534 three positive cases: 64MiB OOM `oom=1/oom_kill=2` exit125/CNF removed; 256MiB ordinary missing QASM `oom=0/oom_kill=0` exit1/CNF removed **despite opt-in**; 256MiB complete science exit0. In all cases no worker cgroup remains. Kernel cleanup-error injection is synthetic unit test, **not** a real unkillable cgroup witness.
- **Integrity:** transfer only `rust/cli/src/supervisor.rs` plus CLI resource contract and this review ledger; test-only Docker, Python pilot and workflow are not transferred. New staged exact SHA admission must run independently; no dev/main merge or automatic approval.

## Performance decision and other limits

- [Same-runner fixed-cost decomposition #41945871411](https://github.com/PhysicsQoo/QuPRS/actions/runs/41945871411): dev→P0 ~+1.53ms, P0→P1 +0.067–0.103ms; worker bootstrap dominates. Do not remove worker isolation/temporary boundary/bounded output for ~0.08ms savings. Native RR/WMC hot path remains unchanged.
- Maintainer must **explicitly** accept or reject provisional **+3ms fixed CLI startup overhead** before merge; high relative regression for tiny one-shot CLI calls is disclosed. Hosted ABBA is an interim method, not CodSpeed Macro; syscall-heavy CPU Simulation cannot prove complete CLI latency.
- SIGKILL of supervisor, arbitrary daemonized grandchildren on macOS, Mac mini/OrbStack real guest cgroup delegation and blocked/broken stdout consumer lifetime remain unproven; use an external whole-job manager for stronger guarantees.
- Remain Open / In Progress. New exact HEAD required CI + appropriate independent review + fixed-cost acceptance are the merge gates. **No auto-merge to dev/main.**

## Historical infrastructure triage (superseded)

An earlier PR attempt had CodSpeed HTTP 503 *upload* failures after benchmark computation, not scientific mismatch. Failed jobs alone were rerun successfully for their old SHA in [#41948355903](https://github.com/PhysicsQoo/QuPRS/actions/runs/41948355903). Current `e6956a7` already passed the full required set independently. Never restart full expensive native/CodSpeed jobs merely because Markdown-only evidence has changed.

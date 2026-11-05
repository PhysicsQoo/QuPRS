# QOO-156 — PR #144 scoped merge-review (2026-11-05)

## Scope and source integrity

- [PR #144](https://github.com/PhysicsQoo/QuPRS/pull/144) targets dev from clean staging/qoo156-cli-resource-admission.
- Initial audit: dev@79e975b0b21c0c650db7a76fe6e35b926c67c2c8, staging@97b96eba3301f153dec4358f88ce4c6580733263, 13 commits ahead, zero behind, 15 changed files, **native rust/pathsum unchanged**.
- The changed files are restricted to the Rust CLI control-plane, its Cargo direct dependencies, relevant benchmark fixtures/CI, tests, documentation and experiment report. No solver or native algorithm code change.
- PR is open, non-Draft, mergeable according to GitHub metadata but **has no approving reviews yet**. Do not interpret mergeability as CI or release approval.

## Reproducible prior P0/P1 evidence

- [P0 Linux/macOS exact-source Actions #41940690787](https://github.com/PhysicsQoo/QuPRS/actions/runs/41940690787): source-specific scope PASS.
- [P1 Linux/macOS/tempdir/true nonroot cgroup OOM Actions #41942991745](https://github.com/PhysicsQoo/QuPRS/actions/runs/41942991745): three jobs PASS, including 64MiB genuine OOM/no stdout/no remaining worker cgroup.
- [P1 production-source hosted ABBA #41943543958](https://github.com/PhysicsQoo/QuPRS/actions/runs/41943543958): PASS *against a provisional +3ms additive budget*, no proof of zero regression; +1.9–2.0ms across three short RR cases. This is not CodSpeed Macro.
- [Same-runner fixed-cost attribution #41945871411](https://github.com/PhysicsQoo/QuPRS/actions/runs/41945871411): P0 roughly +1.5ms, P1 incremental +0.07–0.10ms; worker bootstrap dominates. Different runner observations are not subtracted.

## Concrete safety gap discovered at formal PR review and corrected

**Blocker in the original PR head**: supervisor preserved failed CNF when QUPRS_KEEP_FAILED_CNF=1 if a cgroup-OOM-killed worker exited nonzero with no explicit timeout/signal. The old predicate did not consider the final kernel memory.events OOM witness. This contradicted the documented rule that cancellation and OOM must not retain circuit artifacts.

**Minimal fix:** production CLI now uses a pure guard predicate that permits CNF preservation **only if** (a) explicitly opted in, (b) the worker has failed without timeout or signal, and (c) the OOM state is **known absent** (or no physical cgroup requested). A confirmed OOM or an unreadable/invalid kernel memory.events state is always fail-closed and removes the worker's private temporary directory. No change to native Rust pathsum/RR/WMC calculations or the supervisor's normal successful worker execution path.

- [Scoped fix experiment](https://github.com/PhysicsQoo/QuPRS/commit/d9abebbca1165945d0181a3bb9352ac8d90d54b8) contains the minimal source correction, unit test and **experiment-only** delegated cgroup harness.
- [Native Linux/macOS + actual kernel OOM experiment #41950595305](https://github.com/PhysicsQoo/QuPRS/actions/runs/41950595305) **ALL THREE JOBS SUCCESS**:
  - Ubuntu24.04 x86-64 12 unit + 20 integration, Release build PASS.
  - macOS14 Apple Silicon 9 unit + 16 integration, Release build PASS.
  - Non-root UID65534 actual delegated Linux cgroup, QUPRS_KEEP_FAILED_CNF=1 and debug-only fake CNF+Solver capture: 64MiB kernel OOM, oom_kill=2, CLI exit125, no successful stdout, no residual private TMPDIR (`oom_optin_private_temp_removed=true`), no residual worker cgroup. 256MiB valid science exit0, no residual worker cgroup. Test-only privileged Docker provides delegation; production CLI does not run privileged.
  - [Positive OOM raw evidence](https://github.com/PhysicsQoo/QuPRS/actions/runs/41950595305/artifacts/13380752372). The experimental Docker/pilot/workflow files MUST NOT be merged into staging.

## PR check triage

The initial PR-head Actions had all twelve native Python/Rust build matrix entries PASS; Dev Fast, Docker and Python CI PASS. Four CodSpeed-related jobs were FAIL because upload to CodSpeed returned **503 Service Unavailable**, with benchmark execution itself reported complete; the cross-instrument evidence aggregator then failed by design because upstream jobs failed. This is a transient result **upload** issue, not evidence that RR/WMC scientific outputs were wrong or that the CLI had a measured native regression.

Re-run **only failed CodSpeed workflow jobs** through [Actions #41948355903](https://github.com/PhysicsQoo/QuPRS/actions/runs/41948355903) (attempt 2), not previously passing twelve-platform or other CI. Only successful upload plus downstream aggregator may satisfy the original SHA. **Any source correction updates PR HEAD and must be evaluated against new HEAD checks**; do not use old pass statuses as final branch certification.

## Review status and decision gates

1. Preserve P0/P1 supervision, output isolation, signal cancellation, real kernel OOM fail-closed and bounded cleanup. Keep the minimal safety predicate correction.
2. Complete fresh PR HEAD required checks, including CodSpeed upload and evidence aggregator. 503 is infra, but a FAIL must not be silently accepted as green.
3. Require explicit maintainer decision on a **provisional additive +3ms CLI overhead** release envelope. Short single-shot CLI invocations suffer substantial relative regression, even though native Rust algorithm remains unchanged.
4. Never claim SIGKILL of the supervisor can be intercepted, arbitrary daemonized macOS descendants are contained, or Mac mini/OrbStack cgroup deployment is already certified. The final stdout commit is not hard real-time and not transactionally atomic to a broken consumer.
5. No merge to dev/main and no auto-merge until gates close.

**Disposition:** PR review in progress. The formerly open CNF/OOM safety defect has a scoped, independently CI-validated source fix ready for clean staging incorporation. Open release decisions and fresh integration SHA checks remain blocking.

# QOO-156 — PR #144 scoped integration review

> **Living source-of-truth for integration review.** Updated 2026-11-05.
> Tested **code HEAD**: [`df0a554bf`](https://github.com/PhysicsQoo/QuPRS/commit/df0a554bf936b836769f72db27eb816bee4cb730);
> base `dev@79e975b0b21c0c650db7a76fe6e35b926c67c2c8`.
> Subsequent **Markdown-only** review edits do not change the qualified CLI
> binaries, but their SHA must not be mistaken for newly executed source tests.

## Decision snapshot

- [PR #144](https://github.com/PhysicsQoo/QuPRS/pull/144): **OPEN, not merged, non-draft**; at tested code SHA, **20 commits ahead / 0 behind**, **17 changed files**. No edits under `rust/pathsum` or upstream GPMC/Ganak.
- **Science / resource / integration CI: all mandatory checks PASS at `df0a554bf`.** See exact-source evidence below.
- **Performance: provisional fixed +3 ms additive CLI budget PASS on hosted same-runner ABBA only.** Not zero overhead; not a CodSpeed Macro qualification; not a cgroup/GPMC/Ganak/OrbStack claim.
- **NOT approved for merge automatically.** Await independent maintainer source/risk review and explicit acceptance/rejection of the provisional +3 ms startup cost. This is **post-v0.14.0** work; the next release version is not assigned.

## Accepted implementation contract

| Area | Current code behavior | Boundary |
| --- | --- | --- |
| Deadline | Isolated worker with monotonic timeout spanning QASM load, worker exit and both stdout/stderr EOF; timeout exit **124**. | Cleanup grace and a blocked/broken downstream stdout may exceed requested deadline; not hard real-time. |
| Atomic science | Parent spools stdout/stderr concurrently, **16 MiB cap per pipe**, then publishes only on successful worker completion; capture/resource failure **125**. | No guarantee of transactional stdout delivery if the consumer breaks mid-copy. `--quiet` can print the non-science token `Timeout` with exit124. |
| Cancellation | Unix SIGINT **130** / SIGTERM **143**. Worker process-group kill; Linux direct worker PDEATHSIG and subreaper for adopted children. | Supervisor SIGKILL is uncatchable. Native macOS cannot guarantee collection of all orphaned daemon grandchildren. |
| Physical memory | Optional Linux delegated cgroup v2 `memory.max`, strict readback, `memory.oom.group`, `cgroup.events` cleanup, `memory.events.oom` **and** `oom_kill`. | No delegation → fail closed; `max>0` alone does not establish OOM; `oom=0` cannot rule out every allocation failure. |
| Virtual memory | Unix `--max-address-space-mib` uses `RLIMIT_AS`. | Not RSS; failure cause cannot be proven from a dedicated RLIMIT_AS exceeded counter. |
| Temporary files | Parent-owned mode-0700 per-request TMPDIR for WMC CNF and solver-output captures; explicit cleanup before science commit. | On exceptional cleanup, **attempt** disposal and typed exit125; unkillable tasks/SIGKILL cannot give universal reclamation guarantees. |
| Debug CNF | `QUPRS_KEEP_FAILED_CNF=1` retains **only regular `temp_eqcheck_*.cnf`** on ordinary **uncapped** worker failure. | Never retains for timeout, signal, OOM, unknown witness, success, **any capped failure** (`memory.max` or `RLIMIT_AS`), or cleanup error. Other solver capture files are removed. |

Contract/details: [resource limits](../../docs/rust_cli_resource_limits.md), [P1 cleanup](P1_CLEANUP.md).

## Exact-code-head qualification: `df0a554bf`

| Evidence | Source-pinned conclusion |
| --- | --- |
| [Native Cross-Platform #41964905814](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964905814) | **13/13 jobs SUCCESS**, 12 OS/Python combinations. |
| [Official CodSpeed #41964905799](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964905799) | **9 required SUCCESS**, including five Simulation shards, native Rust CPU, paired Solver-inclusive WallTime and per-SHA evidence; **11 optional SKIPPED**. Solver-inclusive stage/science matrix **20/20 PASS** (per workflow evidence; do not substitute Ganak precision caveats with a blanket numerical certification). |
| [Python #41964905770](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964905770), [Dev Fast #41964905787](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964905787), [Docker #41964905768](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964905768) | **All SUCCESS.** |
| [Hosted ABBA #41964899052](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964899052) | **SUCCESS**, strict verdict guards **18/18** and source-paired, byte-identical stdout; paired additive median: Single H **+2.136 ms**, GHZ32 RR **+2.068 ms**, QPE-exact8 RR **+2.073 ms**. 95% bootstrap intervals respectively **[2.118,2.151]**, **[2.054,2.093]**, **[2.058,2.085] ms**. All below provisional +3 ms upper CI budget. |
| CodSpeed Macro | **SKIPPED / not provisioned**, not a PASS. |

The formal CI results above are **specific to the tested code HEAD**. Earlier commits' PASS and different hosted runner environments must not be silently pooled. Current PR code did not change after `df0a554bf` at this review; a later Rust/Python/benchmark edit requires its own source-specific checks.

## Review findings resolved in earlier isolated experiments

1. **Cgroup OOM missed without process kill.** Linux `memory.events.oom>0,oom_kill=0` can indicate failed allocation. Parser now validates both independently and returns resource125 for either positive; `max>0` by itself is only pressure. **The no-kill OOM combination was tested synthetically, not as a real kernel event.** [Source pilot `8b456a52`](https://github.com/PhysicsQoo/QuPRS/commit/8b456a52f45ec2fce9a3813cf59008f5ddac66af), [3/3 jobs #41954784814](https://github.com/PhysicsQoo/QuPRS/actions/runs/41954784814), [Linux cgroup v2 upstream semantics](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html).
2. **Capped failure with apparently zero OOM counters.** Counter-zero is not a complete absence-of-ENOMEM witness; `RLIMIT_AS` also lacks a dedicated exceeded counter. Any explicitly capped nonzero worker failure now refuses opt-in CNF retention. [Source pilot `bdc3b2e4`](https://github.com/PhysicsQoo/QuPRS/commit/bdc3b2e48eb2563669e5be61ed444a008097e0f1), [3/3 jobs #41957629230](https://github.com/PhysicsQoo/QuPRS/actions/runs/41957629230). Real nonroot UID65534 cgroup tests: **64 MiB** OOM `oom=1/oom_kill=2`, exit125 and no CNF; **256 MiB** ordinary failure `oom=0/oom_kill=0`, exit1 and no CNF; **256 MiB** valid science exit0. No residual worker cgroup.
3. **Unrelated capture files retained with CNF.** Retention now filters to regular CNF files; solver capture, nested directories and symlinks are deleted. [Linux/macOS pilot #41952489722](https://github.com/PhysicsQoo/QuPRS/actions/runs/41952489722).
4. **Exceptional cleanup skipped explicit removal.** Adopted-child failure and cgroup cleanup-error paths now **attempt** private TMPDIR cleanup, disable retention and report typed resource125. [Synthetic Linux exception pilot #41959156390](https://github.com/PhysicsQoo/QuPRS/actions/runs/41959156390) PASS. An actual unkillable kernel descendant is **not verified**.
5. **False-positive scientific test guards.** `"equivalent" in output.lower()` also accepts `not_equivalent`; fixed both Python ABBA/CodSpeed dual-verdict parsers (exact EQ/EQ* only), [18/18 pilot #41963333044](https://github.com/PhysicsQoo/QuPRS/actions/runs/41963333044). Rust identical-circuit test now requires **exact** `equivalent` and failed-cap tests require **empty science stdout**, [focused real CLI tests #41964598964](https://github.com/PhysicsQoo/QuPRS/actions/runs/41964598964) 3/3 PASS. **These were test-admission defects, not a demonstrated QuPRS algorithmic false verdict.**

All privileged Docker delegation and fault-injection workflows above remain in **experiment branches**, not PR #144. The production CLI was exercised as a nonroot worker in the delegated-cgroup pilots.

## Evidence boundaries and further research

- The ABBA single-H case checks a **structural output marker** (`Reduced PathSum State`) and exact full-output parity with the base, **not** an independent numerical oracle for its state. The GHZ/QPE dual mode independently accepts only exact EQ/EQ* tokens for identical QASM, but equal self-inputs and full-output parity alone do not replace the project's separate scientific conformance suites.
- The hosted ABBA uses 8 warmups + 30 alternating ABBA/BAAB blocks per case on **one Ubuntu runner**, with a 4000-sample bootstrap. This is a **provisional engineering envelope**; bootstrapped precision is conditional on the measured runner/blocks, not a hardware-independent uncertainty statement. Small one-shot circuits may incur a large relative slowdown. [Measurement method](HOSTED_ABBA.md).
- Official CodSpeed cross-run comparisons can reflect **different hosts/runtime versions**. The reported 20 apparent speedups against older HEAD and historical QAOA7/GPMC `-10.29%` comparison are **PERFORMANCE_INCONCLUSIVE** as source-caused changes. Only code HEAD's official run + the separate same-host ABBA support the narrow claims above. CodSpeed Macro remains unprovisioned.
- `cleanup_adopted_children` and cgroup removal can consume bounded **post-deadline cleanup grace**; do not advertise `--timeout` as strict process-exit wall clock. A higher-level container/job manager is required for supervisor SIGKILL, stray macOS daemons, a blocked stdout receiver, and lifecycle housekeeping.
- The physical cgroup pilot demonstrates **constructed delegation** (hosted Linux x86-64/ARM64, nonroot CLI). **Mac mini + OrbStack guest delegation, exact guest image/identity, and CodSpeed Macro parity are not admitted.**
- **CI cost observation, not a QOO-156 blocker:** a Rust CLI **test-only** change after a green code SHA still re-triggered five CodSpeed shards due to cumulative PR-to-dev impact classification and an insufficient narrow evidence-reuse whitelist. Restrict any future CI refinement to proven non-benchmark test-only scopes; do not globally exempt tests, reopen Done [QOO-130](https://linear.app/qoogohome/issue/QOO-130), or rerun expensive suites for Markdown updates. Later **documentation-only** commits should reuse previously verified code evidence via source-impact skipping.

## Merge disposition

- [x] Mandatory science/CI and provisional hosted ABBA successful on tested source `df0a554bf`.
- [x] Explicit Linux/macOS scope, kernel-accounting limitations and high-relative-cost disclosure documented.
- [ ] **Independent maintainer review** of the 17 changed files and exceptional worker-tree failure semantics; only COMMENT reviews exist so far.
- [ ] **Maintainer accepts/rejects +3 ms additive startup overhead as a release policy**; this is not yet approved.
- [ ] Only then consider **squash merge to dev**; no auto-merge or main update.

Historical chronological investigations are preserved by [Linear QOO-156 archived research ledger](https://linear.app/qoogohome/document/qoo-156-historical-research-and-ci-ledger-through-2026-11-05-894ef448b837) and their linked Actions runs, rather than multiple contradictory "CURRENT" entries in this document.

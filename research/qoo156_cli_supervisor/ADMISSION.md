# QOO-156 — outstanding gates and delegated-runner recipe

Status: experimental branch only. A successful GitHub workflow is NOT the
same as a positive physical-memory or CodSpeed performance certificate.

## Proven today

- GPMC and pinned static Ganak 2.8.0 (mode=6): genuine solver forced timeout
  and cleanup witnessed, including no partial EQ/NEQ.
  See Actions run 41831505038 (Ganak) and previous GPMC real-solver certificate.
- Genuine Ganak cleanup in both normal timeout and forcibly SIGKILL'ed Rust
  worker cases passed with BOTH pre- and post-Linux-subreaper implementation:
  Actions 41832224555 and 41833398697. No observed incremental subreaper
  benefit for those cases; synthetic orphan protection remains defense in depth.
- Rust Path-sum hot path was not changed by the outer CLI process experiment.
  Hosted CodSpeed observed ~1.5–2.7 ms added latency for tiny circuits;
  that is NOT formal Macro Runner admission.
- A physical RAM cap is available ONLY with a writable delegated Linux
  cgroup-v2 memory.max. The Unix RLIMIT_AS flag limits virtual address space,
  NOT physical RSS; unsupported environments fail closed.
- Linux GitHub-hosted runner, a systemd scope and privileged Docker all
  failed to obtain writable memory.max (NOT_ADMITTED). Lightweight syntax
  and truthful fail-closed preflight succeeded at Actions 41836128779.

## Docker-daemon externally enforced memory cap (2026-11-04)

A cheaper **alternative to child-cgroup delegation** is to have Docker
itself apply `--memory` and `--memory-swap` before launching an isolated
QuPRS CLI container. The cap applies to the entire container; the unprivileged
CLI inside does **not** need to create its own cgroup. This is a different
resource contract from `QuPRS_cli --max-memory-mib` and must not be counted
as internal CLI memory-cap certification.

[Real kernel memory.events probe #41838137145](https://github.com/PhysicsQoo/QuPRS/actions/runs/41838137145)
**PASS**, isolated Ubuntu 24.04 Docker cgroup v2, source-pinned image
digest + SHA. It allocated/touched 160 MiB physical memory inside a
child process under Docker memory caps:

| Docker cap | Recorded HostConfig.Memory | memory.events oom_kill delta | Child exit | Result |
|---|---:|---:|---:|---|
| 64 MiB | 67,108,864 bytes | +1 | SIGKILL (-9) | PASS |
| 128 MiB | 134,217,728 bytes | +1 | SIGKILL (-9) | PASS |
| 256 MiB | 268,435,456 bytes | 0 | 0, page touch complete | PASS |

This confirms actual physical enforcement by the kernel without
writable `memory.max` inside Docker. **Docker `State.OOMKilled`
alone is insufficient**: the first attempt observed exit=137 with
`OOMKilled=false`, even though the configured cap was present.
The final certificate uses per-container kernel `memory.events`
deltas and a successful high-memory control.

**Real Rust CLI experiment is now PASS** at [CI #41839492389](https://github.com/PhysicsQoo/QuPRS/actions/runs/41839492389), [artifact #13327809025](https://github.com/PhysicsQoo/QuPRS/actions/runs/41839492389/artifacts/13327809025). The same compiled DEBUG Rust CLI with the existing 192 MiB page-touch hook ran in the same unprivileged Ubuntu 24.04 Docker image, under daemon-installed limits:

| External cap | Kernel memory.max | memory.events oom_kill delta | Actual CLI result | No false scientific result |
|---|---:|---:|---|---|
| 384 MiB | 402,653,184 bytes | 0 | Exit 0; expected Reduced PathSum State | N/A (normal verification) |
| 128 MiB | 134,217,728 bytes | +1 | Exit 125, `WorkerFailed: ... SIGKILL` | **PASS**; stdout empty |

This certifies that an **externally installed Docker cap works on the
real Rust CLI worker** and prevents a false EQ/NEQ after its process is
killed. The CLI did NOT produce typed `MemoryLimitExceeded`; it emitted
generic `WorkerFailed` because it had no privilege to create its own
child memory cgroup. External Docker kernel event accounting is what
distinguished actual memory OOM from other SIGKILL causes in this
experiment. **`QOO156_CLI_INTERNAL_MEMORY_CERTIFICATE=NOT_TESTED`** remains
explicit; do not re-label the external certificate as internal memory
guard admission.

This can support an operational Docker/OrbStack resource envelope,
but cannot replace a positive `--max-memory-mib` child-cgroup
`memory.events` / exit=125 proof unless the CLI contract is explicitly
changed and independently tested.

## Source-backed real GPMC/Ganak WMC under Docker memory cap (2026-11-04)

[One-build controlled solver study #41842070834](https://github.com/PhysicsQoo/QuPRS/actions/runs/41842070834) **PASS**, [artifact #13329986800](https://github.com/PhysicsQoo/QuPRS/actions/runs/41842070834/artifacts/13329986800). Source `experiment/qoo156-cli-supervisor@b05e8d3d10ce8c3903b78f64754bf096de344451`. In a single Ubuntu 24.04 Docker runtime with unprivileged UID, network disabled, read-only root, bounded temporary storage, and no Linux capabilities:

- The same **release** Rust CLI (SHA-256 `8319636e21d88a4b559a054fb0f4ffafd642158fe728ed93f2336eab78e67f0d`) received the MQTBench VQE4 QASM with an additional X gate on the second circuit. All attempts used `--method wmc-only --strategy proportional --quiet`.
- The harness observed the **real solver PID, executable identity and arguments** before SIGSTOP→SIGCONT (no solver binary modifications). GPMC SHA-256 `507919b9af456645b55dc73e7d4db4a56b9293a0fa3ba99f5f8a0986826ef4b1`, `-mode=1`; Ganak 2.8.0 SHA-256 `934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd`, `--mode=6`.
- Docker installed exact `memory.max` in the container's kernel cgroup. No OOM event was observed in these four complete science runs:

| Real solver | External memory.max | Kernel oom_kill delta | Complete CLI verdict | Admission |
|---|---:|---:|---|---|
| GPMC | 256 MiB | 0 | `not_equivalent` | PASS |
| GPMC | 1024 MiB | 0 | `not_equivalent` | PASS |
| Ganak 2.8.0 | 256 MiB | 0 | `not_equivalent` | PASS |
| Ganak 2.8.0 | 1024 MiB | 0 | `not_equivalent` | PASS |

**Interpretation:** For this real VQE4 fixture, GPMC and Ganak can execute entirely inside a 256 MiB container and return identical verdicts. This **does not** establish that 256 MiB is adequate for larger QFT/QAOA/VQE cases or that numerical WMC values are identical. The driver checks the verdict and solver identity, not full WMC numerical parity.

The first attempt [#41841384189](https://github.com/PhysicsQoo/QuPRS/actions/runs/41841384189) found a **packaging/runtime prerequisite**: GPMC failed to start because Ubuntu runtime lacked `libgmpxx.so.4` (exit 127). The subsequent image includes `libgmpxx4ldbl` and explicitly verifies runtime dynamic linkage with `ldd` before the solver experiments. Never confuse a missing shared library with a solver or memory-cap failure.

**Separate certificates:**
- Kernel Docker memory cap + actual worker injected OOM: PASS ([#41838137145](https://github.com/PhysicsQoo/QuPRS/actions/runs/41838137145), [#41839492389](https://github.com/PhysicsQoo/QuPRS/actions/runs/41839492389)).
- Real solver inside Docker at 256/1024 MiB with consistent non-equivalence: PASS for exercised VQE4 fixture (above).
- Forced **actual WMC solver memory exhaustion** inside a container: NOT_TESTED. No solver OOM occurred in the four runs.
- `QuPRS_cli --max-memory-mib` own delegated child-cgroup contract: NOT_ADMITTED. Do not conflate these.
- Linux ARM64 under Mac mini/OrbStack: NOT_TESTED. Do not infer ARM64 from hosted x86_64.

This is a scientific/resource correctness control, **not** CodSpeed performance evidence. Final adoption requires an operational packaging/interface decision, source-image identity and architecture parity.

## Memory footprint sweep: real GPMC/Ganak vs circuit family (2026-11-04)

Source-locked [GitHub Actions #41845129593](https://github.com/PhysicsQoo/QuPRS/actions/runs/41845129593), [artifact #13331805422](https://github.com/PhysicsQoo/QuPRS/actions/runs/41845129593/artifacts/13331805422), `experiment/qoo156-cli-supervisor@4e852d8e27d69bae282b2e57303cb3957fe0bd17`: one release CLI build, immutable solver SHA, true solver PID/ELF/argv with SIGSTOP→SIGCONT, no solver source modifications. WMC-only, proportional strategy, source-backed MQTBench original circuit vs the same QASM with one additional X gate, exact complete `not_equivalent` verdict on all admitted cases.

| Case | Solver | Docker limit | cgroup v2 `memory.peak` | Kernel `oom_kill` delta | Verdict |
|---|---|---:|---:|---:|---|
| VQE4 | GPMC | 64 MiB | 18.836 MiB | 0 | `not_equivalent`, PASS |
| VQE4 | GPMC | 128 MiB | 18.844 MiB | 0 | `not_equivalent`, PASS |
| Graphstate16 | GPMC | 256 MiB | 19.797 MiB | 0 | `not_equivalent`, PASS |
| QFT16 | GPMC | 512 MiB | 42.000 MiB | 0 | `not_equivalent`, PASS |
| VQE4 | Ganak | 64 MiB | **unavailable** | **unavailable** | Container exit 137, Docker `OOMKilled=true`; **NOT_ADMITTED** (driver killed, no solver witness) |
| VQE4 | Ganak | 128 MiB | 80.668 MiB | 0 | `not_equivalent`, PASS |
| Graphstate16 | Ganak | 256 MiB | 80.738 MiB | 0 | `not_equivalent`, PASS |
| QFT16 | Ganak | 512 MiB | 81.328 MiB | 0 | `not_equivalent`, PASS |

**Interpretation:** `memory.peak` is the *entire container cgroup*, accounting for CLI, solver, Python test harness, kernel file page cache and any tmpfs pages, **not an isolated solver RSS**. Under this one exact workload, Ganak has a much larger observed full-container footprint than GPMC; the 64 MiB Ganak container suffered an OOM, while GPMC VQE4 survived at 64 MiB. Do not infer that the Ganak solver PID (rather than its parent/harness) was itself the OOM-selected victim: the 64 MiB container produced no in-container JSON witness. It only proves this container/job configuration is unsafe at 64 MiB. **Do not generalize memory minima to every circuit or architecture**, and never treat the scientific-control test's elapsed time as CodSpeed performance evidence.

Next bounded experiment: concentrate the threshold between 64 and 128 MiB (Ganak) and a lower QFT16/GPMC limit, with a success control and explicit unobserved-OOM state. Independent Mac mini/OrbStack ARM64 proof remains NOT_TESTED.

## Targeted GPMC/Ganak tight-memory boundary (2026-11-04)

[Seven-case bounded boundary experiment #41846141175](https://github.com/PhysicsQoo/QuPRS/actions/runs/41846141175), [source-pinned artifact #13331781669](https://github.com/PhysicsQoo/QuPRS/actions/runs/41846141175/artifacts/13331781669), SHA `experiment/qoo156-cli-supervisor@793f69c3ca1d42733144c3e715cdaa1f2c204f77`. Real unmodified pinned ELF, WMC-only source-locked original VQE4+X or QFT16+X, same Ubuntu Docker image, one release CLI build. No walltime-based performance claims.

| Solver / source case | Docker physical cap | Actual container `memory.peak` | Docker exit / OOM | Scientific result |
|---|---:|---:|---|---|
| Ganak VQE4 NEQ | 72 MiB | unavailable | 137 / OOMKilled=true | **NOT_ADMITTED**, parent driver killed; no Solver-specific death witness |
| Ganak VQE4 NEQ | 80 MiB | unavailable | 137 / OOMKilled=true | **NOT_ADMITTED**, parent driver killed; no Solver-specific death witness |
| Ganak VQE4 NEQ | 88 MiB | 80.773 MiB | 0 / false | full `not_equivalent` PASS |
| Ganak VQE4 NEQ | 96 MiB | 80.754 MiB | 0 / false | full `not_equivalent` PASS |
| Ganak VQE4 NEQ | 128 MiB | 81.012 MiB | 0 / false | full `not_equivalent` PASS |
| GPMC QFT16 NEQ | 48 MiB | 42.168 MiB | 0 / false | full `not_equivalent` PASS |
| GPMC QFT16 NEQ | 64 MiB | 42.066 MiB | 0 / false | full `not_equivalent` PASS |

Pre-worker container `memory.peak` was ~10.9 MiB for Ganak tests and ~9.6–9.9 MiB for GPMC. These are **whole-cgroup** metrics and include the Python observer, dynamic loader, page cache and tmpfs; subtracting them does not yield isolated Solver RSS. The natural memory boundary for this one Ganak VQE4 NEQ/container combination was bracketed between failure at 80 MiB and success at 88 MiB; successful GPMC QFT16 cap of 48 MiB has only ~5.8 MiB space above observed peak and should **not** be promoted as a production default. Repeats and equivalent (EQ) / difficult-case fixtures are needed for robust operational headroom.

**Actual Solver PID OOM remains unproven by these low-cap results:** the Ganak72/80 containers were completely killed (exit137, Docker OOM flag true) before an in-container JSON witness could be preserved. A separate bounded adversarial kernel OOM experiment targeting a paused authentic Solver PID is in progress; it must differentiate a controlled victim-selection stress test from ordinary Solver memory demand. The internal CLI `--max-memory-mib` remains NOT_ADMITTED due absent delegated cgroups. CodSpeed remains the sole formal performance basis.

## Real 64 MiB cgroup OOM certificate

Use a dedicated, trusted ephemeral Linux VM/runner with unified cgroup v2,
memory controller delegation, Rust stable, CMake, pkg-config, GMP/MPFR
development headers, coreutils, and QuPRS checked out at a fixed SHA.

A systemd-managed runner service may need an administrator-approved
drop-in under its own service name:

    [Service]
    Delegate=yes
    MemoryAccounting=yes

The above configuration alone is not proof of delegation. The effective
process cgroup under /proc/self/cgroup must allow the runner identity
to create a child group and write memory.max, memory.oom.group, cgroup.procs
and cgroup.kill. Do NOT use sudo within the test or silently downgrade the
physical memory limit to RLIMIT_AS.

In the same identity as the runner:

    QOO156_OOM_EVIDENCE="$PWD/evidence/qoo156-oom-positive" \
      bash scripts/qoo156_positive_cgroup_oom_gate.sh

This bounded, fail-closed script first verifies memory.max write/readback
without compiling native code. If admitted, it builds only the CLI
integration test, forces 192 MiB page touches under a 64 MiB memory.max
limit, requires an actual kernel memory.events oom_kill witness, a
typed resource exit 125, and no scientific result. Only the exact output

    QOO156_CGROUP_OOM_CERTIFICATE=PASS

is positive certification. An ordinary test result of PASS or a CI job
success is insufficient. Archive SHA, Rust version, kernel, effective
cgroup, source hashes, readiness, test stdout/stderr, and verdict.

A manual-only template is staged at
.github/workflows/qoo156-positive-cgroup-oom.yml with runner labels
self-hosted + linux + qoo156-cgroup-v2. GitHub workflow_dispatch requires
the file on the repository DEFAULT branch; as long as this workflow
exists solely on the experiment branch, use the direct bash script.
Do not merge the experimental CLI just to activate the workflow.

## Macro Runner

The one-shot paired pilot Actions 41825389124 remains queued with
runner_id=0 (no runner assigned); it has NOT generated formal CodSpeed
measurements. The codspeed-macro runner label matches public CodSpeed
documentation. Account/repository runner access or availability cannot be
established solely from a queued job. Check the CodSpeed integration and
GitHub runner group permissions; avoid repeated expensive dispatches.

Once a Macro Runner is truly assigned, compare unchanged dev vs
experimental supervisor vs direct worker, using identical Rust core source
and ABBA CodSpeed WallTime on the same runner. Keep absolute startup
milliseconds separate from percentage overhead on tiny circuits.

## Gate verdict

GPMC/Ganak real solver cancellation: ADMITTED for exercised cases.
Positive physical-memory OOM enforcement: EXTERNAL_DOCKER_ADMITTED for exercised cases; INTERNAL_CLI_NOT_ADMITTED.
True Macro Runner CLI performance: NOT_ADMITTED.
Linux subreaper real-Ganak incremental benefit: NOT_DEMONSTRATED.
No dev merge until the outstanding safety and performance gates are
explicitly addressed on a consistent source SHA.

## 2026-11-04 follow-up: 72–128 MiB real WMC boundary and CLI safety source audit

### Source-paired container boundary (not CodSpeed)

[Actions #41846141175](https://github.com/PhysicsQoo/QuPRS/actions/runs/41846141175) completed SUCCESS, workflow source
`793f69c3ca1d42733144c3e715cdaa1f2c204f77`, one pinned release Rust CLI SHA256
`8319636e21d88a4b559a054fb0f4ffafd642158fe728ed93f2336eab78e67f0d`.
Ganak 2.8.0 `--mode=6` SHA256 `934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd`;
GPMC `-mode=1` SHA256 `507919b9af456645b55dc73e7d4db4a56b9293a0fa3ba99f5f8a0986826ef4b1`.
All completed cases genuinely witnessed the solver PID, argv, STOP/CONT and complete `not_equivalent` output. Docker installed the physical cap; internal `--max-memory-mib` was NOT exercised.

| Authentic solver / circuit | Docker memory.max | Container memory.peak | Classification |
|---|---:|---:|---|
| Ganak / VQE4 | 72 MiB | unavailable | container exit137 / Docker OOM flag, no in-container record; NO PID victim attribution |
| Ganak / VQE4 | 80 MiB | unavailable | container exit137 / Docker OOM flag, no in-container record; NO PID victim attribution |
| Ganak / VQE4 | 88 MiB | 80.773 MiB | COMPLETE_WITHIN_CAP, kernel oom_kill delta0 |
| Ganak / VQE4 | 96 MiB | 80.754 MiB | COMPLETE_WITHIN_CAP, kernel oom_kill delta0 |
| Ganak / VQE4 | 128 MiB | 81.012 MiB | COMPLETE_WITHIN_CAP, kernel oom_kill delta0 |
| GPMC / QFT16 | 48 MiB | 42.168 MiB | COMPLETE_WITHIN_CAP, kernel oom_kill delta0 |
| GPMC / QFT16 | 64 MiB | 42.066 MiB | COMPLETE_WITHIN_CAP, kernel oom_kill delta0 |

These values include the CLI, Python driver, solver, kernel page cache and tmpfs; they are **NOT solver RSS** and are not universal minimum recommended memory limits. Ganak VQE4 in this *one source-pinned container* failed at 80 MiB and completed at 88 MiB. The Docker OOM flag is outer evidence; absence of a surviving driver record means the OOM victim and event delta were not individually certified in the 72/80 MiB cases. Do not use wall-clock durations from this experiment for performance comparison.

### New code-audit findings: resource-contract gaps (NOT yet runtime-fixed)

Source inspected on `experiment/qoo156-cli-supervisor` at the above boundary run, files `rust/cli/src/{supervisor,args,main}.rs`:

1. **Output bytes are not actively capped.** Supervisor redirects stdout/stderr into parent-owned `tempfile::tempfile()`; `OUTPUT_LIMIT=16 MiB` for stdout is checked only **after successful child exit**. Failure stderr is truncated on *reading back*, not on writing to its temporary file. A noisy worker can exhaust temporary storage *before* the eventual output cap check. Classify this as a **source-proven safety gap, not a demonstrated actual disk exhaustion**. Required fix: truly bounded streaming/spooling of both streams; abort/reap full worker tree on overflow; preserve atomic scientific output. Test stdout + stderr flood and temporary filesystem boundedness on Linux/macOS, including if the child exits immediately after overflowing.

2. **Hidden worker flag has no parent-origin admission check.** `--__quprs-worker` is parsed as a hidden boolean; `main.rs` directly executes `prepare_worker()` and the verifier when it is present. Hiding an option in Clap help is not an authorization check; direct invocation bypasses the new outer supervisor's timeout and resource-limit enforcement. This is **source-proven reachability, not a runtime exploit test**. Required fix: a verified parent-to-worker launch channel/inherited handle rather than merely a user-settable environment variable; reject unauthorised direct worker invocation without scientific output; keep the `direct_head` CodSpeed baseline through a controlled benchmark-only entrypoint, not a public release bypass.

3. **Exact timeout semantics:** `recv_timeout` covers child execution, but reaping and cleanup (and eventual buffered output publication) may run *after* deadline. Describe the contract as monotonic execution deadline + bounded cleanup latency; do not claim that the outer CLI process always exits at exactly `timeout` seconds. Assess cleanup when a worker/subprocess ignores TERM or exits while OOM occurs.

None of these findings changes established GPMC/Ganak cleanup evidence, the unchanged Rust Path-sum core, or the positive external Docker cap. There is **no positive internal child-cgroup admission**, no macOS/OrbStack ARM64 memory proof, and no assigned Macro CodSpeed runner (Actions #41825389124 still queued as inspected).

### Next scoped work, in order

1. Isolate the output-limit and hidden-worker launch fixes on this experiment branch, add **small, deterministic** Rust CLI tests for overflow, direct bypass and atomic output, and preserve source identities. Avoid modifying `rust/pathsum` or QOO-6 solver lifecycle; no numerical/tolerance changes.
2. Only the scoped Linux/macOS CLI CI on code changes; no full five-shard CodSpeed rerun for Markdown or unrelated changes. Explicitly compare full process overhead through properly paired **CodSpeed Macro** once a runner is truly assigned; no merge before admission.
3. Keep internal delegated cgroup/OOM certification separate from external Docker caps, and investigate native Mac/OrbStack ARM64 separately. Do not infer typed `MemoryLimitExceeded` from Docker exit137 alone.

## 2026-11-04 real-solver adversarial OOM victim attempt: NOT_ADMITTED

A newer controlled authentic-solver victim-selection attempt [Actions #41847115883](https://github.com/PhysicsQoo/QuPRS/actions/runs/41847115883), source `7c363165b1c5fd67631d71b51a6c34b74a1e7f36`, finished **workflow FAILURE** and `QOO156_REAL_SOLVER_OOM_CERTIFICATE=NOT_ADMITTED`. The evidence was retained [artifact #13331537658](https://github.com/PhysicsQoo/QuPRS/actions/runs/41847115883/artifacts/13331537658). This is a *different* test from the successful natural-footprint boundary run #41846141175.

- GPMC: `NOT_ADMITTED_NO_RECORD`; no in-container solver PID or cgroup event record survived. Cannot attribute the failure to an OOM-selected solver.
- Ganak: genuine pinned `--mode=6` PID observed and SIGSTOP, `oom_score_adj=1000`; the synthetic 230 MiB pressure helper exited zero, **kernel oom_kill delta=0**, and the test harness ultimately sent SIGKILL to the solver to clean up a stopped process. CLI returned non-scientific error and stdout empty. **The SIGKILL was harness-driven, not kernel OOM**; no positive OOM-victim certificate.
- The Ganak cgroup peak was 255,881,216 bytes (~244.03 MiB) despite a 256 MiB cap. The script's fixed page-touch quantity does not guarantee effective cgroup OOM because reclaimable file cache can be reduced. Treat this as a plausible explanation supported by observed peak and kernel delta, not a verified causal kernel trace.
- This adversarial run cannot establish natural solver memory requirements; its purpose was to witness a real kernel-selected solver victim and no false verdict. No scientific result or speed claim is certified.

**Next *scoped* corrective design, without new native algorithm changes or blind retries:** Move the witness and cgroup-event recorder **outside** the memory-limited container. The host-side harness should retain PID/start-time identity, Docker memory.max, cgroup memory.events, container exit/oom signal and output atomicity even if the container driver dies. Run bounded gradual page pressure rather than a single fixed allocation, independently distinguish `kernel OOM killed target`, `pressure child OOM`, `CLI timeout cleanup` and `harness SIGKILL`, and require a high-cap complete control. Do not assert solver victim identity merely from exit137, Docker OOMKilled, disappearance of a PID, or a harness-triggered kill. Keep native release source and solver hashes pinned. This will be a new experiment only when the revised harness has a preflight that demonstrates it can preserve records under actual container death.

This failed attempt does not invalidate the earlier positive Docker memory-cap control, real GPMC/Ganak normal complete computations, or actual solver forced-timeout cleanup. Internal `--max-memory-mib` remains NOT_ADMITTED.

## 2026-11-04 isolated CLI I/O + worker admission fix (source-pinned)

Separate implementation branch `experiment/qoo156-cli-io-admission`, forked at previous experiment commit `8c5bc45019e2e414c170c0522f846c35058b1bb8`. The original `experiment/qoo156-cli-supervisor` branch remains independent for parallel real-solver OOM experiments; **no dev/main merge**, no changes to `rust/pathsum` or third-party WMC sources.

**Scoped source commits and verified focused CI:**

| Source SHA | Change | ubuntu-24.04 | macos-14 |
|---|---|---|---|
| [`c8492fe`](https://github.com/PhysicsQoo/QuPRS/commit/c8492feefef2c2d41050f2e27a803875eca1bab2) | Parent-owned 16 MiB per-stream bounded stdout/stderr pipe capture; fail before committing scientific stdout on excess/IO error; debug-only overflow tests | [#41849527251](https://github.com/PhysicsQoo/QuPRS/actions/runs/41849527251) PASS | same workflow PASS |
| [`92bbe5c`](https://github.com/PhysicsQoo/QuPRS/commit/92bbe5c68017bc68e4b7abac3c32753d2ed7d01a) | Reject ordinary direct `--__quprs-worker` launch without parent PID + anonymous inherited stdin launch witness; tests cover missing context, forged PID without pipe, normal supervised output. Source-paired benchmark removes the `direct_head` bypass and retains base/HEAD ABBA | [#41850230345](https://github.com/PhysicsQoo/QuPRS/actions/runs/41850230345) PASS | same workflow PASS |

Both workflows report **completed SUCCESS** and both matrix jobs passed CLI tests and release build. The code still uses an event-based waiter rather than introducing a periodic 20-ms poll. Every captured stream is capped **while the worker runs**, unlike the old stdout check after worker success and previously unlimited stderr temporary file. Debug-only large-output hook is absent from the release CLI.

**Accurate scope:** the inherited pipe + parent-PID check is an ordinary-misuse guard, **not a cryptographic authentication or adversarial same-user security boundary**. A user who controls executable invocation can deliberately construct their own launch protocol or call the native library directly. Hard whole-request containment still depends on independent OS process isolation/cgroups and correct cleanup. No strict deadline is claimed for delayed process cleanup or final output transport after the monotonic worker-execution deadline.

**No new formal performance certificate:** the Rust Path-sum core source tree is unchanged, but two pipe-capture threads, process spawning, and output forwarding impose CLI overhead. Formal paired CodSpeed Macro run [#41825389124](https://github.com/PhysicsQoo/QuPRS/actions/runs/41825389124) remains **QUEUED without an assigned runner**, so mark `PERFORMANCE_NOT_ADMITTED`. Do not infer CodSpeed equivalence from unit tests or uncontrolled wall time. The Macro bench now compares legitimate base/HEAD (ABBA) only; prior `direct_head` internal-worker bypass has intentionally been removed.

**Memory status unchanged:** external Docker `--memory` cap, actual GPMC/Ganak complete WMC cases, and pinned solver timeout cleanup are already admitted for exercised workloads. Internal `--max-memory-mib` with delegated cgroup typed OOM remains `NOT_ADMITTED`; native Mac mini / OrbStack Linux ARM64 is `NOT_TESTED`. A more recent adversarial external Docker OOM run [#41849006978](https://github.com/PhysicsQoo/QuPRS/actions/runs/41849006978) has a **positive GPMC subcase** (real pinned solver SIGKILL and cgroup oom_kill +1 under artificial memory pressure, no partial science output) but **Ganak `NOT_ADMITTED_NO_RECORD`**, so the overall workflow correctly remains FAILURE / NOT_ADMITTED. Do not conflate this with natural RSS demand, unmodified-solver crash semantics beyond these cases, or typed internal child-cgroup OOM.

**Remaining gates / next action:** verify final CLI version through **true** CodSpeed Macro source-paired ABBA, test a hard memory-controller case on an actually delegated Linux host, and separately establish Mac/OrbStack ARM64 containment. Only after these conditions decide whether the CLI safety branch can be integrated. Do not rerun expensive native CI merely for this Markdown update.

## 2026-11-04 inherited output pipes: completion-EOF gate

- [Commit a02d2b9](https://github.com/PhysicsQoo/QuPRS/commit/a02d2b9512d51b1be0e580d2e50abb1216405052) closes an additional source-audited failure path: after direct worker exit, a descendant could retain stdout/stderr descriptors and cause an unbounded `reader.join()` even when the parent deadline had expired.
- Both bounded stream-capture threads now send `CaptureFinished` on EOF. The supervisor only publishes success after **worker Exited + stdout EOF + stderr EOF**, within its monotonic request deadline. If EOF never arrives, it returns Timeout and does not join a blocked reader on the failed path; cancel/reap is attempted. A debug-only spawned child inherits output descriptors and verifies the deadline holds and no partial scientific success leaks.
- Exact [focused GitHub Actions #41852901307](https://github.com/PhysicsQoo/QuPRS/actions/runs/41852901307) SUCCESS on both Ubuntu24.04 and macOS-14, including release compilation. This test covers a child in the inherited worker process group, not a detached re-session child escaping macOS supervision. No claim of complete macOS process-tree containment.
- **Important**: This closes the blocking pipe `join()` path for exercised cases, not a mathematical guarantee of exact total CLI wall-clock exit: kernel cleanup, output publication to a blocked downstream consumer, and nondelegated detached grandchildren remain separate limits.
- This branch changes `rust/cli` only, with **unchanged `rust/pathsum`** and no Solver changes. Source-scoped correctness PASS is not a CodSpeed performance certificate; the true Macro Runner job is still queued/unassigned, so **P1 performance NOT_ADMITTED**. No `dev` merge.

## 2026-11-04 final CLI I/O branch source-paired CodSpeed observation

Exactly [GitHub Actions #41855169039](https://github.com/PhysicsQoo/QuPRS/actions/runs/41855169039), source `e7cef4041992bd753ba60a97380e57407bb08b5e`, completed SUCCESS, official connected [CodSpeed run `6aeb4b9d09f1ddb2bf501af8`](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aeb4b9d09f1ddb2bf501af8). It built untouched `dev@79e975b0` and current bounded-stdout+stderr/worker-admission+EOF-gated HEAD using the **same** `rust/pathsum` tree, then measured source-paired Base/HEAD/HEAD/Base CLI subprocess WallTime on one hosted Ubuntu runner. No direct worker release bypass variant was included.

| CLI case | Base min WallTime (repeated) | HEAD min WallTime (repeated) | Observed extra HEAD fixed cost |
|---|---:|---:|---:|
| single H | 1.0 / 1.0 ms | 2.3 / 2.2 ms | approx 1.2–1.3 ms |
| GHZ32 RR dual circuit | 1.2 / 1.2 ms | 2.4 / 2.4 ms | approx 1.2 ms |
| QPE-exact8 RR dual circuit | 2.0 / 2.1 ms | 3.2 / 3.3 ms | approx 1.2 ms |

**Official CodSpeed warning on all twelve cases:** `Walltime results may be unreliable` because the run was **NOT a CodSpeed Macro Runner**. Therefore this is an **OBSERVATIONAL_ONLY** scientific/performance early signal, **NOT** a formal performance-regression/no-regression certificate. Absolute startup overhead is real in the hosted observations and large relative to these tiny 1–2ms requests; do not claim zero CLI overhead. All Rust core native pathsum algorithms remain unmodified. The earlier ~20ms polling tail was eliminated, but this final branch adds a bounded pipe pump, verified launch context, extra thread synchronization and process isolation. The current result must not be compared as a different runner/mode environment without accounting for CodSpeed's environment warnings.

**Formal P1 Macro** [GitHub job #126558702309](https://github.com/PhysicsQoo/QuPRS/actions/runs/41825389124/job/126558702309) still `queued` with no runner assignment. Avoid dispatching more identical queued jobs. Once a truly available Macro Runner is confirmed, run a fresh same-SHA, same-runner ABBA comparison on the finalized CLI and evaluate **absolute extra milliseconds plus relative overhead by circuit duration**, separate from Rust-native CPU Simulation. No full release or five-shard CI rerun for this documentation update; no `dev` merge while formal performance admission remains NOT_MET.


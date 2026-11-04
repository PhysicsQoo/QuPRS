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

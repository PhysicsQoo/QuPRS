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

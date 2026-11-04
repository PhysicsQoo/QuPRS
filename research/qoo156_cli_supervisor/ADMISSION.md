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
Positive physical-memory OOM enforcement: NOT_ADMITTED.
True Macro Runner CLI performance: NOT_ADMITTED.
Linux subreaper real-Ganak incremental benefit: NOT_DEMONSTRATED.
No dev merge until the outstanding safety and performance gates are
explicitly addressed on a consistent source SHA.

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

## Remaining acceptance

1. Confirm event-driven CodSpeed CLI overhead across short and realistic workloads; hosted WallTime is non-Macro observational until fixed runner acceptance.
2. Validate GPMC/Ganak nested process groups, forced timeout cleanup and no child-process leak (including Linux/macOS distinctions).
3. Positive physical-memory enforcement test on a delegated Linux cgroup, forced OOM, cgroup event provenance, and process-start containment confirmation. Pre-exec placement is now implemented but lacks a delegated-runner positive gate.
4. Repeat science and performance gates on final source SHA. Do not merge or release from this experimental branch until admitted.

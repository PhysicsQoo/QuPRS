# Rust CLI timeout, process isolation and resource limits

The `QuPRS_cli` executable supervises each invocation in a separate worker process. The deadline includes QASM parsing, verification, worker termination and closure of both captured output streams. The native Path-sum reduction and weighted counting algorithms are unchanged by this CLI mechanism.

## Usage

```bash
QuPRS_cli circuit1.qasm circuit2.qasm --timeout 120 --quiet
```

On Linux with a properly delegated, writable cgroup v2 memory controller:

```bash
QuPRS_cli circuit1.qasm circuit2.qasm --timeout 120 --max-memory-mib 2048 --quiet
```

On Unix, a separate virtual-address-space cap is available:

```bash
QuPRS_cli circuit1.qasm circuit2.qasm --max-address-space-mib 4096 --quiet
```

| Option or behavior | Contract |
| --- | --- |
| `--timeout SECONDS` | Default **600**; positive integer; monotonic, whole-invocation budget. A bounded cleanup grace or a blocked downstream stdout consumer can extend wall-clock termination beyond the budget. |
| `--max-memory-mib MIB` | **Linux only**, opt-in physical memory cap using a writable delegated **cgroup v2** `memory.max`. No delegation or failed setup → fail closed; never silently substitutes an address-space cap. |
| `--max-address-space-mib MIB` | **Unix only**, `RLIMIT_AS` virtual address-space cap; **not** a physical RSS limit. |
| Worker output | stdout and stderr are captured concurrently, each bounded to **16 MiB**. Successful worker output is published only after completion and resource cleanup. |
| `--quiet` | Successful dual-circuit verification uses the ordinary machine-readable verdict. Timeout emits the non-scientific token `Timeout`; no partial equivalence verdict is published on worker or resource failure. |

## Exit and cleanup behavior

| Exit code | Meaning |
| --- | --- |
| `0` | Worker completed successfully and required cleanup succeeded. |
| `124` | Whole-invocation timeout. |
| `125` | Resource supervision, output capture/size limit, or cleanup failure. |
| `130` / `143` | SIGINT / SIGTERM cancellation on Unix. |
| Other nonzero | Worker failure propagated when available; no partial scientific result. |

A Linux physical memory limit is enforced only when an appropriate cgroup v2 controller has been delegated. The supervisor verifies `memory.max` and accounts for both `memory.events.oom` and `oom_kill` before classifying a capped result. A positive `memory.events.max` pressure counter alone does not prove OOM. Missing or malformed required resource evidence is an error, not an assumed success. The worker cgroup must be cleaned up before successful result publication.

Worker-side WMC CNF and solver output captures use a parent-owned, mode-0700 per-invocation temporary directory. Normal completion, timeout, cancellation and capped failures clean it. `QUPRS_KEEP_FAILED_CNF=1` is an explicit debugging opt-in that retains **only regular `temp_eqcheck_*.cnf` files** after an **ordinary uncapped worker failure**. A physical cap, `RLIMIT_AS` cap, OOM, unknown resource state or cleanup failure disallows failed-CNF retention; solver captures are not retained.

## Platform and security boundaries

On Linux the supervisor uses child-subreaper cleanup, worker-parent-death notification and process-group handling, but it cannot synchronously clean up if the supervisor itself receives SIGKILL. macOS supports timeout, cancellation and `RLIMIT_AS`, but not Linux cgroup v2, child-subreaper or parent-death-signal guarantees. Uncontained detached solver descendants and unkillable kernel tasks require host-level process or job management.

These controls are a resource-management and result-integrity mechanism for **trusted local execution**, not a security sandbox against a malicious same-user solver. Output committed to an external consumer is not transactional if that consumer breaks or blocks during the write. For forced-termination containment, manage the full invocation in an external container or job cgroup. An external container memory cap constrains the entire job but is not equivalent to the CLI's `--max-memory-mib` flag.

For current options and validation use `QuPRS_cli --help` and the CLI integration tests under `rust/cli/tests/`.

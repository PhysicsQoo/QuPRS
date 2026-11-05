# Python API: Rust process isolation

QuPRS provides an optional, one-call process-isolated mode for its existing
Python equivalence-checking interface. The public function signature is unchanged.

```python
from QuPRS import check_equivalence

fast = check_equivalence(
    original, optimized,
    backend="rust",
    method="hybrid",
    safe_mode=False,  # default: in-process PyO3 extension
)

protected = check_equivalence(
    original, optimized,
    backend="rust",
    method="hybrid",
    safe_mode=True,   # separate supervised worker using the same PyO3 engine
    timeout=60,
)
```

The default in-process mode does not launch a Worker. The isolated mode runs the
same Rust verification engine in a fresh process and returns the same
`EquivalenceCheckResult` type. It is not a wrapper around the separately
distributed Rust CLI executable.

## Limits and error handling

Isolation is supported on POSIX systems. A monotonic deadline bounds
supervised Worker execution and IPC. Cleanup has a separate bounded grace
period, so the call can outlast the requested `timeout` while children are
being reaped. For Qiskit `QuantumCircuit` inputs, the global-phase preflight
runs in the parent before the deadline starts; subsequent QASM serialization
is counted against that budget but cannot be forcibly interrupted by the
child Supervisor. Consequently, this is **not** an unconditional hard
end-to-end deadline for the entire Python API call.

The worker protocol bounds request and diagnostic output sizes. Missing,
partial, or malformed replies, failing Solver processes, and unverified
resource cleanup raise an exception rather than being interpreted as quantum
circuit inequivalence. Completed Rust verification still distinguishes
`equivalent`, `equivalent*`, `not_equivalent`, `unknown`, `Timeout`, and
`MemoryOut` according to the existing result contract.

An isolated Worker is not a general-purpose sandbox for hostile code.
On Linux, supervision includes a dedicated child-subreaper so that ordinary
detached solver descendants can be reaped without changing the host Python
application's child-process handling. A force-killed Supervisor or malicious
daemonization may still require an outer container/job manager. On macOS,
unrelated-session daemon descendants cannot be universally contained with
POSIX process-group signals alone.

## Optional memory restrictions

The default `safe_mode=True` does **not** promise a physical-memory cap.
These optional environment variables are evaluated by the isolated execution
path; no additional Python function arguments are required:

| Variable | Meaning |
| --- | --- |
| `QUPRS_ISOLATED_MAX_ADDRESS_SPACE_MIB` | Unix Worker `RLIMIT_AS`, limiting virtual address space, **not resident RAM** |
| `QUPRS_ISOLATED_MAX_MEMORY_MIB` | Linux delegated cgroup-v2 `memory.max` for the isolated Worker, requiring a suitable controller and delegation |

For example, on a Linux host that actually delegates the memory controller:

```bash
QUPRS_ISOLATED_MAX_MEMORY_MIB=4096 python run_verification.py
```

An explicitly requested physical cap fails with an error when delegation is
unavailable; it is never silently replaced with `RLIMIT_AS`. For a delegated cgroup, the parent admits the private Supervisor before
it launches the Rust Worker, so the Worker and any Solver descendants inherit
the physical memory cap from process creation. The private Supervisor's own
interpreter startup occurs before admission and is **not** covered by the
cap. For hard caps covering the entire request, including Supervisor startup,
use an outer job or container manager.

The internal PyO3 extension API still rejects `safe_mode=True` when called
without the Python supervisor. Call `QuPRS.check_equivalence()` to request
isolation. Solver precision, RR tolerance, phase policy, and WMC tool selection
have the same meanings in both Rust execution modes.

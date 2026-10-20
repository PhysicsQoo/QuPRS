# Opt-in native Rust exclusive stage attribution

This is an experimental, source-pinned diagnostic. It does not modify
equivalence, WMC solver selection, numerical tolerances, or the public
Python result dataclass. Ordinary verification does not emit these fields.

## Enable

Set the environment variable QUPRS_STAGE_LEDGER=1 in the process invoking
the native Rust verifier. The native FFI dictionary then includes an optional
stage_ledger object. With the flag absent, that key is entirely omitted.
The instrumented solver and reduction code uses a thread-local session.
An explicit session guard resets data on every return, including failures.

The narrow real pilot runs the official Rust verifier on:
- QAOA7 Hybrid / Proportional / GPMC, using the existing QASM pair.
- Generated GHZ4 WMC-only / Proportional / GPMC, with Z²=I on the
  second circuit.

Run from the repository root after installing the development Rust/Python
package and its native toolchain:

    cargo test --manifest-path rust/Cargo.toml -p pathsum --lib diagnostics::tests
    python -u .diagnostics/rust_stage_ledger/run.py

The paired control runs one process with the flag disabled and another with
the flag enabled for each circuit. It is a **semantic and accounting check**,
not a timed performance A/B. Use repeated source-pinned controlled samples
before making any performance or observer-overhead claims.

## Stage contract

All stage times below use Rust Instant elapsed walltime in seconds, excluding
the Python FFI's initial QASM parsing and Python object marshaling.

| Field | Definition |
|---|---|
| strategy_except_reduction | Native Strategy inclusive wall less all root-level full_reduce spans |
| reduction | Top-level full_reduce elapsed time; nested frames counted once |
| cnf_encode | WmcManager::encode_trace |
| cnf_serialize | All native to_dimacs_string calls, including the one inside the solver path |
| cnf_file_write | Temporary CNF file opening, writing and closing |
| solver_supervision | Actual native process spawn, wait, stdout/stderr handling and cleanup |
| classification | Final native WMC amplitude interpretation |
| wmc_other | Native WMC interval less the above disjoint WMC stages |
| native_setup_status_other | Native verification wall less native PathSum and WMC intervals |

The separate solver_child_spawns count increments **only after OS child
creation succeeds**. A nonzero count documents real invocation. It does not
equal a solver's number of internal searches and its supervision walltime
is not pure Solver CPU time.

The check on has_stage_overlap rejects material negative residuals and
records the signed closure_error_seconds. Legacy Rust tool_time and
to_dimacs_time overlap the new WMC interval and are never added to stage
totals. Thus stage closure is arithmetic validation by construction, not
proof of complete causal attribution.

### Known limits

The experiment does not yet separate each individual Elim, HH and Omega
rule's exclusive time, record K/L/V/D/W_redundant structural counters,
or include native FFI/QASM parsing inside the engine timer. Likewise,
Python and Rust have different internal reduction orders and cost
representations; per-stage causality cannot yet be compared one-to-one.
Profiling itself can perturb short-latency runs.

## Initial evidence

The first successful native stage experiment is source-pinned at
fcf7bc9ba716ea29c299d89cc7d61efc17b3e5c3:

https://github.com/PhysicsQoo/QuPRS/actions/runs/39439871708

The raw artifact includes source and GPMC SHA, environment/Python package
versions, four individual on/off JSON observations, summary.json/summary.md,
samples.jsonl and a SHA256SUMS manifest. The original artifact ZIP digest was
efb48d77331d6adf947a140f9c4b49b806cc9d10766367622e302f79c014d57a.
All 10 original internal SHA256 checks were independently verified.

Three Rust thread-local/recursion/partition contracts and all four
end-to-end classifications passed; the two opt-in cases each recorded a
real GPMC child process. No speedup claim is made from this pilot.

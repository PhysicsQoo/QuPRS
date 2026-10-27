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
rule's exclusive time, or fit structural counters to measured costs,
or include native FFI/QASM parsing inside the engine timer. Likewise,
Python and Rust have different internal reduction orders and cost
representations; per-stage causality cannot yet be compared one-to-one.
Profiling itself can perturb short-latency runs.

## Opt-in Elim structural records

`stage_ledger.structural_elim_attempts` is a list of **pre-mutation**
snapshots, one for each actual `try_reduce_elim` call. A normal
`full_reduce` call with no candidates skips Elim and emits no records;
an explicit `try_reduce_elim(&[])` records a valid `k_r=0` sample.

| Field | Meaning |
|---|---|
| `k_r` | Number of candidates passed to Elim |
| `l_r` | Sum of monomial lengths across all stored phase terms |
| `v_r` | Number of currently active internal path IDs >= num_qubits |
| `d_r` | Number of phase polynomial terms |
| `w_redundant_estimated` | Saturating `max(k_r - 1, 0) * l_r` |

The final field estimates redundant phase scanning in the **historical
pre-Hoist Elim** implementation. It is not a measured operation count,
CPU/wall time, or verified speedup. Samples are collected before Elim
mutates its PhasePolynomial or variable set, and an attempt is recorded
whether or not elimination succeeds. WMC-only yields an empty list.

When `QUPRS_STAGE_LEDGER` is unset, the whole `stage_ledger` FFI
object is absent and no additional phase scans or sample allocations
are performed. Opt-in detailed records may grow large on long runs.
Rule-level exclusive timing and a predictive cost model remain future
experiments.


## Optional per-Elim rule-body clock (separate opt-in)

To compare pre-Elim `K/L/V/D/W_redundant_estimated` structure with individual
Elim operation time, enable **both** `QUPRS_STAGE_LEDGER=1` and
`QUPRS_ELIM_TIMING=1`. This adds an optional
`stage_ledger.elim_attempt_timings` array. Ordinary results and the existing
Stage Ledger JSON schema are unchanged when the second flag is unset.

Each timing record is `{structural_index, elapsed_ns, success}`. Indices refer
to `structural_elim_attempts`, success indicates whether Elim removed any
variable, and the monotonic Rust timer starts **after** structural feature
extraction and ends at the end of the Elim rule body (including its actual
phase-used-vars scan, candidate scan, mutation and bookkeeping). Thus
`elapsed_ns` excludes the extra `K/L/V/D` feature scans but includes
the timer's own `Instant` call overhead. This is a *perturbed measurement*,
not the uninstrumented counterfactual cost.

The sum of per-Elim times for nested `full_reduce` calls is contained within
the existing non-overlapping root-level `reduction` time; **do not add it**
to the root stage time. If a direct `try_reduce_elim` is called outside
`full_reduce`, its timer correctly exists but need not belong to any root
Reduction span. Timing outcomes are recorded both for successful and
unsuccessful attempts, with original sample ordering retained.

This remains a diagnostic-only research feature, not an adaptive scheduler or
a speedup claim. Compare off / structural-only / timed instrumentation on the
same binary and host to assess timing perturbation; evaluate family-grouped
generalization on *distinct circuits*, never count repeated runs of the same
structure as independent predictor training data.


## Optional candidate discovery / HH / Omega rule clocks

Set **both** `QUPRS_STAGE_LEDGER=1` and
`QUPRS_OTHER_RULE_TIMING=1` to add the independent
`stage_ledger.other_rule_timings` list. Normal runs and Stage-Ledger-only
runs have no new FFI keys or rule timers. `QUPRS_ELIM_TIMING` remains an
independent second opt-in specifically for Elim.

Each rule record contains `{rule, elapsed_ns, success, candidate_count,
within_reduction}`, where `rule` is one of `candidate_discovery`,
`hh`, `omega`. For discovery, `success` means at least one candidate
was returned; for HH/Omega it means that rule actually reduced a variable.
The `candidate_count` for discovery is **the returned count**, whereas
for HH/Omega it is the input candidate count. `within_reduction` captures
whether the guard began inside an active `full_reduce` root span; direct
rule calls outside this root remain visible but are not incorrectly added
to root reduction attribution.

All these clocks measure their own instrumented rule bodies and are
**nested in**, not additive to, the root Reduction wall. They include
clock/RAII overhead and exclude other rules. Together with opt-in
`elim_attempt_timings`, the observer can separate candidate discovery,
HH/Omega and Elim, but any residual root Reduction span also includes loop,
branch selection and dispatch. Do not treat independently activated timer
modes as exact uninstrumented counterfactuals. The enabled mode must be
benchmarked against matched Stage-Ledger-only mode on the same binary and
hardware before deciding if per-rule timer perturbation is acceptable.

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

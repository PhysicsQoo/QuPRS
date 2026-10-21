# Graphstate16 FFI gap and VQE4 solver-supervision provenance

Research-only opt-in profiler. The native verification algorithm, solver,
Reduction priority and precision are unchanged; ordinary result dictionaries
gain no new key unless `QUPRS_FFI_PHASE_TIMING=1`.

The opt-in Rust PyO3 result key `ffi_phase_timings` reports *disjoint* intervals
within the call:
- `qasm_extract_ns` = Rust input read / QASM parsing for both circuit inputs;
- `native_bridge_ns` = call from Rust PyO3 through native engine completion
  (includes Rust native verification and PyO3 allow_threads transition);
- `python_dict_build_ns` = Python result materialization total; its
  `stage_ledger_materialize_ns` subset isolates constructing Stage-Ledger
  dictionaries, including per-rule records.

`ffi_elapsed_excluding_phase_metadata_ns` is an internal FFI time snapshot
taken before inserting these diagnostic timings in the Python dictionary.
An independent Python `perf_counter_ns` wrapper includes this emission and
Python→Rust dispatch. It is never exactly equal to the sum of the three Rust
subsegments because of glue/clock overhead.

Graphstate16 uses both file-path inputs and exact-content inline QASM.
The Python inline file read preparation is measured **outside** FFI and the
Rust QASM parse is measured inside it. VQE4 uses file paths; Stage Ledger
separates `solver_supervision`, `reduction`, and other mutually exclusive
native stages. VQE4 truly launches GPMC (verify `solver_child_spawns=1`).

For Graph path / Graph inline / VQE path, interleave three modes under the
same source SHA, Rust wheel, GPMC SHA and CPU:
- control: Stage Ledger, no extra FFI or rule timestamps;
- ffi: Stage Ledger + FFI phase timestamps only;
- rules: ffi plus candidate-discovery/HH/Omega clocks.

Three warm-up triplets and 36 formal triplets per group produce 351 total
runs (324 formal). Each invocation uses a fresh child process; the exact QASM
input SHA, result hash/rule stats and Rust binary identity must agree across
modes. The original JSON, JSONL, environment, timing distributions,
source SHA and SHA256SUMS are retained. Failures are INCOMPLETE and upload
partial evidence. Negative or incoherent phase durations are rejected.

The two separate pairs address different questions: Graphstate16's former
+28% whole-FFI discrepancy cannot be assigned to native rule timers if most
extra time lies in Stage-Ledger→Python conversion. VQE4's large solver
supervision variability must not be called an FFI optimization; use paired
process/solver/run ratios and p10/p90 bands to identify it.

These results are descriptive on one GitHub-hosted machine; timestamps
include observer perturbation. Do not infer causal speedup, zero default-off
overhead or a production Reduction Scheduler policy from this experiment.

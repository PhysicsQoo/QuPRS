# Exclusive stage ledger — opt-in diagnostic

This experiment measures **disjoint stage intervals** rather than attempting
to add legacy, nested WMC timers. It does not modify the production
verification API, algorithm, solver selection or equivalence semantics.

## Inputs and execution

The pilot uses two representative circuits on one Ubuntu 24.04 / Python 3.12
runner with fixed CPU affinity: an existing QAOA7 QASM pair in Hybrid mode,
and a deterministic four-qubit GHZ circuit plus Z²=I in WMC-only mode.
Both use GPMC and the Proportional strategy, once per Python/Rust backend.

With the QuPRS development package installed, run the six solver-free
accounting contracts in test/test_exclusive_stage_ledger.py, followed by
the source-pinned runner in .diagnostics/stage_ledger/run_pilot.py.
The corresponding Actions workflow is manual-only. GitHub generally exposes
workflow_dispatch after its definition reaches the default branch normally.

## Python exclusive stage definitions

| Bucket | Measured interval |
|---|---|
| setup_parse | load_circuit, initialize, and get_gates calls inside the request |
| gate_processing_except_reduction | Strategy.run less top-level Reduction spans |
| reduction | Root apply_reduction intervals, without recursive double counting |
| cnf_encode_serialize | to_DIMACS encoding plus CNF output file |
| solver_spawn_wait_output | Bounded external subprocess spawn, wait, output and cleanup |
| solver_control_resolution_output_parse | run_wmc less nested subprocess supervision, including lock and parsing |
| wmc_classification | Actual classify_weighted_count call |
| other_unattributed | Wrapper walltime minus the known disjoint intervals |

Rust exposes only a **coarse partition**: pathsum/Strategy (Reduction
included), total WMC (all stages included), and wrapper/FFI/setup residual.
Fine-grained native stages, including actual native subprocess invocation,
are explicitly marked NOT_MEASURED. Legacy to_dimacs_time and tool_time are
nested metadata and are never summed with the coarse ledger.

All new timestamps use monotonic elapsed time. The residual ensures
arithmetic closure by construction; independent contract tests ensure
recursive Reduction time is not added repeatedly and reject material
negative residuals. Closure alone does not establish full attribution.
The child supervision duration is not the solver's CPU time.

The Python GHZ4 WMC-only test asserts that solver_process.run was called;
Rust solver invocation remains unknown. A sample failure, missing real
solver invocation, or Operator semantics mismatch causes a nonzero exit.

## Provenance, controls and limitations

The output retains the source SHA, GPMC submodule revision, Python package
versions, CPU affinity, circuit/QASM checksums, four individual JSON files,
summary.json, summary.md, samples.jsonl, and SHA256SUMS. It never claims
statistical significance: only one observation is run per case/backend.
Do not interpret the results as a Python/Rust speedup comparison.

The initial source-pinned real run completed with four valid Operator-oracle
classifications and six accounting-contract tests:
https://github.com/PhysicsQoo/QuPRS/actions/runs/39433230951
Artifact: https://github.com/PhysicsQoo/QuPRS/actions/runs/39433230951/artifacts/12269790631

All nine internal artifact SHA256SUMS entries were independently validated.
Subsequent documentation and workflow-trigger changes do not affect the
measured source implementation.

Missing future scope includes independent Rust stage timers for gate,
Reduction, CNF encoding, serialization, native solver lifecycle and
classification, followed by structural features K, L, V, D and W_redundant.
Those features are not part of this first pilot.

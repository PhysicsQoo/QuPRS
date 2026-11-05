# CodSpeed benchmark suite compatibility and retirement policy

Status: v0.14.0 published suite compatibility contract. This governs CodSpeed measurement
identities and history, not the public QuPRS Python/Rust API.

## Policy and releases

- v0.14.0: retain all **32 main-published Simulation URIs** and original
  source inputs, distributed across the same five shards. Add **12 QASM261
  CPU Simulation identities** (six source circuits × Python/Rust), for
  44 Simulation IDs total. Retain 30 Native Rust/core identities and
  ten full-Solver paired WallTime cases (nine existing Hybrid + one
  source-pinned QAOA7 Rust/GPMC WMC-only NEQ).
  Previously proposed extra solver-named CPU aliases were not released;
  simulation without subprocess tracking does not measure the GPMC/Ganak child runtime.
- v0.15.0: curated suite may become the default only after source/oracle,
  instrument and CI cost qualification. The complete legacy suite must remain
  runnable by opt-in and in periodic/release validation.
- v0.16.0: continue opt-in full legacy runs and source-preserved archive.
  Keep older SHA-v2 manifest/report ingestion compatible.
- v0.17.0: **last mandatory full-run-compatible minor release**; publish
  deprecation/retirement decision, source mapping and final benchmark snapshot.
- v0.18.0 or later: legacy automatic runs may be retired **only if** at least
  three successor stable minor releases after v0.14.0, 90 days of coexistence,
  at least two comparable new-suite release baselines, valid scientific/timeout
  evidence and resolved actual solver-inclusive end-to-end regressions exist.
  Otherwise extend the retirement window. Do not delete source QASM or the
  legacy URI, manifest v2 reader, historical provenance, or recorded baseline.

## Measurement identity

A benchmark identity specifies source and counterpart QASM hashes, method,
strategy, direction, backend, solver if invoked, tolerance contract, verified
execution stage, CodSpeed instrument, subprocess tracking flag, cold/warm
process scope, metric units, fixed run/source SHA, measurement suite version and
runner CPU cohort. Changing any of these in a way that changes benchmarked
work must produce a new benchmark ID and independently measured baseline.
Never call carried-forward CodSpeed values measurements at current HEAD.

The frozen legacy simulation SHA-256 is
`7eb82617bf092c81c6a6bde6e8cd05cec9bab71879f17b2bf315c9c420c7c8ed`.
Legacy five shards, 32 identities and no subprocess tracking remain as-is.
The current 12-URI QASM261 CPU cohort is additive inside the same five
shards. Its suite marker is `qiskit-2.6.1-opt0-v2-cpu` and its
identity SHA-256 is
`59d46eb951ca5280fddd19000ca14bfc45a71ea22717b178e76b76fd715e9a18`.
The manifest declares its suite version, count, and identity digest,
preventing a partial run from passing as original-32-only or complete-44.

The curated suite remains a distinct research candidate and is **not**
activated by merely registering its cases.

The SHA manifest v2 reader remains available; new runs may use v3 with
`suite_id`, `suite_version`, `suite_spec_sha256`, `measurement_scope`,
`metric_units`, `simulation_track_subprocess` and `runner_cohort`.
The migration compatibility module rejects missing fields, mismatched
instrument units, source/fixture revision mismatch and changed suite scope.
In a later integration phase, new CI reporters must use this module instead
of hard-coded 32/five-shard checks for the new suite; they must preserve the
legacy verification path and its original report schema.

## Future benchmark retirement

Replacement cases must preserve independent source oracles, correct
EQ/NEQ/timeout classification, original input provenance, bounded CPU and
memory workloads, and actual solver-inclusive CodSpeed coverage. A changed
instrument, fixture, solver-invocation stage or tolerance is a **new
benchmark identity**, not a comparable new version of the old measurement.

A future retirement of the legacy automatic suite must follow the
versioned coexistence and baseline requirements above. Keep the original
QASM fixtures and prior-run provenance accessible; a CI artifact with a
short retention window alone is insufficient historical evidence.

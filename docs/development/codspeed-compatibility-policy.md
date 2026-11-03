# CodSpeed benchmark suite compatibility and retirement policy

Status: updated for v0.14.0 controlled CodSpeed v3 PR #133.
The original research proposal and its pre-release benchmark migration are
distinguished from the active suite. This governs CodSpeed measurement
identities and history, not the public QuPRS Python/Rust API.

## Policy and releases

- v0.14.0: retain all **32 main-published Simulation URIs** and original
  source inputs, distributed across the same five shards. Add **12 QASM261
  CPU Simulation identities** (six source circuits × Python/Rust), for
  44 Simulation IDs total. Retain 30 Native Rust/core identities and
  ten full-Solver paired WallTime cases (nine existing Hybrid + one
  source-pinned QAOA7 Rust/GPMC WMC-only NEQ).
  The initial development-only proposal had 24 QASM261 CPU aliases
  (two Solvers × two backends × six circuits). The 12 Ganak-alias
  identities were retired *before release* because CPU Simulation
  does not measure GPMC/Ganak subprocess execution. Historical results
  remain archived under their original SHA and must not be relabeled
  as current-suite numbers. The larger curated corpus and v3
  manifest schema remain separate research candidates.
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

## Evidence-backed suite selection

Primary difficulty prior: TACAS 2026 Table 2 (36 normal-mode rows) and
Table 3(b) (random-rotation negative rows; Table 3 also includes WState32).
The historical 200-second timeout and Azure hardware are *not* comparable to
current CodSpeed timings. The source ledger is
`benchmarks/codspeed/paper_difficulty.json`; pinned source identity is in
`docs/development/paper-corpus-manifest.json`. Graphstate64 belongs to Table
2 and WState32 is a Table 3-only supplemental stress case.

Pilot selection must cover RR-only vs Hybrid/WMC-only, both Python and Rust,
true positive and independently established negative cases, GPMC/Ganak with
correctness/precision warnings, larger family instances, and resource-risk
classes. An unchanged compiler/solver-excluded CPU Simulation trace cannot
serve as the primary end-to-end verifier regression signal. Only CodSpeed
solver-inclusive WallTime measured on comparable base/HEAD source/runner
cohorts can resolve the current PR #131 performance hold. Dedicated
subprocess-tracked Simulation CPU is optional, bounded, and **not** WallTime.

For each candidate record `PILOT_NEEDED`, `NOT_MEASURED`, or a real CodSpeed
run ID with observed solver stage, verdict, source and instrument provenance.
Do not automatically promote the nine preliminary algorithm CPU candidates.

## Migration release gates

The following must pass before promoting the replacement suite: full
paper-table source set comparison, legacy 32/5 SHA unchanged, candidate
collection with no duplicate/missing URI, versioned dynamic-shard report,
v2/v3 ingestion tests, unmodified historical baseline, same-SHA CodSpeed
WallTime and independent source/verdict/precision checks, bounded CPU/memory
pilots and documented CI cost. GitHub artifact retention alone (some entries
currently retain only 14 days) is insufficient: archive a privacy-reviewed
source/manifest/run-URL/hash baseline snapshot in the existing benchmark
history or release assets, preserving the original service-run links.

PR #131's earlier performance hold was historical development context,
not a current merge gate on the separate PR #133 benchmark integration.
The PR #133 five-shard, ten-pair, and opt-in true ABBA contracts were
verified in Actions #41643926066 and #41645323941. P5 remains
observation-only; no unqualified percentage performance veto applies.

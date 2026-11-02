# CodSpeed benchmark suite compatibility and retirement policy

Status: phase-1 compatibility scaffolding, not a promotion of the curated suite.
Initial implementation: v0.14.0 development, PR #131. This document governs
benchmark measurement IDs and history, not the QuPRS public Python/Rust API.

## Policy and releases

- v0.14.0: maintain the legacy 32/five-shard Simulation suite unchanged.
  Introduce the curated suite and manifest schema v3 *in parallel*, using
  separate benchmark URIs and an independently measured CodSpeed baseline.
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
Legacy five shards, 32 identities and no subprocess tracking remain as-is
during coexistence. The curated suite is a candidate, **not activated** in
the regular workflow by merely registering the cases.

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

Until these gates and the independent CodSpeed failure are resolved, PR #131
remains Draft and must not be merged to dev.

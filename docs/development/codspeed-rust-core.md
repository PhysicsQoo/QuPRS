# Native Rust CodSpeed within the unified same-SHA experiment

As of v0.14.0 CodSpeed v2, the 11 native Rust core CPU benchmarks run
**inside the same GitHub Actions workflow and against the same HEAD SHA**
as the original 32-case five-shard Python-facing Simulation suite and the
paired Solver-inclusive WallTime suite.

The standalone workflow formerly named
`.github/workflows/codspeed-rust-core-pilot.yml` has been retired; its
independent benchmark crate at `benchmarks/rust_core` and checked-in
`Cargo.lock` remain unchanged.

- CodSpeedHQ/action v5 with `cargo-codspeed 6.0.0` and
  `codspeed-divan-compat 6.0.0`.
- The 11 stable native benchmark identities measure phase arithmetic,
  RR tolerance behavior and RR pipeline setup/execution. These are **not**
  complete source-to-Solver walltime, nor direct MPFR weight-encoding tests.
- Routine PRs and pushes collect CPU Simulation. Native Memory remains a
  deliberate `workflow_dispatch` option, on the exact same commit.
- The native job writes an exact-SHA manifest after a successful CodSpeed
  action and uploads its pinned lockfile. Because cargo-codspeed reports
  numerical measurements directly to the CodSpeed service, the GitHub
  manifest only confirms provenance/upload, not local numeric values.
- Cross-instrument synthesis is in
  `docs/development/codspeed-experiment-architecture.md`. Never infer an
  end-to-end Solver acceleration from an isolated native microbenchmark or
  report a native numeric metric as checked without verifying its CodSpeed
  run for the same SHA.

The former three-shard experiment is discontinued. All 32 original benchmark
URIs, their definitions and five-shard collection remain frozen.

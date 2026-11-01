# Native Rust CodSpeed CPU and Memory pilot

The historical 32-case `pytest-codspeed` Simulation suite is **immutable**:
8 Feynman RR-only identities and 24 MQT Hybrid identities. Do not clone them
into every instrument, rename them, or compare modeled CPU cycles to WallTime.

An independent benchmark crate at `benchmarks/rust_core` directly calls the
`pathsum` Rust library using the `codspeed-divan-compat` 6.0.0 integration.
The native benchmark functions never call Python/PyO3 or a Solver. No
production QuPRS Cargo manifest or original rust workspace lockfile is changed.

Initial benchmark scope: phase Clifford arithmetic, source-decimal and symbolic
phase arithmetic, complete native reduction construction+execution, and
RR-only native API at three tolerances. These are labeled honestly: the RR
pipeline includes setup, rather than claiming isolated per-rule costs. Expand
to direct CNF and adaptive MPFR weight generation only after bounded native
fixtures are validated; avoid accidental Solver invocation in microbenchmarks.

The opt-in workflow `codspeed-rust-core-pilot.yml` provides both CPU
Simulation and Memory instruments. Trigger deliberately by
`ci-codspeed-rust-core` on PR #131 or manually; do not count a configured
workflow as collected evidence until a real run passes and its identities
appear in CodSpeed. Simulation and Memory establish separate first baselines.
The standalone benchmark workspace initially resolves its own dependency
lock at build time; pin the generated `Cargo.lock` after the first successful
trial and before enabling the workflow on every affected PR.

For Memory, these allocations are in the Rust benchmark process; they are
not evidence of whole-GPMC/Ganak peak RSS. For system-level Solver cost,
continue to use bounded Solver-inclusive CodSpeed WallTime separately.

P0 WallTime correctness remains strict: any base/HEAD verdict class change
makes the pair performance-INCOMPARABLE. The instrument's raw values remain
visible but its change percentage is N/A; it cannot be counted as a speedup
or no-regression. Known Ganak print-resolution limitations retain a distinct
scientific warning instead of silently relaxing correctness.

## First real source-pinned pilot

PR `d7bba7cf6a2a10e22e6f3c39faef4722c04f7428` successfully compiled
the standalone Rust benchmark crate with `cargo-codspeed 6.0.0` and
`codspeed-divan-compat 6.0.0`. Both CPU Simulation and Memory benchmark
measurements were uploaded to CodSpeed (11 stable benchmark identities per
instrument). The initial GitHub job conclusions were FAIL **only in the
post-upload version-printing step**: `cargo codspeed --version` printed
`cargo-codspeed 6.0.0` but returned status 1. That optional command was
removed; the corrected workflow still requires an exact-HEAD CI pass.

The first measurements are a new baseline, not evidence of a speedup versus
the historical 32-case Python API suite. CPU Simulation reported
system-call dominance for the three native_rr_tolerance variants; these
should not be used as an end-to-end latency oracle. The generated benchmark
Cargo.lock is uploaded by the pilot for review, so it can be pinned before
automatic PR gating.

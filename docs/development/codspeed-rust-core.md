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

# QOO-157 same-input cross-language and distance-boundary pilot

This is an independent research branch based on the feature-gated Rust d4 PoC. It does not modify dev/main, default solver selection, release packaging or the original scientific tolerance contract.

The workflow .github/workflows/qoo157-d4-parity-boundary.yml uses one native d4 binary built from pinned upstream be15f91f3e9769e1f5cb175fa27e3eca3a1ea690 and an ephemeral GMP preparse 426-bit patch. No binary is bundled in this repository.

It SHA-checks six Rust-emitted weighted CNFs (Identity, H/T/H and Bell/T, each f64 and MPFR256 source weights), then sends their **identical bytes** to both:
- QuPRS Python run_wmc() with an explicitly registered d4-poc external adapter, and
- QuPRS Rust WmcManager::experimental_d4_count_prepared_cnf(), enabled only by experimental-d4.

The Python comparator compares exact printed rational counts and input SHA256 for each case, not rounded f64 counts; any source discrepancy, missing case, or conflicting count is a hard failure. It still labels numerical evidence as NOT_CERTIFIED for internal solver arithmetic.

An independent Rust example compares single-qubit P(theta) versus identity, with exact-decimal theta = 1e-8 and 4e-8 radians at QuPRS D_proj epsilon = 1e-8, against both d4 and incumbent GPMC. Analytically D_proj = |sin(theta/2)|, so these cases are on opposite sides of the tolerance. This is a scientific correctness guard, not a performance benchmark.

The feature is disabled by default. Current source precision policy is unchanged; a source f64 vs MPFR256 test is not automatically the same as internal GMP precision or a rigorous error certificate. Before any production PR: native/binary licensing, upstream-maintained configurable GMP precision, macOS/Windows, solver timeout/cleanup and CodSpeed same-runner base/HEAD.

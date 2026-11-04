# QOO-156 — bounded Rust cooperative cancellation experiment

Experimental branch: experiment/qoo156-rust-cooperative-cancellation
Parent dev: 79e975b0b21c0c650db7a76fe6e35b926c67c2c8
Scope: Rust verification request, not a new hard-process wall-clock guarantee.

## Implemented research contract

- PathSum holds an internal per-request monotonic deadline and a sticky
  deadline_exceeded flag. No global timeout, tolerance, or shared state.
- VerificationStrategy::run_with_deadline preserves the legacy ordering of
  Naive/Straightforward/Proportional/Difference and the existing automatic RR
  cadence. It polls before/after each gate and aborts gate traversal when the
  request's budget is exhausted. Legacy run() remains unaffected.
- full_reduce polls at entry, each Elim/Omega/HH scheduling step and the
  next reduction iteration; each candidate loop has a cancellation safe point.
  A partially simplified PathSum is NOT an equivalence verdict.
- CNF phase/ANF/trace encoding polls the same deadline and returns the existing
  typed SolverTimeout. The high-level request classifies that as Timeout,
  avoids launching the solver and never classifies an incomplete CNF.
- Existing GPMC/Ganak subprocess supervision from QOO-6 is reused; no
  replacement supervisor or new automatic solver fallback is introduced.

## Known limitations (must remain explicit)

- This is **cooperative**, not a provable hard wall-clock bound. One long
  QuantumOp.apply, polynomial substitution, a single high-precision phase
  conversion, or Myers diff computation can still occupy time between polls.
- No asynchronous Rust-thread termination is attempted. Hard whole-request
  termination would require a separately owned worker PROCESS and supervisor.
- A deadline that expires after all source work but before solver launch
  yields Timeout; it never promotes unknown/error to equivalent.
- Precision, RR tolerance, Hybrid residual, source angle and solver selection
  are unmodified; these must be checked with representative real circuits.
- Performance overhead is **NOT_MEASURED** until paired CodSpeed tests on a
  controlled cohort. Never infer a speedup from CI test durations.

## Scoped execution and evidence

Branch-only workflow: .github/workflows/qoo156-cancellation-pilot.yml

    cargo test --manifest-path rust/Cargo.toml --locked -p pathsum \
      --lib cooperative_ -- --nocapture

Control cases: Elim, HH, Omega and Hybrid final RR residual. The branch-only
workflow saves source/tree SHA, toolchain, test logs and source hashes.

Before a dev PR, still required:
1. Scoped tests and real QFT/QPE/Grover cancellation cases, including
   mid-request expiration, worker cleanup, no residual solver.
2. Negative tests for near-boundary Timeout versus EQ/NEQ and concurrent
   independent requests.
3. CodSpeed same-runner, same-SHA base/HEAD measurement for gate loop, RR,
   CNF and complete solver-inclusive paths; no fixed % performance gate.
4. Normal QuPRS CI compatibility and exact-HEAD review. No changes are
   merged or considered release certified by this experiment alone.

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

### Second-cycle deep cancellation (2026-11-04)

- The verification-only `BooleanState` substitution and `PhasePolynomial`
  substitution now poll within monomial products, arithmetic XOR subset DFS
  and phase reinsertion. They retain exact source angles and F2/XOR parity.
  Returning false marks the parent `PathSum` as canceled; its incomplete
  state is never classified as EQ or NEQ.
- The separately optimized **Bra-CX** path now polls during its exact
  monomial rewrite, instead of bypassing the request budget; its original
  fast exact algebra is preserved.
- The U-gate Bra substitution stops after cancellation; the SWAP 3×CX
  decomposition polls between sub-gates. Normalization, HH and Omega scans
  include conservative safe points.
- After RR, CNF, external solver, and numerical classification, the
  verifier rechecks the monotonic deadline before returning a verdict.
- Fresh controls cover exact fractional/radian phase preservation,
  synthetic exponential XOR cancellation, multi-qubit GHZ+T RR parity,
  independent concurrent requests, Bra-CX exact fast-path parity, and
  matched CNF bytes.

Source at the second-cycle scientific gate: `f4da97e5b9fb5d1d1e06b29a2ffffe26d644c30b`.
[Branch-only CI #41806670133](https://github.com/PhysicsQoo/QuPRS/actions/runs/41806670133)
passed **15/15 new cooperative + 4/4 existing RR/Hybrid controls**.
The follow-up workflow-only SHA `26b5bbda420a47de4e80e267ebd6217de68bc68d`
adds a full `cargo test -p pathsum --lib` suite and complete modified-source
hash ledger; its result must be checked independently, not inferred from
the narrower earlier run.
- Existing GPMC/Ganak subprocess supervision from QOO-6 is reused; no
  replacement supervisor or new automatic solver fallback is introduced.

## Known limitations (must remain explicit)

- This is **cooperative**, not a provable hard wall-clock bound.
  The remaining non-interruptible internals include single large
  `mul_boolean_polys` / ket-gate updates, general `PhasePolynomial AddAssign`,
  expensive phase coefficient arithmetic, QASM parse before entry, and Myers
  diff computation. Deep substitutions are now checked, but can still overrun
  between safe points. Do not treat a successful timeout status as a maximum
  real-time bound.
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

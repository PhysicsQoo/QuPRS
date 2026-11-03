# Real QASM Rust RR shared-XOR attribution (isolated experiment)

**Source**: Existing QuPRS MQTBench original/transpiled pairs: QFT16, QPE-exact8,
QPE-inexact8, VQE4, including the pre-existing QFT16 reversed pair direction.

## What is counted
The opt-in, non-default `pathsum/rr-xor-witness` Rust feature observes ONLY
`try_reduce_hh` after deleting the integration variable phase terms,
immediately before it substitutes `v`. Bra-gate substitutions are **excluded**.
It records real HH successes, affected phase-source count, XOR size, shared
fast-path hits, parity/exact-radian fallback hits, and bounded exact snapshots.
Count/hash evidence is printed in a Rust semantic test outside benchmarking.
No timestamps, wall clock calls, GPMC/Ganak subprocesses, or Python wrappers.

The collector is disabled in default builds via `#[cfg(feature = "...")]`;
even when built with the feature it records nothing unless `begin()` is called.
The entire pathsum remains scientifically exact; the witness test runs with
and without collecting and compares final P, F and HH successes.

## CodSpeed native CPU scope
- `*_miter_rr`: load QASM and clone operations in Divan setup, then run
  source-pinned real PathSum miter with automatic on-gate HH/Omega/Elim RR,
  followed by full_reduce. This includes gate application; **not** RR alone.
- `*_hh_phase_replay`: collect real HH pre-substitution P snapshots in Divan
  setup, clone all samples in setup, and execute only actual P substitutions
  inside timed CodSpeed Simulation. 4096 exact samples maximum. An empty
  or truncated sample set is stated, not projected as complete.
- Both use `rr_tolerance=1e-10`, no solver. QASM SHA256, qubits/gate count,
  HH attempts/successes and sample truncation are archived.

## Attribution policy
The preferred cost share is a real-QASM **CodSpeed Simulation flamegraph**
inclusive CPU cost of `PhasePolynomial::substitute_var_with_poly` divided by
the native `*_miter_rr` total CPU cost, with denominator explicitly including
gate execution and RR. The sampled replay / miter+RR ratio is a diagnostic
proxy only, never relabeled as a precisely measured share of RR proper.
If the flamegraph lacks symbols, report **NOT_CERTIFIED** for exact cost share.
Do not use local process elapsed time for performance comparisons. No
outside-Solver comparison or end-to-end speedup claim can be inferred here.

This is a standalone opt-in CI workflow, not one of the protected 32 legacy
simulation identities; documentation-only updates do not trigger any costly
benchmarks. Do not merge to formal PR #131 based solely on this experiment.

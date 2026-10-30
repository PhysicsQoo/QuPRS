# Path-sum → weighted CNF: experiment-only parity and precision study (2026-10-30)

**Source baseline:** PR #131 `f6ab474769027ec0817e6e51f3e330db45907e34`. This branch is not for release. It does not modify GPMC/Ganak.

## Evidence tiers

1. `scripts/experiments/cnf_semantic_probe.py`: bounded independent Gaussian-integer WMC oracle on ten tiny source-level *emulations* of the Python and Rust Tseitin encoders. The emulations are **not** native QuPRS executables.
2. `rust/pathsum/src/wmc.rs`: **experimental-only native change**, reserve all PathSum free path variables in the DIMACS map; old/new A/B selection available privately within native Rust test. Native test checks whether an orphan path variable doubles the satisfying assignment count, and reports same-runner encoding timing. Never merge this change without an end-to-end PathSum semantic analysis.
3. `scripts/experiments/weight_boundary_probe.py`: high-precision source-angle reference vs binary64 `sin/cos` and 17-digit serialized weights. Lexical QASM angles are **proxies**, not the fully converted PathSum phase coefficients. Timing is Python/maths emulation, NOT Rust/GPMC Walltime.
4. The experiment-only workflow `.github/workflows/cnf-weight-boundary-experiment.yml` executes one bounded Ubuntu native job with these standalone oracles and Rust tests; its results are not PR #131 release results.

## Bounded offline observations (non-native, executed once)

The exact-weight emulator agrees with direct WMC in 8 fixtures without orphan free path variables, using different Python-style and Rust-style Tseitin layouts. Two specially constructed orphan-path cases differ:

| Fixture | Direct weighted count | Python-style | Unmodified Rust-style | Rust-style with free-var reservation |
| --- | ---: | ---: | ---: | ---: |
| 1 input qubit + 1 unused path variable | 4 | 4 | 2 | 4 |
| 2 input qubits + 2 unused path variables | 16 | 16 | 4 | 16 |

This is a potential **missing free-variable multiplicity** in the lazy Rust DIMACS registration. It is **not yet proof that a reachable public QuPRS PathSum retains such an orphan variable**. A native Rust unit test on this branch checks the synthetic PathSum directly.

For a 16-qubit identity model, the Python-style compiler emits 0 clauses and the Rust-style compiler 32 tautological equality clauses. They have identical Boolean meaning, but performance differences need native measurement.

In a 15-angle high-precision reference sample, binary64 trigonometry followed by `{:.16e}` serialization has maximum complex-weight error `1.15997963468544183e-16` and unit-modulus drift `1.0666667297777773e-16`; eight of 15 have positive drift. The 34-digit approximation maximum absolute error was `5.55571477786810047e-35`. These errors straddle the normalized squared-magnitude margin `epsilon_D^2=1e-16` at `epsilon_D=1e-8`.

One bounded Python emulator run (medians including lexical angle parsing) took 11.32 μs per binary64 phase, 23.03 μs per 35-decimal-digit phase, and 42.41 μs per 90-digit phase. **Do not treat these as native Rust performance or cost estimates for the full circuit.**

## Candidate boundary architecture, not yet implemented

Retain exact source-radian fractions and symbolic π-cycle coefficients through the reduction and CNF Boolean encoding. At a *weight-only* boundary, calculate `exp(2πiP)` at selected precision without converting the source coefficient to `f64` and write enough decimal digits directly into GPMC weight lines. Keep the selected solver, Path-sum reduction, WMC normalization, external output parser, and **one Solver invocation** unchanged. Clifford cases may use algebraic special values; arbitrary angles need a tested high-precision implementation. Evaluate dependencies, source-to-weight fidelity, true-equivalent and negative-controls, and actual fixed-runner walltime before any production promotion.

## Latest PR CI investigation

PR #131 at `c55dc44`: Dev Fast 1181 passed / 2 failed; 12 native matrix jobs and Docker failed from the same test-instrumentation assertion `Native solver wrapper must capture its one CNF` in Rust Graphstate16/QFT16. The public Rust verifier had returned normally; the test wrapper failed to capture the CNF. WMC numerical evidence, Python CI, and CodSpeed succeeded. The failing capture code was removed from PR #131 in `f6ab474`, separate from this experimental branch; the standalone experiment does not rely on that interception mechanism. No external solver code was modified.

## Reproduction

```bash
python scripts/experiments/cnf_semantic_probe.py --rounds 1200 --json /tmp/semantic.json
python scripts/experiments/weight_boundary_probe.py --rounds 120 --json /tmp/weights.json
cargo test --locked --manifest-path rust/Cargo.toml -p pathsum experiment_free_var_contract -- --nocapture
```

All numerical results here are conditional observations. The branch must not be merged until native verdict parity, unchanged scientific correctness, and same-runner performance gates are satisfied.

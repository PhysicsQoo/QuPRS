# QOO-157 — Python/Rust native d4 printed-count parity

Evidence date: 2026-11-04. Research-only, NOT a release certification.

Both independent implementations executed pinned external
`jm62300/d4@be15f91f3e9769e1f5cb175fa27e3eca3a1ea690` with the
ephemeral **pre-parse 426-bit GMP initialization** fix, via their existing
QuPRS process-supervision contracts. The source CNF bytes are frozen by
the six-file SHA-256 manifest in the isolated adapter branches.

| Original QuPRS source CNF | Python native Adapter | Rust native Adapter | Exact rational printed parity |
|---|---|---|---|
| quprs_identity1.cnf | PASS | PASS | equal |
| quprs_identity1_mpfr256.cnf | PASS | PASS | equal |
| quprs_t1_miter.cnf | PASS | PASS | equal |
| quprs_t1_miter_mpfr256.cnf | PASS | PASS | equal |
| quprs_bell_t_miter.cnf | PASS | PASS | equal |
| quprs_bell_t_miter_mpfr256.cnf | PASS | PASS | equal |

**Result:** The componentwise difference between the *exact rational
representations of printed real and imaginary counts* from Python and
Rust was **zero for all six inputs** (not merely <1e-25).

Reproducible evidence:

- Python installed-package `run_wmc(..., "d4-poc", preserve_count=True)`,
  scoped [CI 41810985081](https://github.com/PhysicsQoo/QuPRS/actions/runs/41810985081),
  artifact 13312362865, `native-python-adapter.json`. Its count/oracle
  pilot gate is 6/6 PASS, arithmetic_certified=false.
- Rust `WmcManager::solve_with_deadline_distance_printed_precision_prepared`
  using the feature-gated `d4-poc` adapter and existing supervised
  subprocess, scoped [CI 41812025526](https://github.com/PhysicsQoo/QuPRS/actions/runs/41812025526),
  artifact 13313495481, `rust-d4-native-oracle.json` and
  `rust-d4-native.log`. Rust printed-decimal vs Fraction oracle 6/6
  PASS; arithmetic_certified=false.
- Original six QuPRS-generated f64/MPFR256 CNF inputs and source SHA:
  [CI 41807195090](https://github.com/PhysicsQoo/QuPRS/actions/runs/41807195090)
  artifact 13310272992. Both adapter CIs independently validate the
  same six input hashes before execution.

Method of comparison: for each matching filename, convert Python's
`observed_decimal_exact` pair and Rust's `rust_d4_printed` pair into
Python `fractions.Fraction`, then compare both components for exact
equality. This was performed against the downloaded original CI ZIP
artifacts, not inferred from success-status badges.

**Limits:** Both language bindings use the *same* external solver binary
logic, so this is a transport/parsing parity result, not two independent
model-counting algorithms. Counts still lack a rigorous bound on internal
GMP arithmetic error, on source-angle approximation, and on projected
distance verdicts. None of these tests proves an arbitrary-circuit EQ/NEQ
boundary decision. No default solver switch or d4 binary distribution
is authorized. Eventual performance conclusions require CodSpeed,
not ad hoc GitHub Actions wall-clock times.

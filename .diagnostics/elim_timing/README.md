# Six-family per-Elim elapsed-time research pilot

Run the standalone `Rust Per-Elim Cost Six-Family Pilot` Actions workflow
against this Draft PR's exact source SHA. This is an isolated research
measurement, not a Reduction algorithm, solver, scheduler, or CI runtime-gate
change.

`QUPRS_STAGE_LEDGER=1` enables the existing structural K/L/V/D/W samples.
`QUPRS_ELIM_TIMING=1` (also requiring Stage Ledger) adds
`stage_ledger.elim_attempt_timings`, an aligned array of
`{structural_index, elapsed_ns, success}` observations.

Measurement begins after structural feature extraction, ends after the
Elim rule body. All Elim intervals are **nested** in root Reduction walltime.
The nanosecond-valued timer is perturbed by its own Instant overhead; values
cannot be interpreted as uninstrumented ground truth.

Six different official MQTBench families (QAOA7, QFT16, Grover4, VQE4,
Graphstate16, GHZ32) use the project's established verification strategy and
direction with one GPMC binary, fixed CPU affinity, 1 warmup and 8
interleaved repetitions in each of two modes:

- structural-only: Stage Ledger ON, Elim clock OFF
- timed: same Rust build, Stage Ledger ON, Elim clock ON

The workflow saves raw individual JSON, environment and QASM/GPMC SHA256
identities, semantic and structural parity, each timer-to-snapshot alignment,
nested stage accounting and descriptive paired bootstrap intervals.
Incomplete/incorrect experiments fail explicitly and still preserve artifacts.

Do not treat eight repeated samples as eight distinct circuit structures.
Assess structural diversity across the six families before attempting any
hierarchically grouped statistical analysis. Any predictive model must be
validated on held-out circuit families and compared against a constant-time
baseline, not tuned on the same exact Elim events.

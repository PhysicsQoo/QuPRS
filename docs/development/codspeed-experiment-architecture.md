# CodSpeed source-pinned benchmark and instrument contract

The routine [CodSpeed workflow](../../.github/workflows/codspeed.yml)
uses **five** CPU Simulation shards, a same-SHA native Rust CPU track,
and, for qualifying pull requests, paired Solver-inclusive WallTime
with source-pinned BASE and HEAD. Optional diagnostics require explicit
manual or controlled opt-in triggers.

Current v0.14.0 benchmark identities include the immutable **32 legacy**
Simulation node IDs plus **12 additive QASM261** CPU identities
(**44 total**), **30 native Rust/core** identities, and **10 paired**
Solver-inclusive WallTime cases. The active registry, case source hashes
and shard checker are the executable source of truth; deliberate coverage
migration requires new benchmark IDs and a versioned baseline.
See [compatibility/retirement rules](codspeed-compatibility-policy.md).

| Evidence family | Instrument | Meaning |
| --- | --- | --- |
| Five-shard CPU Simulation | CodSpeed Simulation, solver subprocess tracking disabled | Host-side modeled CPU; not full Solver elapsed time |
| Native Rust/core | cargo-codspeed / CodSpeed Simulation | Native RR/phase microbench cost; no Python-to-Solver process path |
| Solver-inclusive paired | CodSpeed WallTime | Full source-to-verifier-to-GPMC/Ganak execution, including subprocess launch and I/O |
| Optional solver CPU, native memory, cross-method | Explicit workflow-dispatch jobs | Research axes; separate units and admission requirements, not routine merge gates |

## Source and measurement integrity

Check out the immutable event HEAD, not a synthetic PR merge commit. For
paired jobs, record the comparison BASE SHA and build isolated environments
while using identical declared QASM inputs. Preserve solver submodule version,
dependencies, toolchain, runner, stdout/verdict and provenance metadata.

Each CodSpeed action writes source-identity evidence. The
[aggregator](../../scripts/report_codspeed_cross_instrument.py) must join
only results from the same workflow run and matching exact source SHA.
Missing/duplicate shard nodes, wrong instrument units, mismatched solver or
missing required evidence fail closed.

The legacy 32-node identity hash is
`7eb82617bf092c81c6a6bde6e8cd05cec9bab71879f17b2bf315c9c420c7c8ed`.
The additive QASM261 suite identity is separately versioned. Never relabel
earlier carried-forward source metrics as new measurements.

## Scientific and performance boundaries

Science correctness, evidence-collection completeness and performance
interpretation are distinct. Record the direction, EQ/NEQ status, RR/WMC
stage, precision warnings, actual Solver invocation and source oracles
before comparing elapsed measurements. `PRECISION_LIMITED`, missing
provenance and timeouts are not successful scientific certificates.

Simulation modeled CPU, native-core CPU, Solver-inclusive WallTime and
sampled RSS are not additive, and must not be treated as common elapsed
time. Cross-host or unmatched cohort observations remain
`PERFORMANCE_INCONCLUSIVE` until independently qualified.

Additional investigations use the existing workflow manual parameters
(`base_sha`, solver CPU, native memory and cross-method flags);
do not create duplicate routine jobs to reproduce the same stages.
See [performance evidence policy](codspeed-performance-policy.md)
and [benchmark testing](benchmark-testing.md).

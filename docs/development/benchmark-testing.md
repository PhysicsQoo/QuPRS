# Benchmarking and reproducibility

QuPRS keeps correctness, experimental resources and measured performance
as separate evidence. Timeout, memory exhaustion and solver precision
limits are **not** equivalence certificates or timing samples.

## Correctness and source inputs

The versioned QASM corpus in `benchmarks/` and the original benchmark
identity definitions in `test/` are source-controlled. Representative
checks:

```sh
python scripts/paper_corpus_audit.py
python scripts/check_codspeed_shards.py
pytest test/test_backend_semantics.py test/test_solver_failure_matrix.py
```

The legacy **32** CodSpeed Simulation node IDs stay stable across five
shards; the v0.14.0 suite also includes **12** source-pinned QASM261
Simulation identities, for **44** Simulation identities total. Native
Rust/core and solver-inclusive measurements use their separate
benchmark definitions. Any material change to fixture, instrument,
strategy, backend, solver invocation or tolerance requires a new
benchmark identity or explicitly qualified baseline migration.

## Performance

Use the project's [CodSpeed workflow](../../.github/workflows/codspeed.yml)
for measured algorithmic performance. CodSpeed Simulation without
subprocess tracking does **not** measure the full GPMC/Ganak solver
child-process path; solver-inclusive WallTime has different units and
cost boundaries. Never add or subtract those results or compare
unmatched runner, CPU, toolchain, source SHA or QASM cohorts as if they
were controlled A/B measurements.

For a numerical timing conclusion, record exact source/fixture IDs,
method, backend, solver, requested precision, verdict, executed stage,
CodSpeed mode and comparable runner cohort. Code-correctness CI and
performance conclusions require separate inspection; the absence of
a reliable performance sample does not establish zero regression.

## Optional resource observations

For memory and timeout experiments, use the resource observer outside
CodSpeed's timed code:

```sh
python scripts/profile_benchmark_resources.py \
  --case grover4 --walltime-seconds 90 \
  --solver-timeout-seconds 45 --memory-limit-mib 3072 \
  --output grover4-resources.json
```

`sampled_peak_tree_rss_mib` is a sampled process-tree total, **not**
a guaranteed instantaneous peak or an exact memory limit. An incomplete
resource experiment never licenses a positive scientific claim.

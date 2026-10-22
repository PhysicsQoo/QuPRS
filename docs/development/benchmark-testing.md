# Benchmark inputs, correctness tests, and resource profiling

The benchmark files in this repository serve three different purposes.
These purposes are **not** interchangeable.

| Purpose | Existing entry point | Runs a solver? | Required for each PR? |
| --- | --- | --- | --- |
| Paper input integrity | `python scripts/paper_corpus_audit.py` | No | Cheap, source-sensitive checks only |
| Small correctness and error handling | `pytest test/test_backend_semantics.py test/test_solver_failure_matrix.py` | Yes, bounded | Via existing pytest CI |
| Representative elapsed-time benchmarks | `test/test_MQT.py`, `test/test_Feynman.py` | Yes | Via existing Benchmark/CodSpeed workflows |
| Full publication reproduction | Original complete paper input corpus | Yes, potentially very expensive | No; use a controlled, comparable machine |
| Process-tree RSS profiling | `scripts/profile_benchmark_resources.py` | Yes, isolated | No, opt-in until actual runner measurements pass |

## Case catalog

`test/_benchmark_cases.py` contains the **six MQT and four Feynman** cases
that were already present in CI. Each family has a small representative
circuit. Do not add every size in a family merely to increase a count.
Changing case names, order, strategies, or source/target direction can also
change pytest benchmark node IDs and CodSpeed shard assignments. Such a change
requires explicit baseline and five-shard collection review.

`docs/development/paper-corpus-manifest.json` records immutable QASM input
identifiers from the original repository snapshot. It is a **static input
inventory**, not evidence that any circuit was proved equivalent. It keeps
MQT Table 2 separate from the Feynman comparator and extra inputs. The paper
prose/table row-count discrepancy is recorded, not silently fixed.

The helper in `test/_benchmark_outcomes.py` is deliberately called
**outside** `benchmark(generate_test, ...)`. It keeps status handling
consistent without changing measured code. `Timeout` and `MemoryOut` fail the individual benchmark execution, both
under correctness CI and `--benchmark-only`, with an explicit resource-limit
reason; they are never reported as skips or equivalence successes. Separate
small fail-closed tests still provide independent semantic controls.

## Memory and time

Do not time memory sampling inside a CodSpeed benchmark; sampling threads,
process checks and logging can change the performance result. Run the
resource observer in a **separate process** and save JSON evidence:

```shell
python scripts/profile_benchmark_resources.py \
  --case grover4 --walltime-seconds 90 --solver-timeout-seconds 45 \
  --memory-limit-mib 3072 --output grover4-resources.json
```

The observer includes the parent and its live solver descendants, and kills
its process group when the configured wall-time or sampled RSS cap is crossed.
The recorded `sampled_peak_tree_rss_mib` is a **sampled** aggregate across
processes, not exact peak virtual memory, solver-only peak, or a rigorous
upper bound. Short-lived subprocesses may be missed. An incomplete run is a
failed pilot, never an equivalence proof or an accepted performance sample.

Promote a new benchmark case to automatic CI only after it passes on the
**actual runner class**, with source and solver identities recorded, under a
fixed end-to-end time and memory budget. Repeat on the same runner class
before interpreting time/RSS deltas. The original Azure machine and GitHub
hosted runners must not be compared as if they were identical hardware.

The benchmark comparison remains report-only for timing regressions on shared
runners. Numerical or resource uncertainty must not be converted into a
positive semantic verdict.
## Legacy performance history during workflow migration

The `benchmarks` branch and its `main_baseline.json` / `main_baseline.provenance.json`
remain the existing historical baseline source. This change does **not**
remove or change the baseline-producing workflow, saved history, or PR
reporting. An immutable reference for the transition inventory is:

- `benchmarks` snapshot commit: `0051d5e25696a118401b3dbc07762ecf7f6c2f42`
- `main_baseline.json` Git blob: `694555bdaba51b75a93a6cf927bebf32256bfb28`
- `main_baseline.provenance.json` Git blob: `99b7bfe73f0a256c881363c6798b73368cd14f9a`

Later snapshots may differ as normal baseline updates continue. Preserve the
historical artifacts and provenance before disabling or removing the old
benchmark workflow. Simulation metrics are not direct measurements of solver
wall-time, system calls, or sampled peak memory.

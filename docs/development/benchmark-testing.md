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
consistent without changing measured code. `Timeout` and `MemoryOut` are
recorded as resource-limited skips, **not correctness successes**; separate
small fail-closed tests remain responsible for actual semantic acceptance.

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
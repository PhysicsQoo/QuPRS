# CodSpeed benchmark experiment architecture

Status: **pilot specification**. This document defines measurement scope, controls, and release gates. The solver-inclusive experiment must be validated and baselined before it becomes a required check. The existing core benchmark history is retained.

## 1. Questions and distinct metrics

A single number cannot represent all of QuPRS's performance.

| Experiment | Measure | What it cannot claim |
| --- | --- | --- |
| Core CPU Simulation | Python/Rust verifier and its native reduction/CNF work; `simulation-track-subprocess: false` | End-to-end performance or actual external solver cost |
| Solver-inclusive CPU Simulation | The verifier **and** external GPMC/Ganak child processes; `simulation-track-subprocess: true` | Time spent waiting in system calls/I/O, or user-observed elapsed time |
| End-to-end CodSpeed WallTime | Full verification request, including process startup, solver execution, and wait/I/O | Deterministic per-function CPU costs |
| Optional memory diagnostics | Explicitly defined allocation or process-tree RSS scope | An all-process peak RSS when only Python allocations are instrumented |

Simulation yields **modeled CPU cost**, not elapsed seconds. The CPU model excludes system-call time. WallTime on an ordinary shared GitHub runner is exploratory; formal elapsed-time regression acceptance requires an eligible, verified stable CodSpeed Macro Runner or a qualified equivalent setup using CodSpeed. See https://codspeed.io/docs/instruments/cpu and https://codspeed.io/docs/features/macro-runners.

An experiment that excludes solver processes cannot be the sole basis for a QuPRS end-to-end performance signoff.

## 2. Baseline identity and historical migration

The existing `test/test_Feynman.py` (4 cases x 2 backends) and `test/test_MQT.py` (6 circuits x 2 backends x 2 solver selections) contribute **32 currently collected benchmark identities**. The latter uses Hybrid: selecting a solver does **not** establish that the solver ran.

Preserve the historical `test/test_Feynman.py` and `test/test_MQT.py` names/results as **host-process-only Simulation v5**. Do not silently change their subprocess setting and compare them to the old values. Historical CodSpeed dashboards may carry skipped benchmarks from earlier CI runs; the number shown by a comparison is not necessarily the number measured on that commit.

Start a *new*, stable benchmark URI namespace for the solver-inclusive suite, e.g. `test/test_codspeed_solver_cpu.py::test_solver_cpu_inclusive[...]`. Never compare CPU Simulation with WallTime; never compare subprocess-disabled with subprocess-enabled Simulation as if they share a baseline. Changing runner major version, counting scope, algorithm method, material precision defaults, or fixture SHA starts another baseline epoch.

A main->dev->PR study must name all three immutable SHAs, not merely branch labels. Main->dev and dev->PR comparisons answer different questions.

## 3. Workload design

**Core reduction**: Retain the 8 Feynman RR benchmark identities (Python and Rust). Existing MQT Hybrid host-only identities remain as host-cost diagnostics, not pure RR benchmarks when they reach WMC.

**Hybrid with real Solver**: A bounded first-stage matrix covers QFT16, QAOA7, VQE4, and Grover4, both GPMC/Ganak and Python/Rust where the selected fixture actually reaches WMC. Parameter identity includes circuit, reduction strategy, backend, solver and method. One invocation of the requested solver per verification; no automatic precision retry or replacement solver. The pilot has dedicated IDs and checks `wmc_solver_invoked is True` **after** the instrumented operation.

**Hybrid RR-fast / mixed path**: GHZ32 and Graphstate16 exercise a complementary `solver_invoked=False` path when applicable. Graphstate16's RR/WMC choice and verdict can vary with tolerance semantics; it cannot be classified as a matched solver workload across versions. Report user-observable end-to-end latency separately when semantics are independently acceptable.

**WMC-only isolation**: Later add a small source-pinned WMC-only fixture with actual nontrivial CNF and expected external solver invocation. Avoid the analytically solved identity shortcut, which deliberately has `wmc_solver_invoked=False`. Do not include unbounded QFT/WMC-only without a feasibility gate.

**Scientific controls**: All measured positives require `equivalent` or `equivalent*` under the relevant public contract; include independent source-pinned near-equivalent and negative controls in correctness CI (not time-based certification). `not_equivalent` for an independently positive pair, `unknown`, Timeout, MemoryOut, unexpected absence of a solver, a solver format error, or a wrong negative result are **not** performance PASS events. Do not silently skip or rebaseline those outcomes.

## 4. Standardized execution/provenance

Record the exact repo commit/tree, QASM fixture SHA256, method, strategy, direction, backend, selected solver, solver binary hash/version where available, GPMC submodule SHA, Ganak artifact identity, Python/Rust compiler and libraries, tolerance values, effective print precision, result verdict, RR approximate status, and `wmc_solver_invoked`. Record GPMC/Ganak precision warnings as annotations, not as an independent second equivalence classifier.

Benchmark the public API with source-pinned inputs. Exclude package installation, building, and benchmark collection from measured spans. Warm up each executable using the *same policy for every revision*, but document that a solver invocation during warmup is a separate research execution, not a production verifier retry. Avoid arbitrary output printing, Qiskit dense-matrix oracles, SHA calculations, filesystem inventory, and repeated solvers **inside the measured operation**. Perform correctness and provenance assertions after `benchmark(...)`.

Use a finite, explicit timeout for each benchmark. The previous `999999` CodSpeed-only timeout is not a reproducible experimental contract: a benchmark that hangs must have a bounded outcome, marked inconclusive rather than treated as a slow successful sample. Keep the same timeout across revisions within an experiment.

Use the actual source precision defaults for ordinary cases; a 90-digit GPMC experiment is a separate benchmark identity from default 30 digits. Do not change Ganak/GPMC source merely to make benchmarks pass.

## 5. CI topology and budget

1. **Routine PR**: existing sharded Core Simulation (5 shards, 32 collected IDs) and *after pilot passes* a small solver-inclusive CPU Simulation suite on source/Rust/solver/fixture changes. Path-filter docs-only changes. No duplicate full Release-Ready or repeated numerical evidence on every documentation push.
2. **Before release, or explicit opt-in**: expanded solver-inclusive CPU matrix, same revision/toolchain/solver provenance and a solver-stage conformance gate. Pin source SHAs and track actual solver invocation for each case.
3. **Main/dev baseline and release candidate**: CodSpeed Macro Runner WallTime for representative whole-request benchmarks. Macro Runner availability, architecture, and both solver binary compatibility on Linux ARM64 must first pass a native preflight. Do not automatically substitute shared-host WallTime for formal evidence if Macro Runner cannot be provisioned.
4. **Exploratory three-revision comparison**: same-host main/dev/PR CodSpeed WallTime may guide diagnosis but must retain its shared-runner warning and source/path metadata. Keep it out of release-gating until the environment is qualified.
5. **Memory**: separate opt-in analysis with explicit process-tree instrumentation; CodSpeed Python allocation measurements alone do not establish solver subprocess RSS.

Benchmark selection should emphasize diverse path behaviors (RR termination, Hybrid solver invocation, different CNF sizes, Python/Rust, GPMC/Ganak) rather than many sizes from a single circuit family. The pilot should be bounded before expansion.

## 6. Validity gates and regression decisions

For each comparison, verify:
- Identical benchmark semantic identity, QASM bytes, method, direction, strategy, selected backend/solver and precision controls; record source revision separately.
- Successful source correctness, scientifically consistent verdict, and required execution stage; stage transitions are flagged before any component-level speedup/regression statement.
- Matching Simulation coverage (`simulation-track-subprocess`), instrumentation major version, cycle estimation, allocator policy; inspect linked libraries, CPU architecture, toolchain and solver artifact changes.
- CodSpeed's own measurement issues (system-call dominance, missing profiles, non-Macro WallTime), complete benchmark coverage, and whether a result was actually measured rather than carried forward by partial runs.
- Per-case performance, plus clearly identified aggregates **within a single instrument and comparable cohort only**. Never mix MQT, RR, solver CPU and WallTime into one percentage. Use geometric means only for matched, semantically comparable case sets, and publish individual regressions.

Initial thresholds are **not numeric release gates** until variance and platform stability are measured. Calibrate per-case thresholds from repeated CodSpeed baseline runs. A sharp change triggers source-path and differential-flamegraph inspection; semantic failures or missing required measurements block acceptance independently of timing.

## 7. PR #131 rollout

- Pilot: add a small, **distinctly named** solver-inclusive CodSpeed Simulation benchmark file and an opt-in PR-specific workflow; do not replace or rebaseline existing tests.
- Verify actual subprocess trace (process names/PIDs), solver invocation, correctness, and CPU profile for both GPMC and Ganak.
- Check x86_64 CodSpeed collection and cost before enabling a permanent always-on solver CPU matrix; then establish first `solver-inclusive-v1` dev/main baseline.
- Test Macro Runner availability and ARM64 GPMC/Ganak compatibility before a permanent WallTime workflow. Do not claim it has been verified until a real CodSpeed Macro run exists.
- After signoff, remove PR-specific diagnostic workflows and consolidate long-lived performance CI; maintain separate benchmark identities per measurement contract.

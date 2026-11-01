# CodSpeed benchmark experiment architecture

Status: **routine dual-instrument collection enabled**. Five-shard CPU Simulation and bounded paired Solver-inclusive CodSpeed WallTime now run on every PR. Extended subprocess CPU Simulation and qualified Macro Runner variance-calibrated release thresholds remain separate decisions. Historical benchmark identities are retained.

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

1. **Every PR**: existing five-shard CPU Simulation and a bounded, same-host paired CodSpeed WallTime suite (seven representative Hybrid Solver/backend cases, two source revisions). This includes docs-only PR updates by explicit policy. The optional subprocess-inclusive CPU Simulation pilot remains separate. No duplicate full Release-Ready is needed merely to collect these two instruments.
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


## 7. Required per-PR CodSpeed instruments

**Simulation** retains its existing five-shard 32-identity benchmark contract,
with `simulation-track-subprocess: false`. It is a modeled CPU-cost
measurement, not real Solver latency.

**Solver-inclusive WallTime** is a distinct, always-on CodSpeed v5 job
(`pr-solver-inclusive-walltime`) in the same workflow. It checks out each
PR's immutable base and HEAD commits on the **same GitHub hosted runner**,
builds independent Python/Rust environments, and measures seven bounded
Hybrid workloads across Rust/Python and both GPMC/Ganak. The test harness
invokes the source-specific public API in a child Python process and includes
Solver execution, startup, blocking/waiting and I/O in the CodSpeed timed
interval. Source installation/building and provenance checks are not timed.

The fixed cohort uses Rust VQE4/GPMC, QFT16/GPMC, QAOA7/GPMC, VQE4/Ganak,
Grover4/Ganak and Python VQE4/GPMC, VQE4/Ganak. Each case has stable `base` and `head` benchmark IDs.
Both source revisions use **identical HEAD QASM input files** while code
is built from its own exact commit. Verdict, stage invocation, strategy,
solver, source SHA and benchmark provenance are attached as metadata.
The benchmark deliberately fails if the requested Solver never ran or
returned an inconclusive/error outcome; known VQE4/Grover4 Ganak printed-
precision negatives are explicitly labeled external Solver limitations,
not scientific correctness PASS. Such point estimates remain timing-only; silently timing an RR-only shortcut
as GPMC/Ganak latency is not scientifically comparable. A test-level
process-group timeout terminates parent and solver descendants together.

The two instruments must not be merged into one time statistic. Shared
GitHub-hosted paired WallTime provides useful *exploratory* matched-runner
evidence, not a qualified fixed Macro Runner. CI success is a collection
and validity gate; numerical regression thresholds still require
runner-variance calibration and matching scientific outcomes. The WallTime test also writes source/solver/verdict provenance **after** CodSpeed
timing. A pytest session hook exports the CodSpeed instrument's own
minimum/median, variance, and rounds. CI validates all seven base/HEAD
pairs, stage and solver parity, source SHA, fixture identity, and normalized
equivalence classification. The paired percent-delta table is published
to the job summary as Markdown and JSON artifacts. No independent
timing framework is introduced; a known Ganak printed-precision negative
remains a timing-only external limitation, never scientific equivalence PASS.

An **opt-in three-shard Simulation candidate** is isolated in
`.github/workflows/codspeed-three-shard-trial.yml`. The default five-shard
workflow remains unchanged. The trial is gated by the
`ci-codspeed-three-shard` label and checks exact 32-node coverage with
no loss, duplicate, or changed benchmark IDs. Initial weights derive from
CodSpeed v5 Simulation modeled CPU costs at `95f8942` and are **only**
placement proxies, not elapsed-time performance measurements. Promote
the design only after three-shard CodSpeed and Actions evidence confirms
full coverage and acceptable CI queue/runner cost.

The more expensive PR #131 three-revision `main/dev/head` WallTime
and optional solver-inclusive CPU Simulation diagnostics remain manual.

## 8. Historical PR #131 pilot rollout

- Pilot: add a small, **distinctly named** solver-inclusive CodSpeed Simulation benchmark file and an opt-in PR-specific workflow; do not replace or rebaseline existing tests.
- Verify actual subprocess trace (process names/PIDs), solver invocation, correctness, and CPU profile for both GPMC and Ganak.
- Check x86_64 CodSpeed collection and cost before enabling a permanent always-on solver CPU matrix; then establish first `solver-inclusive-v1` dev/main baseline.
- Test Macro Runner availability and ARM64 GPMC/Ganak compatibility before a permanent WallTime workflow. Do not claim it has been verified until a real CodSpeed Macro run exists.
- After signoff, remove PR-specific diagnostic workflows and consolidate long-lived performance CI; maintain separate benchmark identities per measurement contract.

## 9. Legacy CI de-duplication

`.github/workflows/benchmarks.yml` retains its automatic `main`-push
historical `pytest-benchmark` baseline writer. The duplicate PR comparison
is now `ci-legacy-benchmark`-label opt-in, while routine CodSpeed CPU
Simulation (32 node IDs) and Solver-inclusive WallTime remain active. Do not
delete `benchmarks` history or compare old pytest elapsed-time baselines to
CodSpeed v5 CPU cycles.

## Independent source QASM oracle for known Ganak output limits

PR WallTime now runs an **unmeasured** Qiskit complex128 operator source
cross-check on the 4-qubit Grover/VQE QASM inputs and writes fixture hashes.
It is a numerical cross-check, not a rigorous `1e-8` distance certificate.
When an actual Ganak process returns a near-equivalent source pair with
an `unknown` printed-resolution diagnostic, an observed resolution coarser
than the user's distance, and a `not_equivalent` midpoint, the paired
evidence becomes `PRECISION_LIMITED` rather than silently claiming a
comparable speedup or scientific equivalence. Its percent delta remains N/A.
All other unexplained verdict shifts remain FAIL; no solver is rerun, patched,
or reclassified. `PRECISION_LIMITED` is explicitly **not** PASS for source
exactness or solver numerical certification.

## Controlled same-host cross-method experiment

The opt-in diagnostic reuses the existing ci-pr131-walltime label without
changing the canonical 32 benchmark IDs, introducing branches or touching
Solver source. Separate base/HEAD Python/Rust installations share one GitHub
runner and the exact same HEAD QASM fixture hashes. The new CodSpeed URI
namespace covers six MQT families, two Solvers and two backends across base
and HEAD (48 WallTime identities). A limited Rust VQE4/QAOA7 GPMC/Ganak
base/HEAD sample (8 CPU Simulation identities) requests subprocess tracking.

The provenance audit separates request execution cost, solver-stage cost
eligibility and scientific verdict parity. Base and HEAD request execution
cost can be compared despite a Ganak verdict difference, while this MUST NOT
be called a verified-equivalence speedup. A change between RR-only and WMC
remains visible and disallows a solver-stage speedup assertion. Distinct
default tolerance semantics across versions, if any, remain disclosed.
Only CodSpeed instrumentation supplies timing; the audit never guesses times.
WallTime on a shared hosted runner remains exploratory.

CPU subprocess instrument contract: source-paired CPU Simulation explicitly
sets the verifier Solver timeout to 300 seconds for **both base and HEAD**
(to bound Valgrind slowdown), and an outer process-tree timeout of 390 seconds.
Standard and cross-method CodSpeed WallTime retain the original 90-second
Solver deadline. Timeout is recorded and checked in the paired provenance.
The two instruments have distinct workloads/deadlines and must not be
interpreted as matching elapsed-time measurements. The shared pytest hook
exports WallTime results only and must not abort Simulation at sessionfinish.

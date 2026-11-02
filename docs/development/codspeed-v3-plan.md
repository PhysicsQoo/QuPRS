# CodSpeed v3 phased update and scientific/timeout acceptance

This plan is additive to [codspeed-experiment-architecture.md](codspeed-experiment-architecture.md).
It does **not** modify the five-shard original 32 benchmark identities or the
v0.14.0 verifier algorithm. P0/P1 are source-only, deterministic artifacts. The first P3 microbench
increment is included but is not complete coverage.
The P2 pilot is opt-in and **not** a certified performance comparison.

## P0 — archived difficulty vs current measurement

\`benchmarks/codspeed/paper_difficulty.json\` transcribes screened TACAS
Table 2 and Table 3(b) circuit families under the historical Azure E8ads v5
8-vCPU / 64-GiB Python experiments. Timeout was 200 seconds in the artifact.
The archive does not include measured current QuPRS v0.14 Rust performance.
A historical time is only a candidate **difficulty prior**.

Every mapping row carries an archived fixture and \`positive_hybrid_seconds\`,
a historical negative rotation column when transcribed, a candidate tier,
and explicit modern fields (\`modern_codspeed_run_id\`,
\`modern_solver_stage\`, \`modern_verdict\`, \`modern_memory_risk\`).
Missing values stay UNVERIFIED/NOT_MEASURED, never promoted by inference.
The two current versions' absolute numbers must never be subtracted.

## P1 — one registry and frozen original 32

\`benchmarks/codspeed/case_registry.py\` owns the 7 current Solver-inclusive
WallTime identities, the 7 distinct subprocess-CPU identities, optional
cross-method cells and candidate pilot fixtures. Existing harnesses and both
report scripts import this source; they no longer copy independent tables.
The historical 32 original IDs remain owned by \`test/_benchmark_cases.py\`,
with five shards and SHA256 checksum unchanged. New IDs are additive only.

## P2 — bounded manual pilot

\`test/test_codspeed_candidate_pilot.py\` uses eight small positive-candidate
circuits and a fresh verifier subprocess. The test reads the exact HEAD QASM
and records stage/verdict and independent watchdog status. A source-specific
15s Solver timeout and 24s parent process-group watchdog are **pilot bounds**,
not universal production settings. Once a source has timeout/solver mismatch,
its result is CENSORED or NEEDS_SCIENTIFIC_REVIEW, not speedup evidence.
The CodSpeed WallTime action is the **sole timing authority**.

Use workflow_dispatch on the existing CodSpeed workflow with
\`pilot_only=true\` and explicitly selected commit. Routine five-shard and
paired PR jobs are skipped in this pilot-only mode to save CI resources,
and its output is an isolated pilot evidence artifact.
The default PR workflow remains fully intact.

Promotion requirements for a candidate: independent scientific fixture and
expected verdict, real Solver invocation for Solver-inclusive category,
finite completion in appropriate budget on current CodSpeed cohort,
and cross-backend/solver semantic comparability. Raw pilot completion does
not automatically promote an example into an every-PR performance gate.

## P3 — native and Python core expansion

Retain original eleven native Rust identities; first-stage implementation
adds three decimal PhaseCoeff hash-load cases (repeated/unique/mixed), for
fourteen native IDs total. These hash cases do NOT measure MPFR from_phase or
WMC encode_trace directly. Further MPFR/CNF/HH/Elim/omega workloads remain
planned and require source-semantic confirmation before admission. Five
source-based pure-Python CPU cases cover ANF F.sub() and HH/Elim matcher
paths in an opt-in same-SHA lane, with no Solver. Do not add all unqualified
cases to every PR at once.

## P4 — true exact-SHA numerical join

GitHub's pytest-codspeed CPU Simulation export does **not** contain modeled
CPU timing (CodSpeed runner collects those values). Case-only output is not
a numeric cross-instrument measurement. A v3 report must ingest CodSpeed's
*actual same-SHA run result* using authorized read API and mark native CPU
values REMOTE_PENDING until fetched; the existing GitHub cross-check is
provenance and coverage only. Each common case has separately typed
host CPU / solver CPU / end-to-end WallTime / native profiler hotspot,
plus solver stages, verdict and context. Missing = MISSING, changed verdict =
INCOMPARABLE, timing cap = CENSORED_TIMEOUT, no mixed-unit subtraction.

## P5 — variance and gate acceptance

No 1–2% walltime decision from just 3 shared runner rounds. For routine
surveillance, choose modest measured rounds by an actual CodSpeed budget.
For promotion or borderline regression, use counterbalanced paired A/B
blocks and variance/CI, ideally stable Macro Runners, and preserve each
individual iteration's scientific provenance. A timeout from either side
is a censored observation: never substitute the timeout cap into ratios.
GPMC/Ganak precision warnings prevent scientific promotion, even if timing
collection succeeds. Never weaken MPFR or RR/WMC tolerances to make benchmarks
pass. Distinguish SCIENCE, COLLECTION and PERFORMANCE acceptance.


## Restricted GitHub connector: one-shot PR metadata pilot trigger

For environments where the GitHub connector cannot perform
`workflow_dispatch`, the existing PR can trigger the same opt-in pilot
without a new branch or worktree. Temporarily append
`<!-- quprs-codspeed-v3-pilot -->` to the PR description. The
`pull_request.edited` event runs only the `candidate-pilot` job; ordinary
five-shard Simulation, paired WallTime, native Rust and cross-check jobs are
skipped on metadata-only events. This job pins the actual PR HEAD, not the
synthetic merge commit, so the code SHA does not change when the marker is
added. Remove the marker only after its CodSpeed run ends. The cleanup edit
will not collect performance data.

This path is opt-in, one-shot and scientifically exploratory. Because the
candidate pilot runs one measured round, it can screen feasibility and timeout
but cannot certify variance or a 1–2% regression. The pilot records original
and transpiled QASM SHA256, solver/watchdog caps, verdict, observed Solver
invocation and explicit censored statuses, including SOLVER_TIMEOUT and
WATCHDOG_TIMEOUT. It does not promote candidates automatically.

## P2b — same-SHA four-case five-round CodSpeed comparison (opt-in only)

Following the independent QNN4 and VQE8 full-matrix numerical oracle in
the source-pinned paired WallTime workflow, a **new opt-in** repeatability
lane contrasts *two Solver-invoked Hybrid fixtures* (QNN4 and VQE8) and
*two RR-terminated Hybrid fixtures* (QPEexact8 and W-state4). Both RR
fixtures are independently checked as source-pair Qiskit operators outside
the timed window. The original 32 identities, five shards, routine seven
paired Solver-inclusive cases, and current Rust native 14 remain frozen.

To execute exactly once without connector access to workflow_dispatch,
append `<!-- quprs-codspeed-v3-repeatability -->` to the existing PR body.
That PR-edited run starts **only** stage-repeatability, and does not trigger
the expensive normal five-shard suite. The job checks out actual PR HEAD,
verifies four QASM pairs with independent Qiskit Operator, runs CodSpeed
WallTime five rounds with bounded 15s Solver / 24s process-group watchdog,
and audits **all observed function invocations**, including warmup, for
unchanged verdict, method stage and process status. A once-per-case JSONL,
the first-party CodSpeed WallTime export, oracle JSON, report JSON and
commit/submodule manifest are preserved in a single artifact.
Remove the hidden marker after the experiment reaches a terminal state.
This cleanup metadata edit must skip all performance jobs.

The scope is full fresh Python subprocess startup + circuit conversion +
Rust/Python execution + optional GPMC + I/O; these measurements **cannot**
be interpreted as isolated solver time, and a side-by-side comparison across
different circuit structures is not an algorithmic speedup or regression.
One hosted runner, five CodSpeed rounds, and a non-Macro Runner warning
provide **variance screening**, not certified performance acceptance.
Do not use source-operator complex128 numerical consistency to mark the
external Solver's printed-count arithmetic precision certified.

## P3 — direct native WMC input boundary measurements (added)

The native `benchmarks/rust_core/benches/core.rs` now includes eight
**distinctly named, solver-free** WMC/MPFR/CNF microbenchmarks. These
complement, rather than rename, the existing 14 Rust CPU tests; native
source registry now has 22 identities. The original canonical 32/five
Simulation shards and seven paired Solver WallTime identities are unchanged.

A fixed eight-term `PathSum` uses the same eight unique Boolean monomials
and identical output functions in both repeated and unique decimal
source-phase cases. The input-phase fixture, exact decimal parsing and
one prepared MPFR manager are initialized through `OnceLock` outside
the measured spans. The following measurements intentionally separate:
- `wmc_trace_cnf_unweighted`: unweighted encode_trace and CNF generation
- `wmc_trace_f64_repeated` / `wmc_trace_f64_unique`: f64-boundary
  phase-weight generation and CNF encoding
- `wmc_trace_mpfr96_repeated` / `_unique`: source-exact 96-bit
  MPFR weight generation and CNF encoding
- `wmc_trace_mpfr192_repeated` / `_unique`: deliberately tighter
  192-bit request, not a default policy
- `wmc_dimacs_mpfr96_unique`: serialization of a pre-encoded CNF,
  excluding `encode_trace` and MPFR weight generation from the timed call.

These are synthetic microfixtures with identical CNF shape per phase
category; results reveal hotpath and repeated source-angle opportunities,
but are not full-circuit throughput or GPMC arithmetic certification.
The shipping Rust algorithm, MPFR precision-selection policy and external
solvers are unchanged. Only CodSpeed is the accepted timing instrument.

## P4/P5 — sourced metric coverage and a non-certifying variance report

The same-SHA external CodSpeed numeric importer checks both the three
CPU Simulation / Solver-inclusive WallTime overlapping sources and **all
22 native Rust IDs**. It refuses cross-SHA, unverified/carry-forward,
duplicate, missing model/unit or invalid numeric measurements, and
retains a separate MISSING_NUMERIC row for every unfetched native ID.
The service has not provided a supported automated read API credential
to the GitHub workflow; the importer remains explicit-input, not a
fabricated build log CPU metric or an automatic GO.

The paired seven-case Solver-inclusive WallTime report now also
preserves **both CodSpeed round counts, mean, median, stdev and CV**
separately for base and HEAD. It does NOT alter the historical min
delta in existing reports. A new `report_codspeed_variance_gate.py`
runs **after** the CodSpeed measurement and semantic auditor,
emits `paired-walltime-sampling.json`, and appends a per-case
sampling table to the GitHub summary.

This P5 report is deliberately non-certifying:
- No universal performance regression percent is set without real
  same-case repeated A/B and stable cohort data.
- A raw median ratio is exploratory; neither summary stats nor an
  unpaired coefficient-of-variation estimate is a valid matched
  confidence interval.
- A verdict mismatch, stage change, timeout or unqualified external
  arithmetic error blocks comparability; numerical values remain
  diagnostic, not replaced with the timeout cap.
- Hosted non-Macro Runner experiments remain NOT_CERTIFIED even if
  the 3 measured rounds are stable. Only CodSpeed supplies timing.
- Preserve actual QASM and method/solver/backend/tolerance/precision
  identity, and arrange counterbalanced A/B blocks before a formal
  performance gate.

Existing seven paired WallTime identities and canonical 32/five shards
are unchanged. Performance GO/NO-GO calibration remains QOO-165.

## P5 — opt-in same-case paired seven-round A/B screen

The normal PR CodSpeed suite preserves its original 32 IDs/five shards and seven
paired Solver-inclusive WallTime identities at three instrumented rounds.
The P5 diagnostic duplicates neither identity set nor everyday test workload:
it is triggered one time by the PR-description marker
`<!-- quprs-codspeed-v3-ab-pilot -->` on `pull_request.edited`, and only
the `p5-ab-screen` job runs (all expensive normal jobs skip metadata-only edits).
On one hosted runner it builds exact dev base SHA and current PR HEAD SHA,
selects four **matching circuit/settings** from the existing seven:
`qaoa7_gpmc`, `qft16_gpmc`, `vqe4_gpmc`, `vqe4_gpmc_python`,
runs CodSpeed WallTime with seven rounds per revision, and applies
source-SHA/fixture/provenance/solver-invocation/exact-verdict checks.
The subset option in the existing paired report is opt-in; normal seven-case
coverage remains strict. The variance reporter accepts a declared expected
case count (four for pilot, seven for every-PR).

The resulting seven-round distributions are **exploratory**. CodeSpeed
round samples are not a counterbalanced block-level distribution, and no
stable Macro Runner is guaranteed. The scientific judgment and real Solver
invocation are required, but do not certify external Solver printed arithmetic
bounds. The default allowed regression threshold remains **unset** and
`performance_status=NOT_CERTIFIED` until independently measured baseline
noise, stable runner cohort, and counterbalanced base/HEAD blocks support a
scientifically defensible per-case threshold. Do NOT calculate speedup when
verdict labels differ, nor mix CPU Simulation with WallTime.

After the pilot job finishes and evidence is saved, remove only that PR body
marker. The cleanup metadata event must skip all performance jobs.

# CodSpeed v3 phased update and scientific/timeout acceptance

> **Current PR #133 strategy (2026-11-03):** retain **32 legacy +
> 12 QASM261 CPU** simulation URIs across five shards, **30 Rust Native**
> identities, and **10 paired Solver-inclusive WallTime** cases per PR.
> The earlier three-block/five-round P5 opt-in prototype has been retired;
> the only current ABBA job is the validated **2-case × 4-block,
> single-invocation ABBA/BAAB** opt-in. Its results are observational,
> not a performance release gate. See
> [CodSpeed formal policy](codspeed-performance-policy.md).
>
> Sections below describe *dated prior research plans* and should not
> be interpreted as a current seven-pair or 24-URI release policy.



## 2026-11-02 P5 observation-only policy (historical seven-pair snapshot)

P5 does **not** set any fixed regression percentage, performance pass/fail
threshold or release-blocking GO/NO-GO. Keep the existing seven same-case
base/HEAD Solver-inclusive CodSpeed WallTime observations on every PR.
Report actual medians, relative changes, round distributions, CV, source
identity, Solver stage, scientific verdict and precision warnings.

**Interpret observed direction without claiming statistical significance.**
An unqualified hosted-runner noise model or absent independent A/A cohort is
an explicit **nonblocking interpretation caveat**, not a reason to suppress
a valid measured delta or to alter a numerical equivalence verdict.
Source-inconsistent workloads, missing measured statistics or unverified Solver
execution remain unsuitable for paired comparisons; never invent ratios.
Independent source-witness-supported Ganak print-limit cases retain
**conditional timing comparability** even when verdicts differ, without
scientific reclassification.

Any future formal performance threshold, independent A/A campaign or Macro
Runner qualification is **optional research, outside current P5 acceptance**,
not a prerequisite for PR merging, release, or reading observed deltas.
Existing five Simulation shards, original 32 identities and seven routine
WallTime pairs remain unchanged.


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
- An **unexplained** verdict mismatch, stage change or timeout blocks
  workload comparability. A source-oracle-supported Ganak printed-resolution
  mismatch retains a **conditional timing** delta but not a scientific PASS
  or a certified performance gate. Timeout caps are never treated as samples.
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
scientifically defensible per-case threshold. Never present a changed-verdict
conditional timing delta as certified speedup; never mix CPU Simulation with
WallTime.

After the pilot job finishes and evidence is saved, remove only that PR body
marker. The cleanup metadata event must skip all performance jobs.


## Ganak verdict change: independent science and conditional performance

A cross-revision `equivalent*` → `not_equivalent` is NOT automatically a
reason to discard measured Solver-inclusive WallTime. Comparing **runtime**
and certifying **numerical correctness** are separate claims. In the observed
source-pinned Grover4/VQE4 Ganak cases, both revisions invoked Ganak for the
same fixture, solver, strategy, backend and input orientation. The PR's
`wmc_printed_verdict=unknown` and
`wmc_precision_reason=ganak_point_estimate_resolution_limited` are supported
by the independent Qiskit full-operator source witness, while the printed
resolution distances (~7.34e-5 and ~1.16e-4) are far above the configured
1e-8 projective-distance tolerance.

For this **strictly evidenced** case, paired reports now retain an actual
base/HEAD CodSpeed timing delta as `CONDITIONAL_GANAK_PRINT_LIMIT`,
mark `verdict_comparable=false`, preserve both raw verdicts and warnings,
and keep `scientific_status=PRECISION_LIMITED`. The P5 sampling audit
shows the same-case timing delta and CV but **blocks performance
certification**: external arithmetic is unproven, base tolerance provenance
is not identical, and hosted-runner variance is unqualified. No
reclassification to `equivalent*` is inferred from the measured duration or
the complex128 source oracle alone.

If the source-operator witness, real Solver invocation, matching fixture/
settings, documented output-precision limitation or numeric width/tolerance
relationship is missing, changed verdict still means
`BLOCKED_UNEXPLAINED_VERDICT`; it is not whitelisted on a family name
alone. No new tolerance override, exactness demand or Solver modification is
introduced. Other P5 source-matched, same-verdict candidates remain
`SAME_VERDICT` and all original 32 IDs, five shards and seven daily
paired Solver-inclusive cases remain unchanged.

## P3 Python native algorithm microbench: bounded first-party CodSpeed

The five already-defined Python-only fixture IDs (ANF target absent/present,
HH pair match, Elim match/no-match) are run from the current exact PR source
through an isolated, opt-in CodSpeed CPU Simulation lane. Trigger this lane
once by temporarily appending `<!-- quprs-codspeed-v3-python-core -->` to
PR #131's description, then remove the marker after the exact-SHA run
finishes and the first-party artifact is preserved. No Python/Rust algorithm
or canonical 32 benchmark is changed. Python fixtures are initialized
outside instrumented functions; Python CodSpeed is the only accepted timer.

## P4 complete inventory of source-pinned metrics without fabricated CPU data

The cross-instrument GitHub evidence contains all 32 canonical Simulation
URIs and all 22 native Rust identities. The numeric importer separately
checks same-SHA CodSpeed service values for each original 32, native 22,
optional Python 5 and three same-fixture CPU-vs-Solver-inclusive WallTime
pairs. Missing values always remain `MISSING_NUMERIC`; unrelated Ganak
precision limitations never reclassify the three GPMC matched CPU cases.
Each benchmark's CodSpeed runner grade and CPU model must be sourced rather
than inferred from the GitHub job name. GitHub manifest now includes actual
CPU model and runner image version if available. The GitHub Actions artifact
for cargo-codspeed Simulation contains identity/provenance rather than
CodSpeed's modeled CPU time: there is NO valid reason to copy over a
historical model estimate or silently substitute a timing from logs.
Until an authenticated CodSpeed service read API is available within the
workflow, service metrics are separately retrieved and normalized through
the existing `join_codspeed_numeric.py` contract; automated service
collection is an explicit external integration limit, not a scientific
or correctness issue.

## P5 true single-round ABBA/BAAB (replaces the original pilot)

The original four-case × three-block × five-round-per-position program
was a **block-interleaved research pilot**, not a true interleaving of
individual Solver calls. Its active test fixture, reporter, and dedicated
unit tests were retired before PR #133 integration. The research code
and original measurements remain in Git history and CodSpeed records.

The current opt-in `p5-abba` job runs QAOA7 Rust/GPMC **Hybrid and
WMC-only**, each in four balanced blocks (ABBA, BAAB, BAAB, ABBA),
for **32 distinct CodSpeed WallTime single-round positions**. Each
officially timed position invokes the complete verifier/GPMC subprocess
exactly once. The known additional unmeasured target-return call from
`pytest-codspeed==5.0.4` uses a cached result, never a second Solver.
The four explicit prewarm calls are separately recorded. Scientific
guards check every NEQ result, source SHA, QASM hash, numerical contract,
Solver invocation, and exact 32-position execution schedule.

[Final PR #133 ABBA Actions #41645323941](https://github.com/PhysicsQoo/QuPRS/actions/runs/41645323941)
passed 32/32 official rounds and real GPMC calls. Max within-run A/A
baseline drift was **7.78% Hybrid and 17.58% WMC-only**; effects changed
sign across blocks. Therefore `P5 NOT_CERTIFIED` is the only supportable
performance conclusion on a shared GitHub Hosted Runner. Exact opt-in
activation rules are in the [formal policy](codspeed-performance-policy.md).
Historical source and measurement provenance are preserved, but the old
48-identity opt-in protocol must not re-enter routine CI.

## P3 final native RR rule-specific CPU isolation

The native core registry preserves its original 22 IDs and adds **exactly
three** separately named Rust reduction-rule attempts: `rr_elim_direct`,
`rr_hh_direct`, `rr_omega_direct`. Divan `Bencher::with_inputs`
generates the complete, reduction-ready PathSum and candidate list outside
the measured span. Each timed closure calls only the selected concrete
`try_reduce_elim`, `try_reduce_hh`, or `try_reduce_omega` (plus
mandatory outcome check), not the whole gate-construction pipeline.
The existing `rr_hh_pipeline` and `rr_nonclifford_pipeline` remain
untouched and separately interpretable. Native total becomes 25; original
32 Python benchmark IDs, 5 shards, 7 paired Solver-inclusive cases,
and 5 Python-core identities remain unchanged. The new Rust IDs have no
historical base; do not call their first CodSpeed results a speedup or
compare them with differently scoped pipeline CPU times.



## P4/P5 follow-up — official CodSpeed read capability and fail-closed evidence (2026-11-02)

The official CodSpeed GitHub Action is a **measurement uploader**, not an
authenticated download API for all platform-side modeled CPU values. CodSpeed's
public pricing lists the Performance Data API as an Enterprise capability;
a general-purpose, officially documented and authorized read credential for
this project's GitHub CI has not been established. OIDC permission to **upload**
benchmark data does not establish a permission to **read** service metrics.
Do not reverse-engineer private GraphQL endpoints, scrape an authenticated
browser session, infer undocumented scopes, or put personal auth tokens in CI.
CodSpeed MCP can provide an authorized human-reviewed read of actual service
runs, but it is not an unattended GitHub Action input. If CodSpeed grants an
official supported read API later, verify its documented scope, the project
entitlement, the service response/run identity and CI secret-handling protocol
before implementing an automatic importer.

Until then, the existing manual source-verified normalized service export
feeds `join_codspeed_numeric.py`. Source SHA, run ID, directly measured flag,
runner mode, unit and CPU model remain mandatory. A Simulation CPU time must
have a time unit and a Memory observation a storage unit; contradictory
instrument/unit pairs fail closed. All expected overlap, native, original and
optional Python identities must have actual numeric values to claim full
external numeric coverage. A verdict-incomparable row can carry its numeric
measurement for diagnosis, but it does **not** satisfy scientific
cross-validation. Source-independent GPMC rows are not invalidated by a
separate Ganak precision-limited verdict. Missing numbers stay explicit; no
performance GO is inferred.

For P5, each source-pinned ABBA case must keep the identical QASM hash pair,
method, backend, Solver, strategy, source fixtures and verdict **across all
blocks**, not only within a block. The A1/A2 drift observed within the same
GitHub-hosted execution is descriptive, not an independently replicated
A/A runner-noise distribution; the report records an explicit zero independent
A/A cohort count. Continue collecting seven same-job paired Solver-inclusive
CodSpeed WallTime cases on every PR. Qualify an empirical threshold only
after independent A/A cohorts with stable hardware/runner metadata, enough
repetitions and a separately reviewed confidence procedure. A Ganak printed
precision-limited mismatch with independent source witness remains eligible
for **conditional same-workload timing**, but never automatic scientific
reclassification or performance release certification.

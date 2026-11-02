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

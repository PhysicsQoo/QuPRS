# TACAS 2026 — isolated historical QuPRS CodSpeed design

Status: **OPTIONAL PERFORMANCE EXTENSION — NOT PART OF ARTIFACT REPRODUCTION ACCEPTANCE** (2026-11-02).

**Priority correction:** the TACAS Artifact experiment is primarily a
**CI scientific reproducibility and numeric WMC evidence preservation**
project, *not* a historical performance benchmark project. Its success
criteria are original QuPRS verdicts, GPMC raw outputs, normalized numeric
provenance and source-locked correctness data that can inform later
tolerance design. The 184-case source evidence is already archived.
`docs/development/tacas26-wmc-tolerance-evidence-contract.md` is the
controlling document for this primary objective.

**CodSpeed is optional and secondary.** If performance becomes a separate
research question, follow the standalone design below. It must not
replace, relabel, or block historical CI-science evidence, and no
CodSpeed run is needed to archive existing WMC values.
Scope: historical QuPRS **v0.9.1 only**, direct original-source science
reproduction, original QASM pairs, native GPMC. No QCEC, Quokka-sharp,
PyZX or Feynver competitor benchmarks.

## 1. Two non-interchangeable datasets

**Historical lane** (THIS document):
- Source ref: `e928abc47dd15926364ec77905eb0d5dc92ce8cc`.
- Paper artifact ref: `d8d3e7da555e9e20bdec6f3abe4a13ad899af62b`.
- Existing 184 scientific call identities, 37 derived same-Hybrid RR cells.
- Existing Git archive: `docs/development/tacas26-results/`.
- New CodSpeed URIs MUST start with `tacas26_hist_v091_` and live in
  `benchmarks/tacas26_historical/` with a dedicated
  `tacas26-historical-codspeed.yml` workflow, **not**
  the regular `.github/workflows/codspeed.yml` registry.
- Every measured row carries target source SHA, GPMC binary SHA256,
  original and counterpart QASM hashes, case/method, version lock,
  Python/compiler/OS, runner class and CodSpeed run URL.
- All historical source times are recorded as historical-source evidence,
  and are NEVER inferred from unrelated modern CodSpeed runs.

**Modern performance lane** (OUTSIDE this document):
- `dev` / PR #131 / v0.14.0 HEAD and base/HEAD CodSpeed experiments.
- Its own case IDs, runner, mode, tolerance and solver provenance.
- No automatic regression gate or numeric percentage difference across
  historical v0.9.1 and modern dev/PR data. Cross-version investigation
  is an *additional, explicitly named* same-fixture and same-runner
  study, requiring semantic comparability first.

Do not promote the 46 numeric historical-paper Hybrid reference times
from `benchmarks/codspeed/paper_difficulty.json` as CodSpeed measurements:
they were published on Azure E8ads v5 (8 vCPU, 64 GiB), not recorded
on the current runner. In the already archived source cohort **zero of
184 native durations were serialized**; the rest are not recoverable from
individual GitHub Actions job durations.

## 2. Measurement population: historical-case *subset*, not 184-by-default

Register the 184 official direct-call IDs as immutable science metadata,
but select a **12–20-case fixed historical benchmark cohort** from the
existing source results. The first pilot should cover at least:
- RR-terminated positive Hybrid: GHZ32, Graphstate16, QPEexact8.
- Hybrid requiring GPMC: representative QFT16, QAOA7, QPEinexact20
  only when original source evidence confirms a determinate return.
- WMC-only: GHZ32 and at least one modest QFT/QAOA example that
  the historical source run completed.
- Random_Rotation negative: GHZ32, QPEinexact8 or similarly bounded
  case with a returned not_equivalent verdict.
- Feynman RR-only: tof_3, one adder and one multiplier of bounded size.

These are **candidates, not guaranteed fast cases**: confirm expected
method stage and 2026 original-source status from the permanent archive
before activation. Prefer cases that finish well below 200 seconds.
Preserve the 36 previously sampled historical cases as metadata, not
automatically as mandatory CodSpeed benchmark identities.
The published Table 2 RR result is **derived from the same Hybrid run**;
do not execute an extra RR-only verification for that column.

Selection policy: small/bounded cases become repeatable WallTime
benchmarks; near-timeout and huge cases remain science-only censored
records unless an isolated opt-in study is explicitly requested.
Add identities only after an opt-in source pilot and a stable runner
decision. Never mutate legacy `main` CodSpeed IDs or include old dev-only
exploratory IDs in the release backward-compatibility set.

## 3. Explicit timeout semantics (scientific vs measurement)

| Result | Science record | CodSpeed timing use |
|---|---|---|
| Original verifier returns determinate verdict before 200 s | RETURNED + exact label | Eligible for WallTime sample if the benchmark invocation completes |
| Verifier itself reports `Timeout` under 200 s `signal.alarm` | ORIGINAL_SOLVER_TIMEOUT, record literal `>200` if returned | **Do not** record 200.0 s as a real measured duration; exclude from numeric performance averages |
| Verifier reports `MemoryOut` | ORIGINAL_MEMORY_OUT | Exclude from completed-case timing statistics |
| Process group killed by external 215 s watchdog | EXTERNAL_WATCHDOG_CENSORED | Incomplete, exclude numeric timing; retain 215 s lower bound only as censoring metadata, not a walltime observation |
| Process exits with no raw JSON | MISSING_RESULT | Incomplete, no timing sample |
| QuPRS source verdict disagrees with expected determinate verdict | SCIENTIFIC_REVIEW | Preserve raw evidence, do not automatically equate timing result with scientific PASS |

**Three distinct limits must not be conflated:**
1. `source_timeout_s=200`: original v0.9.1 API's verification
   timeout; preserve its behavior, never increase it to force completion.
2. `external_watchdog_s=215`: per-*single original verification
   invocation* process-group safeguard; on expiration kill the process
   group including GPMC children, reap it and record censoring.
   It is NOT a measured Solver time.
3. `codspeed_max_time` / `max_rounds`: warmup/iteration scheduling
   budget, **not** a timeout for the verifier and not a substitute for
   the process-group watchdog. A job-level Actions timeout is a fourth
   operational safety ceiling; it must cover setup plus all invocations.

WallTime frameworks may execute a benchmark multiple times even when
the test source only calls the fixture once; the 200/215 s protection
must be **inside every single iteration**. Use an explicit one-iteration
first pilot, `warmup_time=0`, `max_rounds=1` (subject to testing that
pytest-codspeed honors the settings), and then only raise rounds for
known-short stable cases. Avoid unbounded automatic warmup/iterations.

For determinately completed cases, a strict harness validates its
verdict *after* the measured invocation and exports status. For a
predictably censored case, skip the numeric CodSpeed benchmark and
store a science-only timeout record. For an unexpected timeout during
measurement, mark that invocation `INCONCLUSIVE_CENSORED` and reject
the numeric benchmark sample; never turn it into a scientific
`not_equivalent` or a successful 200-second performance result.
A benchmark execution failure is a measurement-integrity failure,
not necessarily a quantum-equivalence regression.

## 4. Instrumentation and provenance

Primary instrument: **CodSpeed WallTime** for complete original QuPRS
Python + native GPMC subprocess execution. Do not compare these numbers
to CPU Simulation, where subprocess and system-call treatment differs.
Use CodSpeed Macro Runner if available. On ordinary GitHub-hosted VMs
keep `HOSTED_EXPLORATORY / PERFORMANCE_INCONCLUSIVE`; no formal
regression or speedup claim based on noisy hosted WallTime data.

Call the original v0.9.1 QuPRS API exactly as the official script:
`method=hybrid|wmc_only|reduction_rules`,
`strategy=Proportional`, `timeout=200`,
with the two immutable historical QASM paths. Use a wrapper that
instruments the outer single call, maintains original source identity,
and serializes the returned result. Do not modify original QuPRS or
GPMC code merely to facilitate timing.

Record both:
- `codspeed_walltime_seconds`: CodSpeed's timed whole-call metric
  including launch/OS/Solver and labeled with instrument and runner.
- `original_v091.verification_time`, `pathsum_time`,
  `to_DIMACS_time`, `gpmc_time`, `wmc_time`: native per-stage
  diagnostic metadata *from the same invocation*, with literal
  censored strings preserved. These source-internal times are **not**
  independent CodSpeed metrics and must not be presented as such.

Make preparation time (fixture lookup, dependency installation,
QASM hash verification) outside the benchmark measurement where
possible; make original verifier initialization, QASM loading, RR and
GPMC all part of the measured complete-call unit. Explicitly document
any persistent process/cache effects and reset/teardown policy.

## 5. Workflow scheduling and archival

- Workflow: dedicated `workflow_dispatch` **only**, no automatic
  source push/PR hooks; ordinary changes must not rerun full historical
  experiments. Do not edit PR #131 or modern CodSpeed workflow.
- Stage A: pure source/fixture/identity + timeout-state unit tests,
  no Solver or CodSpeed invocation.
- Stage B: **2–4** selected source cases, single invocation each,
  validate instrument runner behavior and per-case watchdog.
- Stage C: 12–20-case original-source WallTime cohort, with
  per-case execution bounds, small parallelism and failure-isolated
  shards. Do not include large 200-second timeout-prone cases.
- Stage D: optional bounded targeted slow-case study, only if requested.
  Not part of release or ordinary PR gate.
- Persist `benchmark_id, historical_target_sha, harness_sha,
  source_verdict, rr_derived, qasm_hashes, gpmc_sha,
  codspeed_run_id, timing_instrument, runner_class,
  native_stage_times, timeout_status, censoring_lower_bound_s`
  with original per-invocation JSON; make downloadable artifacts
  and commit a compact immutable Markdown/CSV/JSON snapshot under
  `docs/development/tacas26-results/codspeed-historical/`.
- The report must have **two different time columns**:
  `paper_reference_seconds` (old Azure publication)
  vs `new_codspeed_walltime_seconds` (new instrument/runner).
  Do not compute ratios across the two as formal speedup/slowdown.
  Prefer no newly captured value rather than an inferred one.

**Promotion gate**: instrument correctly produces per-case benchmarks;
verified no hidden multiple runs after timeout; child processes fully
reaped; no wrong-sha fixture; no history/modern URI overlap; source
verdict reproducibility remains intact; correct censorship semantics;
successful persistence to Git; stable runner qualifies comparison.
Fail closed if these invariants break.

This document is a design, not an assertion that new CodSpeed historical
measurements exist or that the workflow has been executed.

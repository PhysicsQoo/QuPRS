# QASM261 Solver coverage-gap study — bounded manual CodSpeed admission

**Date:** 2026-11-03. **Current status:** six-case manual CodSpeed pilot has run successfully and timing/provenance artifact was uploaded; **per-case scientific eligibility still requires raw JSONL review**. See [post-run admission evidence below](#post-run-admission-evidence-and-next-actions-2026-11-03) and the [prior empirical matrix](codspeed-solver-coverage-matrix.md).

The existing 7 legacy + 2 new paired cases were retained when PR #131 merged to `dev`. This research pilot does not expand them.
No ordinary PR job, default five Simulation shards, native Rust job or
P5 release gate is expanded by this experiment.

## Why these six and no more

| Candidate ID | Circuit / variant | Backend | Method | Solver | Expected binary | New evidence axis |
|---|---|---|---|---|---|---|
| `q261_gap_qaoa7_neq_wmconly_rust_gpmc` | QAOA7 / Random_Rotation | Rust | WMC-only | GPMC | NEQ | Remove RR prepass |
| `q261_gap_qaoa7_neq_wmconly_python_gpmc` | QAOA7 / Random_Rotation | Python | WMC-only | GPMC | NEQ | Python WMC-only |
| `q261_gap_qaoa7_neq_hybrid_python_gpmc` | QAOA7 / Random_Rotation | Python | Hybrid | GPMC | NEQ | Matched native Rust Hybrid pair |
| `q261_gap_qft16_neq_hybrid_python_gpmc` | QFT16 / Random_Rotation | Python | Hybrid | GPMC | NEQ | Cross-backend QFT complexity |
| `q261_gap_vqe8_eq_wmconly_rust_gpmc` | VQE8 / transpiled | Rust | WMC-only | GPMC | EQ / EQ* | Positive WMC-only |
| `q261_gap_qaoa7_neq_hybrid_rust_ganak` | QAOA7 / Random_Rotation | Rust | Hybrid | Ganak | NEQ | Distinct Solver, genuine NEQ |

Expected source verdicts are **hypotheses pending new execution**; historic QASM
and the strict operator-science oracle give context but do not certify these
new method/backend runs. Ganak's printed-count resolution must be assessed
separately, even if this case is expected to be truly NEQ.

## Original CI and measurement budget (pre-run plan; superseded by observed results below)

- Use the **existing** `.github/workflows/codspeed.yml` only via
  `workflow_dispatch`: `pilot_only=true`, `pilot_group=qasm261_gap`, and an **exact** `coverage_gap_verifier_sha`. The research branch supplies the harness and QASM; one checkout/build of that pinned formal PR **v0.14 verifier** supplies the implementation.
  A normal PR or push on the research branch does **not** run this group.
- At most **six separate single-round official CodSpeed WallTime samples**,
  each with a bounded **15 s verifier solver timeout and 24 s process-group
  watchdog**. This is an admission pilot, **not** a regression estimate.
- Use **one shared pinned PR verifier build** (no six separate builds) and 1 upload artifact
  `quprs-codspeed-v3-candidate-pilot` (CodSpeed first-party JSON,
  `candidate-pilot-science.jsonl`, exact-SHA manifest).
- If the solver times out, preserve `SOLVER_TIMEOUT` or
  `WATCHDOG_TIMEOUT` as a **censored observation**. Do not replace it with
  15/24 seconds as performance or claim an actual Solver invocation.
- `run_source_pinned_candidate` now requires a configured
  `expected_solver_invoked=True` to agree with **observed** Solver provenance
  before marking the result eligible for review.
- The six gap cases explicitly pass v0.14 `rr=1e-10`, `distance=1e-8`, `phase=1e-8`, GPMC digits 30; their execution is against the checked-out **PR verifier SHA**, not the older experiment branch's `dev` API. This pilot is not a base/HEAD comparison.\n- Job elapsed, build and CodSpeed action duration are **unknown until the
  manual job actually runs**. The existing 459-second 100-round ABBA job
  is not a valid per-case price estimator for this different matrix.

### Original manual trigger (already executed; do not rerun for documentation updates)

```bash
gh workflow run codspeed.yml \
  --repo PhysicsQoo/QuPRS \
  --ref experiment/qoo160-qasm261-codspeed-selection \
  -f pilot_only=true -f pilot_group=qasm261_gap \
  -f coverage_gap_verifier_sha=a4c7b12652b3c59c086f5d408a95e004df570bad
```

Check one source SHA, all 6 result markers, Solver stage, binary verdict, QASM
hashes, CodSpeed duration and actual job cost. Only stable, determinate,
genuinely WMC-invoked candidates may be shortlisted for 3-round base/HEAD
research; **no automatic every-PR promotion**. In particular, Python QFT16
or Rust WMC-only VQE8 may remain opt-in/censored if expensive.

## Historical PR #131 CI failure (resolved before merge)

On formal `542eded`, nine-pair run 41594571639 failed because the old
`solver_case.py` accepted two rather than three optional CLI args. The
harness fix was committed separately to formal PR #131 as
[`675c806`](https://github.com/PhysicsQoo/QuPRS/commit/675c8065110a59b1e6641a70ea8020ab873c78c3).
Treat that fix's newer CI as independent required evidence; this research
pilot cannot waive it.

### Precision and history qualification (2026-11-03)

Previous 100-round ABBA observations were collected through the experimental harness
without explicit diagnostic tolerance environment variables. Consequently, old
`dev@2dd451e` used its legacy API default (magnitude classifier unless distance
was requested), while PR v0.14 used default distance=1e-8; the recorded default
`effective_distance_tolerance` label in that harness did **not** prove the base
received the option. The reported timing/CV values remain raw measurements, but
**cannot certify an equal-numerical-contract algorithmic speedup**. In addition,
if distance=1e-8 is explicitly requested on old dev, its Rust GPMC distance adapter
uses **90 output digits**, not the new PR's default **30**. The formal paired PR
code now pins both revisions to 90 for the two new QASM261 NEQ cases, verifying
the old dev source before timing. Do not describe the earlier ~58% QFT16 delta
as an isolated optimized-RR gain.

### Research workflow cost containment

The original `qoo160-qasm261-codspeed.yml` (15-case pilot) and
`qoo160-qasm261-comparison.yml` (pinned 100-round A1/B1/B2/A2)
are now archival **workflow_dispatch only**; editing the shared registry,
new coverage-gap harness or evidence notes no longer automatically repeats
old studies. The only suggested new work is the six-case **manual**
`codspeed.yml` `pilot_only` job, using one pinned v0.14 verifier build.

### After PR #131 merged into dev (2026-11-03)

The PR was squash-merged at `dev@a4c7b12652b3c59c086f5d408a95e004df570bad`.
Git tree `76bff0488472a57270e2c81f7fac56685e3c5ac2` is **identical**
to the verified pre-merge PR head `ce51fd6155c381c84d41c1031ccd109982b9ea64`.
The manual pilot command above therefore pins the **retained dev merge commit**
instead of an eventually deletable PR branch commit, without changing the
verifier's source, benchmark identities, precision semantics, or CI scope.
Do not compare the old experimental ABBA (unmatched numerical defaults) to
this new matched numerical policy as if they were one controlled cohort.


## Post-run admission evidence and next actions (2026-11-03)

**Observed:** [manual CodSpeed Actions #41600679301](https://github.com/PhysicsQoo/QuPRS/actions/runs/41600679301) completed SUCCESS on experiment harness `2b74058f17b4f7c3bafa57240067d3ed14a1211c`, using the separately checked-out v0.14 verifier `ce51fd6155c381c84d41c1031ccd109982b9ea64`. The latter has the same Git tree as merged `dev@a4c7b12652b3c59c086f5d408a95e004df570bad`, but the workflow itself ran on the **research harness SHA**, not on a fresh dev workflow run. The bounded candidate job and incremental CI impact job succeeded; optional unrelated jobs were skipped as designed.

- Official CodSpeed completed **six single-round/no-warmup benchmark samples**; pytest reported `6 passed in 16.09s`; performance data uploaded successfully. Overall workflow from 08:05:14Z to last update 08:07:21Z was approximately **127 seconds elapsed**, including preparation/build and artifact handling; this is *not* per-case marginal CI cost.
- Preserved [artifact #13213994435](https://github.com/PhysicsQoo/QuPRS/actions/runs/41600679301/artifacts/13213994435), `quprs-codspeed-v3-candidate-pilot`, with the first-party CodSpeed JSON, `candidate-pilot-science.jsonl` and exact SHA manifest (retention through 2026-11-17 UTC). Do not equate uploaded timing with numerical correctness certification.
- **Critical interpretation:** the exploratory test `run_source_pinned_candidate()` accepts `COMPLETED`, `SOLVER_TIMEOUT`, `WATCHDOG_TIMEOUT`, `PROCESS_ERROR` and missing/unparseable results as pytest-successful observation statuses. Eligibility is instead recorded in `pilot_qualification` and observed `solver_invoked`/verdict fields. Therefore `6 passed` alone **does not prove six valid scientific results, six real Solver calls or a determinate EQ/NEQ matrix**. Audit the actual JSONL before making those claims. The log also noted `Lost 157 events` during CodSpeed collection; assess sampling completeness separately, without treating this as an automatic correctness failure.
- These six candidates explicitly use `rr_tolerance=1e-10`, `distance=1e-8`, `phase=1e-8` and **GPMC digits=30**. Existing historic dev-versus-v0.14 matched QASM261 comparisons pinned **90 digits**; their timing deltas are **not numerically matched to this pilot**. No base/HEAD CV, A/A drift or regression conclusion can be inferred from one measured round.

### Promotion plan (reuse existing research branch and CodSpeed workflow)

1. **Science/admission audit:** parse all six `candidate-pilot-science.jsonl` entries and timing JSON; attach each exact case ID, two QASM SHA256 hashes, verifier SHA, expected/observed binary verdict, explicit observed Solver invocation, status/exit code, numeric precision and any timeout. Treat missing evidence and censored observations as non-admitted, not silent PASS. Cross-check Ganak printed-count resolution independently.
2. **Shortlist, do not bulk-promote:** first consider `q261_gap_qaoa7_neq_wmconly_rust_gpmc` for a distinct, versioned regular paired identity because the retained formal suite otherwise lacks WMC-only. Keep the Python WMC-only/Hybrid QAOA7 cases as conditional cross-backend/method controls, Python QFT16 Hybrid as expensive opt-in, VQE8 positive WMC-only periodic, and Rust/Ganak NEQ opt-in pending numerical print qualification. These are **candidate decisions, not approved additions**.
3. **Paired repeatability / cost:** for science-qualified shortlist candidates, run bounded **three-round base/HEAD official CodSpeed WallTime** with identical source/target QASM hashes, runner cohort, solver, method, RR/distance/phase and GPMC precision on both sides, and record paired per-case medians/CV, stage/verdict parity, artifact provenance and incremental CI duration. When comparing old `dev@2dd451e` to v0.14, retain source-verified 90 digits or explicitly establish a genuinely equivalent numerical contract before attributing gains to algorithm changes. The post-merge `dev` is now a new baseline for future PRs; do not replay unmatched historical cohorts as if they were comparable.
4. **Integration boundary:** reuse the existing five Simulation shards, 32 protected historical IDs, retained nine Solver-inclusive base/HEAD pairs and existing native RR IDs. Prefer placing a proven new case in the **existing** paired job and path-sensitive CI routing, not creating a new default expensive build/shard or automatic research trigger. CodSpeed remains the sole timing authority; P5 remains observational with no fixed percentage release gate. Documentation-only edits should reuse successful evidence rather than rerunning expensive measurements.

The admission work is tracked in the existing benchmark research plan; this documentation update does not open a new PR or expand automatic CI.

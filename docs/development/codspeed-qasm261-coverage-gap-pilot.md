# QASM261 Solver coverage-gap study — bounded manual CodSpeed admission

**Date:** 2026-11-03. **Status:** candidates and source/fixture contracts staged on the
experiment branch; **no CodSpeed timings, science verdicts or CI costs have yet
been observed for these six new method/backend/solver combinations**.
Read the [prior empirical matrix](codspeed-solver-coverage-matrix.md) first.

The existing 7 legacy + 2 new paired cases remain unchanged in PR #131.
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

## CI and measurement budget

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

### Manual trigger (when ready)

```bash
gh workflow run codspeed.yml \
  --repo PhysicsQoo/QuPRS \
  --ref experiment/qoo160-qasm261-codspeed-selection \
  -f pilot_only=true -f pilot_group=qasm261_gap \
  -f coverage_gap_verifier_sha=ce51fd6155c381c84d41c1031ccd109982b9ea64
```

Check one source SHA, all 6 result markers, Solver stage, binary verdict, QASM
hashes, CodSpeed duration and actual job cost. Only stable, determinate,
genuinely WMC-invoked candidates may be shortlisted for 3-round base/HEAD
research; **no automatic every-PR promotion**. In particular, Python QFT16
or Rust WMC-only VQE8 may remain opt-in/censored if expensive.

## Formal PR #131 separate CI failure

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

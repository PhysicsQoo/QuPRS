# CodSpeed v3: source-pinned benchmark selection and evidence policy

**Active plan — 2026-11-03.** This document supersedes previous proposed shard reductions, pre-merge PR #131 instructions, and obsolete seven-only paired-suite descriptions. The previous revisions remain available in Git history. This is a **research-branch plan**, not a change to the current `dev` CI.

## Accepted baseline and measurement taxonomy

- PR [#131](https://github.com/PhysicsQoo/QuPRS/pull/131) was squash-merged into `dev@a4c7b12652b3c59c086f5d408a95e004df570bad` on 2026-11-03. The merged tree equals the final verified PR head `ce51fd6155c381c84d41c1031ccd109982b9ea64`.
- Retain **five** Simulation shards, the **32 historical Simulation IDs** and their original source identities, the **nine** source-pinned Solver-inclusive base/HEAD WallTime pairs and the installed native-core suite. No three-shard experiment or unreviewed fixture substitution. Release compatibility applies only to identities verified on `main` before v0.14 development; PR/dev-only experimental identities may be revised before first release.
- **Simulation** measures modeled CPU within its instrument's scope. The legacy suite does not capture actual subprocess solver work. Native Miter+RR Simulation excludes input parsing and WMC and cannot establish complete solver walltime.
- **Solver-inclusive WallTime** measures a complete verifier request including the real GPMC/Ganak subprocess; its stage and scientific verdict must be checked separately. CI job duration is a resource-cost measure, **not** a per-case CodSpeed timing.
- Scientific source/verdict oracle, solver printed precision, actual solver invocation and timing comparability are **independent** fields. P5 remains **observation-only**: no fixed percentage performance release gate, no automatic interpretation of noise-limited changes as significant.

## Existing scientific and performance evidence

| Source | Observed evidence | Interpretation |
|---|---|---|
| [Historical difficulty ledger](../../benchmarks/codspeed/paper_difficulty.json) | TACAS Table 2 36 source cases; 8 measured on prior SHA, 28 unmeasured | Archival difficulty prior, not a current runtime baseline; original Table 2/3(b) fields still require source-by-source audit |
| [QASM261 initial pilot](codspeed-qasm261-pilot-results.md) | 15 single-round Rust/Hybrid/GPMC cases: 10 RR-terminated; 5 truly WMC-invoked | Stage discovery only, not repeatability or paired comparison |
| [Formal nine paired cases](codspeed-solver-coverage-matrix.md#2026-11-03-最新正式九組驗收配對-walltime-已成功追補證據) | [Actions #41598328358](https://github.com/PhysicsQoo/QuPRS/actions/runs/41598328358), 9/9 paired / 18 URIs, observed solver invocation, verdict and dispersion | Existing routine suite; old `dev@2dd451e` QASM261 NEQ A/B matched GPMC **90** printed digits. Do not mix with 30-digit pilot |
| [Five QASM261 native RR cases](codspeed-qasm261-formal-selection.md) | GHZ32, Graphstate16, QFT16, QPE-exact8, VQE4 native Miter+RR Simulation | Solver-free CPU benchmark identities, no claim about end-to-end GPMC |
| [Exact Bra-CX research](https://github.com/PhysicsQoo/QuPRS/blob/experiment/qoo151-rr-xor-reuse-20261103/benchmarks/rr_cx_qft16_paired/RESULTS.md) | Same-source native QFT16 45.802→30.641 ms (**−33.10%**), 68 public-API EQ/NEQ and 12/12 RR residual checks PASS; separate QFT16 Solver-inclusive median **−1.23%**, baseline drift **2.64%** | Native RR optimization is supported; solver-inclusive performance remains **INCONCLUSIVE**. The exact Bra-CX source is now merged via #131 |
| [Six new QASM261 gap candidates](codspeed-qasm261-coverage-gap-pilot.md) | [Actions #41600679301](https://github.com/PhysicsQoo/QuPRS/actions/runs/41600679301): six one-round CodSpeed requests, `6 pytest passed in 16.09s`, original [artifact #13213994435](https://github.com/PhysicsQoo/QuPRS/actions/runs/41600679301/artifacts/13213994435) | **SCIENCE AUDIT PENDING**: the exploratory pytest harness accepts recorded timeout/error statuses. Read each JSONL `observed` and `pilot_qualification` before admitting any case |

The experimental old 100-round A1/B1/B2/A2 QASM261 cohort did **not** match old/new numerical defaults. Its timings are historical observations, not an isolated algorithm speedup. The later corrected nine-pair source-verified comparisons are distinct. Ganak output resolution warnings must be retained; a conditional same-workload timing delta does not certify scientific EQ.

## Single workflow, explicit owners

### P0 — source integrity and representativeness
Check the original TACAS Table 2/3(b) circuit rows, qubit counts, fixture directions, historic times/timeout annotations and paper-page provenance against the 36-case manifest. Preserve `NOT_MEASURED` and `UNVERIFIED` instead of inventing observations. Distinguish historic TACAS QASM, Qiskit 2.6.1 Level-0 and Random_Rotation negative QASM with versioned source hashes. The original v0.9.1 paper-reproduction study remains on its separate research branch and is not an every-PR benchmark.

### Algorithm evidence — exact native reduction
Keep exact Bra-CX and PhasePolynomial measurements separate from Solver-inclusive results. The merged direct Bra-CX path is accepted on its bounded science and native-source evidence; do not rerun it on Markdown edits. Residual cost attribution should focus on existing scans/clones, term insertion/merge and coefficient arithmetic, plus the historical VQE4/Ganak CNF and literal/solver-cost difference **only if existing evidence warrants another bounded diagnostic**. No speculative PhasePolynomial container rewrite or precision relaxation.

### P4 — evidence ingestion and science admission (next immediate step)
Read the existing six-case `candidate-pilot-science.jsonl`, CodSpeed JSON and SHA manifest **before running a new benchmark**. Audit case/source target hashes, method/backend/solver, verifier/harness SHA, RR/distance/phase tolerance, GPMC digits, process status/timeout, exit code, actual `solver_invoked`, EQ/EQ*/NEQ and independent oracle. The pilot pinned `rr=1e-10`, `distance=1e-8`, `phase=1e-8`, **GPMC 30 digits**. A pytest PASS is not the same as six valid WMC/solver-science results.

Update the existing [coverage matrix](codspeed-solver-coverage-matrix.md) and its JSON companion with distinct `science_qualification`, `numeric_comparability`, `performance_comparability` and `admission_decision`. Missing data remain `MISSING`; timeouts/right censoring are not converted to fixed stopwatch values. Record `Lost 157 events` as a potential instrument-quality caveat, not an automatic science verdict. Authorized manual CodSpeed service snapshots are acceptable; a CI upload does not imply access to a supported unattended Performance Data API.

### P5 — bounded repeatability, future paired comparisons and promotion
For **P4-qualified** candidates, first consider **QAOA7 negative / Rust / WMC-only / GPMC** because the routine nine cases primarily exercise Hybrid. Other candidates: QAOA7 Python WMC-only/Hybrid as conditional cross-method/backend controls; VQE8 positive Rust WMC-only periodic; Python QFT16 Hybrid and QAOA7 Rust Ganak opt-in (the latter needs print-resolution review).

Because PR #131 is **already merged** and no new algorithm HEAD is pending for these candidates, start with an optional **three-round same-SHA CodSpeed repeatability** check, not a fake current-dev/current-dev base/HEAD comparison. When a future verifier PR changes code, perform **three-round matched dev-versus-HEAD** CodSpeed WallTime on the chosen case with identical source/target QASM hashes, backend, method, solver, printed precision, RR/distance/phase, runner/instrument and confirmed solver stage/verdict. Expand to ABBA only when instability or a real regression signal warrants it.

Every case receives `EVERY_PR`, `PERIODIC`, `OPT_IN` or `CENSORED_OR_REJECTED` with grounded coverage benefit, CV/noise, scientific verdict, actual CI cost and source provenance. Reuse the existing paired job/build where justified; do not add all six candidates by default.

## Completion and safe CI policy

P0 is complete when the 36 historic source rows and focused source guards are auditable; no obligation to run 28 unmeasured historical cases. The algorithm work is complete when integrated Bra-CX source/science evidence and remaining bounded-cost caveats are documented. P4 is complete when all six candidate observations are explicitly qualified or marked missing/censored, and the combined cross-instrument matrix can be reproduced from named sources. P5 is complete when qualified candidates have a justified measurement cadence/admission decision and actual cost or a documented absence of sufficient evidence.

**Never trigger full CodSpeed for Markdown-only edits.** Changes to a benchmark identity, verifier algorithm or numerical semantics must have appropriately scoped science and measurement checks. Keep paper reproduction, native optimization experiments and routine PR performance observations as separate evidentiary lanes. Release signoff remains independent of the optional P5 performance threshold research.

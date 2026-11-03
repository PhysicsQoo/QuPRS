# Qiskit 2.6.1 Level-0 CodSpeed — multi-round acceptance and formal-case decision

> **Post-merge status (2026-11-03):** PR [#131](https://github.com/PhysicsQoo/QuPRS/pull/131) is **merged into `dev@a4c7b126`**; the final [nine-pair corrected numerical-contract workflow #41598328358](https://github.com/PhysicsQoo/QuPRS/actions/runs/41598328358) succeeded with all nine true Solver-inclusive base/HEAD pairs. The original decision and prior 100-round data below are preserved as **historical study observations**, not a pending PR admission request. Their 30/90-digit and older-default differences remain documented. For current admission decisions use [CodSpeed v3 plan](codspeed-v3-plan.md), [nine-pair acceptance](codspeed-solver-coverage-matrix.md), and [six-case follow-up pilot](codspeed-qasm261-coverage-gap-pilot.md).

> **2026-11-03 PRECISION / FAIRNESS ERRATUM:** The retained 100-round CodSpeed
> numbers below are true historical observations, but the experimental
> `solver_case.py` did not pass explicit distance/RR/precision kwargs to
> `dev@2dd451e` and PR `07d5c8d`. The two APIs therefore selected differing
> numerical defaults (legacy magnitude versus v0.14 distance). The returned
> stage and binary verdict observations remain meaningful, but their measured
> deltas **do not certify equal-policy base/HEAD speedups**. If a distance
> is explicitly pinned on old dev, its Rust GPMC adapter runs `-prec=90`, not
> the new default 30. The formal PR's [corrected harness](https://github.com/PhysicsQoo/QuPRS/commit/ce51fd6155c381c84d41c1031ccd109982b9ea64)
> requests the same 90 digits in both revisions, and the resulting CI must be
> assessed independently before using any new promotion baseline. This erratum
> does not alter raw historical samples/CV figures.


**Historical decision date:** 2026-11-03. **At that time:** science and CodSpeed research gates passed; formal PR #131 was not modified by this experiment. **Current status:** PR #131 is now merged as noted above. The previous 32/five-shard Simulation and seven paired WallTime identities are preserved.

### Source-pinned independent evidence

- [GitHub Actions #41589357492](https://github.com/PhysicsQoo/QuPRS/actions/runs/41589357492): all three jobs PASS on experiment SHA `fe47ba5`. Dev comparison `2dd451e`, PR head `07d5c8d`. Old/source + new Level-0 QASM are identical across A1/B1/B2/A2, Rust/GPMC/Hybrid, strict 1e-8/1e-10, with expected EQ/NEQ and **real GPMC invocation in every relevant measurement**.
- [Native CPU source artifact](https://github.com/PhysicsQoo/QuPRS/actions/runs/41589357492/artifacts/13209324069). [Paired CodSpeed WallTime, 100 rounds, provenance, environment freeze and JSON report](https://github.com/PhysicsQoo/QuPRS/actions/runs/41589357492/artifacts/13209902171).
- [CodSpeed official 25 measurement run](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6ae97ee3170f3fb7637c3e0a). The actual instrument is authoritative, not job elapsed seconds. This was a shared hosted runner, **not** a Macro Runner; numerical solver arithmetic is not mathematically certified.
- Machine-readable [summary and selection](../../benchmarks/codspeed/qasm261-formal-selection.json). QFT16's ~58% improvement is **observed** with small same-runner A/A drift; it is not a universal confidence interval.

### Real native Rust Miter + RR CPU Simulation

| Circuit / Versioned URI | CodSpeed CPU Simulation | Admission |
|---|---:|---|
| `q261_rr_ghz32_positive` (GHZ32) | 1.1 ms | **New native-core ID**, observational; no Solver |
| `q261_rr_graphstate16_positive` (Graphstate16) | 6.6 ms | **New native-core ID**, observational; no Solver |
| `q261_rr_qft16_positive` (QFT16) | 42.7 ms | **New native-core ID**, observational; no Solver |
| `q261_rr_qpeexact8_positive` (QPE-exact8) | 4.8 ms | **New native-core ID**, observational; no Solver |
| `q261_rr_vqe4_positive` (VQE4) | 6.5 ms | **New native-core ID**, observational; no Solver |

QASM2 source is parsed *before* the timed native RR invocation, and the benchmarked code uses the real original and Qiskit261 Level-0 gate lists. Scientific RR-only positive and `solver_invoked=false` assertions succeeded for all five. Native code is [benchmarks/rust_qasm261/benches/native_rr.rs](../../benchmarks/rust_qasm261/benches/native_rr.rs); for default PR, integrate these into the **existing native-core job** rather than compile a standalone second crate on every PR. Retain all original native IDs.

### Solver-inclusive A1/B1/B2/A2 CodSpeed WallTime

Five GPMC cases × four positions × five measured rounds = **100 CodSpeed rounds**. All five cases retained same input hashes, solver stage, independent source identity and expected binary verdict. A1/A2 drift checks shared-runner noise; it is not an independent A/A confidence cohort.

| Case | dev median (ms) | PR median (ms) | PR relative time | Base A1/A2 drift | Largest cell CV | Decision |
|---|---:|---:|---:|---:|---:|---|
| `q261_qaoa7_negative` | 985.6 | 1003.4 | 1.81% | -2.20% | 3.6% | every-pr candidate |
| `q261_qft16_negative` | 3555.1 | 1478.6 | -58.41% | -1.45% | 3.2% | every-pr candidate |
| `q261_qnn4_negative` | 1020.2 | 1027.4 | 0.71% | 14.70% | 7.6% | opt-in |
| `q261_vqe4_negative` | 1040.7 | 1071.8 | 2.99% | -5.04% | 18.5% | opt-in |
| `q261_vqe8_positive` | 1354.8 | 1347.9 | -0.51% | 2.13% | 15.3% | periodic |

QFT16-negative's magnitude substantially exceeds its observed A1/A2 drift and per-cell CV, making it the clearest source-versioned Solver performance sentinel. QAOA7-negative is a low-cost independent NEQ guard: its +1.81% is within drift/noise and is **not** a confirmed regression. QNN4-negative has 14.7% base A/A drift; VQE4-negative and VQE8-positive show high CV, so do not add these to every PR by default.

### Actual CI cost

| Work | CI runtime | Measured-work step |
|---|---:|---:|
| Source and reporter contracts | 9 s | 4 s source test |
| Standalone Native RR job | 156 s | 20 s CodSpeed (125 s build) |
| Standalone paired Solver job | 459 s | 213 s CodSpeed (226 s building dev and PR environments) |

**Historical promotion proposal, subsequently integrated in PR #131:** retain the 32 historical Simulation identities and five shards; add the five new native RR IDs to the existing native-core job and QFT16-negative plus QAOA7-negative as separately versioned pairs to the existing seven paired WallTime cases (now **nine total**). Retain larger four-position/five-round research cohorts as opt-in. VQE8-positive remains periodic; QNN4-negative/VQE4-negative opt-in; Ganak mode 6 QASM261 needs separate printed-resolution qualification. This paragraph is an archival decision record, not an unexecuted PR task.

The 24 extra QASM261 Simulation URIs in a separate 32+24 research experiment are not part of this acceptance: [run #41588474734](https://github.com/PhysicsQoo/QuPRS/actions/runs/41588474734) had 4 of 5 shards succeed, while shard0 failed a reporter expectation; do not describe that experiment as a fully accepted 56-case suite.

**Not a formal performance regression gate.** Future CI must retain source hashes, actual Solver invocation, exact binary decisions, CodSpeed runner context, any censoring and metric units. A 1–3% drift in one hosted-runner session alone is not proof of regression. Changes to code/benchmarks justify new CI; Markdown evidence updates should reuse existing successful measurements.

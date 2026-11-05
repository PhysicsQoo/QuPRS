# QOO-157 P9 — Pre-BiPe structural policy across QAOA/QFT families (research only, 2026-11-05)

## Research question and CURRENT decision

**Investigate a conservative, feature-aware preprocessing policy, but do not ship a family-name switch or change the GPMC/d4 solver default yet.** Existing first-party official CodSpeed confirms strongly opposite QAOA7-vs-QFT16 behavior when BiPe is **entirely disabled**, but the sample size is **one CNF per family**, QAOA7 is NEQ whereas QFT16 is EQ, the original CNF sizes differ, and all quoted benchmarks ran on hosted **non-CodSpeed-Macro** hardware without paired ABBA/BAAB. Any threshold derived from these two inputs is *post-hoc* and **not out-of-sample validated**.

## Source-pinned factual baseline

Original archived QuPRS weighted-CNF science artifact: [GitHub Actions #41822549728](https://github.com/PhysicsQoo/QuPRS/actions/runs/41822549728), artifact `13317939531`; original report `matched-science-report.json`, source d4 `be15f91f3e9769e1f5cb175fa27e3eca3a1ea690`, complex weighted count 38 effective decimal digits / actual 128 GMP bits.

Independent read-only Python analysis of these *exact archived CNF bytes* (not a new official CI or CodSpeed run) built the **pre-BiPe primal graph** from clauses and computed its exact **degeneracy** by repeated lowest-degree removal (which is **not** certified exact treewidth). SHA256 was checked against the archived source manifest:

| Source case | Original nvars | Clauses | Pre-BiPe primal edges | Degeneracy k | Protected/weighted-variable count | Original CNF SHA256 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Grover4 EQ | 372 | 698 | 600 | **4** | 256 | `e75f823656177295a5c10c3e2fc2bfd6608a20eb2b96f7477e586104e14f6a05` |
| QAOA7 genuine NEQ | 470 | 823 | 669 | **2** | 319 | `66375ceba75cd7b02e8f4a723c534618d5206dc2ebfaf02255d4c863f79a3123` |
| QPE exact8 EQ | 250 | 495 | 426 | **4** | 178 | `f747148c96c48bbb4349585652fac805117e964112cdb082feb096a28a80feb0` |
| QFT16 EQ | 486 | 1144 | 1041 | **11** | 400 | `c7fe1574adb4221bf890aa1f2181dbcdaf793fa54a4438c60a98e5b620e0c1fd` |

The original QAOA7/QFT16 values **2/11** reproduce the independent native BiPe pre-stage degeneracy observations in [BiPe v1.0.0 science Actions #41847739344](https://github.com/PhysicsQoo/QuPRS/actions/runs/41847739344), artifact `13331518772`. P1 native post-BiPe k-proxy became QAOA7 **2→2** and QFT16 **11→8**. The remaining Grover/QPE k=4 are **unlabeled intermediate negative controls**; no policy speed effect has been measured for these cases.

### Previous official CodSpeed evidence (no new performance measurements here)

[BiPe option trial #41839512753](https://github.com/PhysicsQoo/QuPRS/actions/runs/41839512753), artifact `13326829794`. **Same-run** 3-round medians of source-prepared-CNF full d4 subprocess (all hosted non-Macro, observational):

| Variant | QAOA7 NEQ ms | QFT16 EQ ms |
| --- | ---: | ---: |
| `auto_default` | 92.775650 | 1134.517316 |
| `manual_sharp` | 64.499798 | 1058.052259 |
| `none` | 56.476381 | 6121.688328 |

`none` lowers QAOA7 median **39.13%** vs default but increases QFT16 median **439.59%**; QFT16 `none` sampling is notably weak because its ~6.12s rounds saturate the previous ~5s CodSpeed time setting, so **do not use that 5.4x as a formal benchmark acceptance** without enough runtime/rounds. `manual_sharp` is less expensive in both samples (QFT only ~6.74%, unproven on fixed runner), hence the only observed structural contrast is **full disabling BiPe**; a proposed **family-specific manual-sharp default is not established**.

[P8 stage attribution Actions #41944225225](https://github.com/PhysicsQoo/QuPRS/actions/runs/41944225225) on the same QAOA7 original residual (byte-identical across auto/manual/no-vivif) obtained hosted CodSpeed five-round preproc-only medians auto 71.425351ms, manual 26.448164ms, no-vivif 56.397074ms. The preproc-only path still contains subprocess startup and parsing; this is evidence of preprocessing-path cost, not a pure isolated BiPe stage timer or additive measured DPLL time.

## P9 candidate policy (not approved)

1. **Low-cost original-CNF features before any BiPe**: `nvars`, `nclauses`, `nliterals`, textual weight/protected share, primal graph degeneracy, and count/density of binary equivalences; no QASM `family` filename dependency. Input parser/read and feature extraction are included in any future **full** CodSpeed timing, with a strict bounded resource policy; if scanning is too expensive, **ABSTAIN → d4 existing default**.
2. **Hypothesis only**, based on the *two labeled cases*, not a trained rule: low k≈2 → compare `none`/ `manual_sharp` to default; high k≈11 → retain `auto` and compare `manual_sharp`; k≈4 (Grover/QPE) → **abstain**. **Do not hard-code** k≤2 or k≥8 as shipping thresholds; these are study buckets selected after seeing the training cases.
3. Structural features *alone* do not determine whether a BiPe pass will reduce k. A stronger future controller can estimate protected-variable constraints and equivalence-substitution opportunity using a cheap bounded pre-scan, but it must record any additional overhead. Do not run multiple full d4 solve candidates per input as a default strategy and call it an optimization.
4. Required independent **same-family holdout**: generate exact provenance-checked original WMC CNFs for **QAOA9/11 and QFT20/22**, each including comparable EQ and NEQ controls when scientifically valid, plus Grover/QPE negative controls. Do not reuse the QAOA7/QFT16 sample as its own test set; record generator version, QASM and CNF SHA, angle source, precision, preprocessor output SHA, search counters, WMC count uncertainty, timeout and RSS. Scale/weight/NEQ confounding must be treated explicitly.
5. Science first: selected vs original d4 baseline must preserve literal weights/protected/projection semantics and complex WMC, using an independent count oracle and the **same** precision and source CNF. Failing/timed-out samples are censored, not discarded as inconvenient.
6. Only then run **official CodSpeed**: fixed Macro Runner / same-SHA / ABBA–BAAB, first-party result export, paired raw within-case latency, variance and simultaneous peak-RSS/timeout. Test `auto`, `manual_sharp`, `none` and the proposed dispatcher **including feature overhead**, not a post hoc oracle choosing each case's fastest observed arm. Pre-register an economically meaningful minimum gain and no-regression bound on each holdout, rather than claiming hosted 1–7% differences are real.
7. If holdouts do not show sustained positive net cost/benefit, **no conditional BiPe shipping**; GPMC remains QuPRS recommended default, d4 remains opt-in/research-only. No routine additional CodSpeed shards or dev/main changes before a release decision.

## Connection to proposed QuPRS-native Rust WMC

The P9 result is **algorithm design guidance, not permission to copy BiPe or immediately replace existing solvers**. The most reusable insight is an **observable policy contract**: `CheapStructuralFingerprint → ConservativePreprocessChoice → Weight/Projection-Provenance-PreservingTransform → Component-WMC`, with per-stage source SHA, cache and time/memory evidence. The Rust design study is documented separately in `QUprs_RUST_WMC_SOLVER_STUDY.md` on this experimental branch.

Research owner remains existing [QOO-157](https://linear.app/qoogohome/issue/QOO-157). Adjacent responsibilities: QOO-7 SolverAdapter, QOO-8 conformance, QOO-105 adaptive precision (post-release), QOO-156 Rust CLI timeout/memory handling and QOO-152 Rust phase-literal provenance. No new duplicate Linear issue.

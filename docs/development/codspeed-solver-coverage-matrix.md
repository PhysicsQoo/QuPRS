# QuPRS CodSpeed Solver-inclusive / Native RR 既有實驗測項覆蓋矩陣

> **Current status (2026-11-03, after PR #131 merge).** The scientific verifier source was integrated into `dev@a4c7b126` and the routine paired Solver-inclusive suite has **nine** source-pinned cases ([exact-head paired SUCCESS #41598328358](https://github.com/PhysicsQoo/QuPRS/actions/runs/41598328358)). [Six additional QASM261 candidates were run once in #41600679301](https://github.com/PhysicsQoo/QuPRS/actions/runs/41600679301), and their original science JSONL/manifest **have now been audited**: six completed solver invocations with matching EQ/NEQ pilot expectations, including **three observed WMC-only** executions. Independent full-operator/solver arithmetic certificates and repeatability remain incomplete. Do not treat all six as permanently science-qualified merely from this observation. See the [active CodSpeed v3 plan](codspeed-v3-plan.md) and [candidate evidence](codspeed-qasm261-coverage-gap-pilot.md).

> **Reading rule:** Sections A–E below are pre-merge and prior-SHA **historical snapshots**, including old statements such as seven routine pairs or zero measured WMC-only. They remain for forensic comparison and are **not** the current CI inventory. The nine-pair addendum at the bottom records the later formal acceptance. Future edits should append separately qualified per-case data rather than rewriting old samples.

> **2026-11-03 evidence-only snapshot.** Base `dev@2dd451e`, formal PR #131 `@542eded`, independent research branch `@91d7a62` before this documentation commit. All figures trace to official CodSpeed reports and GitHub Actions logs. **No new benchmarks were run.**

## 歷史快照範圍及分類規則（pre-merge prior-SHA）

- **27 distinct versioned benchmark IDs:** 7 historical paired Solver WallTime, 15 Qiskit 2.6.1 single-round Hybrid pilots (including 5 already subjected to ABBA repeats and 2 registered into formal PR), 5 pure native RR Simulation. Different instruments/source corpora are separate rows and **must not be conflated**.
- The formal PR currently registers **9 paired (18 base/head URIs), 30 native Rust**, and five shards of **32 legacy + 24 extra Q261 Simulation URIs**. Other 56 Simulation stage results are **not** evidence of Solver invocation by themselves.
- `RR` means verifier finishes without a WMC solver; `WMC` means confirmed external Solver was invoked. `Hybrid` is the configured method for all recorded end-to-end measurements, including those that terminated early at RR. **Measured WMC-only coverage = 0**.
- Verdict `equivalent*` is an EQ-class verdict (e.g. global phase), not NEQ. The three Ganak legacy base→HEAD verdict changes are numerical precision warnings and **conditionally comparable performance only**, not a scientific equivalence PASS.
- GitHub job elapsed seconds measure **shared CI resource cost**, not individual benchmark runtime. Per-case marginal CI build/runner cost is **unknown**; do not allocate job elapsed equally across rows.

## A. 現有七組歷史 paired Solver-inclusive（舊 QASM、正式 CI 已成功）

| ID | Backend | Method / Solver | 實際階段 | Base → HEAD verdict | CodSpeed **min** ms base → HEAD | CV base/head（3+3 輪） | A/A drift |
|---|---|---|---|---|---:|---:|---|
| `vqe4_gpmc` | Rust | Hybrid/GPMC | WMC | `equivalent* → equivalent*` | 562.58 → 551.22 | 2.25% / 4.63% | 未測 |
| `qft16_gpmc` | Rust | Hybrid/GPMC | WMC | `equivalent* → equivalent*` | 1195.44 → 1164.53 | 1.33% / 0.84% | 未測 |
| `qaoa7_gpmc` | Rust | Hybrid/GPMC | WMC | `equivalent → equivalent` | 535.38 → 545.93 | 1.14% / 0.90% | 未測 |
| `vqe4_ganak` | Rust | Hybrid/Ganak | WMC | `equivalent* → not_equivalent` ⚠ print limit | 727.26 → 755.46 | 0.75% / 1.65% | 未測 |
| `grover4_ganak` | Rust | Hybrid/Ganak | WMC | `equivalent* → not_equivalent` ⚠ print limit | 788.27 → 786.42 | 2.56% / 2.06% | 未測 |
| `vqe4_gpmc_python` | Python | Hybrid/GPMC | WMC | `equivalent* → equivalent*` | 725.00 → 704.34 | 6.77% / 4.27% | 未測 |
| `vqe4_ganak_python` | Python | Hybrid/Ganak | WMC | `equivalent* → not_equivalent` ⚠ print limit | 880.39 → 928.37 | 6.56% / 2.28% | 未測 |

**Interpretation:** these min figures are taken from the previous successful paired report; the CV values and associated percent changes are based on the **median-by-rounds** P5 summary. Do not compute an asserted median improvement by dividing the displayed min timings. Seven pairs had real Solver invocation in both revisions; 3 Ganak cases require independent print-resolution warnings. Source: [full green formal workflow #41589264308](https://github.com/PhysicsQoo/QuPRS/actions/runs/41589264308) and [PR case registry](https://github.com/PhysicsQoo/QuPRS/blob/542eded49277d68a0871560cea05da2e05034858/benchmarks/codspeed/case_registry.py).

## B. 新 QASM261 Hybrid pilot：15 組（Rust/GPMC，一輪正式 CodSpeed WallTime）

| 版本化測項 | Source target | 結束階段 | Verdict | WallTime 單輪 ms | ABBA base→HEAD **median** ms | Max 單格 CV | A1/A2 base drift | 正式 PR 狀態 |
|---|---|---|---|---:|---:|---:|---:|---|
| `q261_ghz32_positive` | transpiled | **RR-terminated** | `equivalent` | 844.15 | 未測 | 未知（一輪） | 未測 | 研究/可選 |
| `q261_graphstate16_positive` | transpiled | **RR-terminated** | `equivalent` | 869.54 | 未測 | 未知（一輪） | 未測 | 研究/可選 |
| `q261_grover4_positive` | transpiled | **RR-terminated** | `equivalent*` | 806.37 | 未測 | 未知（一輪） | 未測 | 研究/可選 |
| `q261_qaoa7_positive` | transpiled | **RR-terminated** | `equivalent` | 826.04 | 未測 | 未知（一輪） | 未測 | 研究/可選 |
| `q261_qaoa7_negative` | Random_Rotation | **WMC-invoked** | `not_equivalent` | 840.61 | 985.6 → 1003.4 | 3.58% | -2.20% | **已登錄、最新 CI 失敗** |
| `q261_qft16_positive` | transpiled | **RR-terminated** (approx. RR) | `equivalent` | 821.21 | 未測 | 未知（一輪） | 未測 | 研究/可選 |
| `q261_qft16_negative` | Random_Rotation | **WMC-invoked** | `not_equivalent` | 1354.24 | 3555.1 → 1478.6 | 3.17% | -1.45% | **已登錄、最新 CI 失敗** |
| `q261_qnn4_positive` | transpiled | **RR-terminated** | `equivalent` | 850.29 | 未測 | 未知（一輪） | 未測 | 研究/可選 |
| `q261_qnn4_negative` | Random_Rotation | **WMC-invoked** | `not_equivalent` | 848.68 | 1020.2 → 1027.4 | 7.60% | 14.70% | 研究/可選 |
| `q261_vqe4_positive` | transpiled | **RR-terminated** | `equivalent` | 835.85 | 未測 | 未知（一輪） | 未測 | 研究/可選 |
| `q261_vqe4_negative` | Random_Rotation | **WMC-invoked** | `not_equivalent` | 828.66 | 1040.7 → 1071.8 | 18.53% | -5.04% | 研究/可選 |
| `q261_qpeexact8_positive` | transpiled | **RR-terminated** (approx. RR) | `equivalent*` | 812.97 | 未測 | 未知（一輪） | 未測 | 研究/可選 |
| `q261_wstate4_positive` | transpiled | **RR-terminated** | `equivalent*` | 865.87 | 未測 | 未知（一輪） | 未測 | 研究/可選 |
| `q261_vqe8_positive` | transpiled | **WMC-invoked** | `equivalent` | 1110.69 | 1354.8 → 1347.9 | 15.32% | 2.13% | 研究/可選 |
| `q261_qpeinexact20_positive` | transpiled | **RR-terminated** (approx. RR) | `equivalent*` | 816.52 | 未測 | 未知（一輪） | 未測 | 研究/可選 |

- All fifteen measured with the same experimental **Rust / Hybrid / GPMC**; the ten `RR-terminated` rows **did not invoke GPMC** despite the configured solver.
- The five actual `WMC-invoked` rows were subsequently included in **100 rounds across A1/B1/B2/A2 (5 per position per case)**. A/A drift and position-specific CV only apply to these five rows. Their A1/A2 and CV are not formal significance confidence intervals.
- `q261_qft16_negative` and `q261_qaoa7_negative` have experimental evidence **but do not yet have a successful nine-case formal PR run**. `q261_qnn4_negative` A1/A2 drift 14.70%; `q261_vqe4_negative` max CV 18.53%; `q261_vqe8_positive` max CV 15.32%—retain as opt-in/periodic.
- QPE-inexact20's pilot RR verdict is tolerance-boundary evidence, **not** proof of a universally exact/fast QPE solver workload.

Provenance: [15-case pilot #41587178934](https://github.com/PhysicsQoo/QuPRS/actions/runs/41587178934) / [pilot JSON](../../benchmarks/codspeed/qasm261-pilot-observations.json); [100-round A1/B1/B2/A2 #41589357492](https://github.com/PhysicsQoo/QuPRS/actions/runs/41589357492) / [selection JSON](../../benchmarks/codspeed/qasm261-formal-selection.json).

## C. Native Rust RR：五組無 Solver 的 CPU Simulation（與 WallTime 不可相加或做倍率）

| Benchmark ID | Backend / Method | 階段 | Verdict assertion | CodSpeed modeled CPU | 變異資訊 | PR 狀態 |
|---|---|---|---|---:|---|---|
| `q261_rr_ghz32_positive` | Native Rust / RR-only | RR；**不呼叫 Solver** | EQ 或 EQ*（未保存更細分 label） | 1.1 ms | 未保存逐輪 CV、A/A | 最新 native-core 成功上傳 |
| `q261_rr_graphstate16_positive` | Native Rust / RR-only | RR；**不呼叫 Solver** | EQ 或 EQ*（未保存更細分 label） | 6.6 ms | 未保存逐輪 CV、A/A | 最新 native-core 成功上傳 |
| `q261_rr_qft16_positive` | Native Rust / RR-only | RR；**不呼叫 Solver** | EQ 或 EQ*（未保存更細分 label） | 42.7 ms | 未保存逐輪 CV、A/A | 最新 native-core 成功上傳 |
| `q261_rr_qpeexact8_positive` | Native Rust / RR-only | RR；**不呼叫 Solver** | EQ 或 EQ*（未保存更細分 label） | 4.8 ms | 未保存逐輪 CV、A/A | 最新 native-core 成功上傳 |
| `q261_rr_vqe4_positive` | Native Rust / RR-only | RR；**不呼叫 Solver** | EQ 或 EQ*（未保存更細分 label） | 6.5 ms | 未保存逐輪 CV、A/A | 最新 native-core 成功上傳 |

Native source parsing is outside the modeled timed region. The 1.1–42.7 ms numbers belong to the *experimental* native benchmark, not identical exact-HEAD performance from the latest PR. Formal native-core run succeeded, but its exact numeric values are held remotely in CodSpeed, not locally exported.

## D. **實際 CI 成本**（GitHub runner wallclock；工作層級，而非逐案例）

| 工作／證據 | 結果 | Runner job elapsed | CodSpeed measure / action | Build/compile | 解釋 |
|---|---|---:|---:|---:|---|
| QASM261 5-case ABBA × 100 rounds（run 41589357492） | SUCCESS | **459 s** | 213 s | 226 s | 5 個案例共享同一個 job；無逐案例邊際成本 |
| QASM261 standalone native 5-case（同 run） | SUCCESS | **156 s** | 20 s | 125 s | 正式 PR 已整合 native-core，避免獨立重編譯 |
| QASM261 source audit（同 run） | SUCCESS | 9 s | 4 s (source check) | — | 不是 CodSpeed 回歸測量 |
| 歷史七組 paired（run 41589264308） | SUCCESS | **220 s** | 71 s action | 未單獨證實 | 3 輪每 revision，實際 14 URIs |
| 最新九組 paired（run 41594571639） | **FAIL** | **268 s** | 79 s action | 未單獨證實 | 後四個 versioned base/head 呼叫在 Solver 前就失敗；**不代表九組有效 CI 成本** |
| 最新三十個 Rust native（同最新 run） | SUCCESS | **198 s** | 44 s action | 未單獨證實 | 完整測得 30 IDs，數值留 CodSpeed 遠端 |
| 舊版五分片 Simulation（run 41589264308） | SUCCESS | **494 / 235 / 479 / 395 / 327 s** | 見原始 artifacts | 分片各自準備 | 合計 **1,930 runner-s**，平行執行；最長單片 494 s（不等於總 wallclock） |

**Timing caveats:** elapsed was calculated from earliest/latest GitHub job log timestamps for successful formal workflows; research run's job-stage timing came from stored machine-readable selection evidence. Action duration can include CodSpeed initialization/upload overhead and is not the sum of per-benchmark instrument medians. Cache state and concurrent job scheduling affect CI cost.

## E. 最新整合阻礙（獨立於實驗證據）

- [PR #131 HEAD `542eded`, Actions run #41594571639](https://github.com/PhysicsQoo/QuPRS/actions/runs/41594571639) completed **FAIL**, even though native-core succeeded and other CI groups passed.
- Root cause evidenced in the paired job log: `test_pr_solver_walltime.py` adds `random_rotation`, `hybrid`, **and an extra** `qiskit-2.6.1-opt0` positional argument. Current `solver_case.py` accepts at most the first two optional arguments (`len(sys.argv) in (7,8,9)`), so four QASM261 base/head requests exit `1` with usage help **before reaching any Solver**. This is a harness contract defect, not observed WMC false classification.
- The valid research ABBA results remain independent evidence; **do not label all nine PR pairs as completed or performance certified**. Correct the argument contract in the code PR and wait for exact-SHA nine-case success before promoting their formal status.

## F. 優先選樣決策

1. **Maintain 7 legacy + 2 Q261 negative pairs** *after the CLI mismatch is fixed and formal CI passes*. This already adds true NEQ and QFT16 slow-path coverage.
2. **First real missing axis: WMC-only = 0** in retained evidence. An existing circuit and source pair can be reused for a distinct, versioned WMC-only identity, but measure genuine solver invocation and assess 3-round CodSpeed cost before admission.
3. **Python gap:** only the two legacy VQE4 Solver pairs have Python evidence; no Q261 pilot Python paired data. Prefer QAOA7/QFT16 Python / GPMC opt-in before adding more overlapping Rust/Hybrid VQE.
4. **Positive WMC gap:** Q261 VQE8-positive is already a verified WMC-positive with high CV; select periodic/opt-in until noise is qualified.
5. **Large/structural WMC gap:** Graphstate16/32 and QPE-exact8 Q261 pilots end in RR, so do **not** count them as WMC-inclusive even if assigned GPMC. New genuine WMC workloads need a bounded source-pinned pilot.
6. **Cost policy:** preserve original 32 historical IDs, five shards, versioned 24 Q261 Simulation identities, 30 native Rust and current seven legacy cases; no expensive rerun or P5 numerical threshold solely for documentation.

**Companion machine-readable coverage:** [codspeed-solver-coverage-matrix.json](codspeed-solver-coverage-matrix.json). `null` denotes absent empirical evidence, never an imputed zero.

## 2026-11-03 最新正式九組驗收：配對 WallTime 已成功（追補證據）

**此節是後續實測追補，先前表 A/B/D/E 均保留當時 SHA 的歷史快照**，請以此節辨識最新正式九組狀態，不能把前一輪失敗覆寫成成功。正式 PR [`ce51fd6`](https://github.com/PhysicsQoo/QuPRS/commit/ce51fd6155c381c84d41c1031ccd109982b9ea64) 對 `dev@2dd451e` 的 [CodSpeed workflow #41598328358](https://github.com/PhysicsQoo/QuPRS/actions/runs/41598328358) 中，paired job `125791567259` **SUCCESS**，9/9 base/HEAD paired identities 共 18 URIs、均實際呼叫 Solver。原始 [CodSpeed + provenance artifacts](https://github.com/PhysicsQoo/QuPRS/actions/runs/41598328358/artifacts/13213217186)。

| Case | Backend/Solver | 最短 base → HEAD (ms) | Median 變化（3/3 輪） | CV base/head | Verdict | 限制 |
|---|---|---:|---:|---:|---|---|
| `grover4_ganak` | Rust/Ganak | 770.01 → 786.48 | +3.31% | 2.97%/6.18% | EQ*→NEQ | Ganak print-limited |
| `q261_qaoa7_negative` | Rust/GPMC | 575.42 → 549.99 | -3.80% | 0.77%/1.20% | NEQ→NEQ | GPMC WMC confirmed |
| `q261_qft16_negative` | Rust/GPMC | 2350.31 → 920.05 | -59.81% | 0.64%/1.62% | NEQ→NEQ | GPMC WMC confirmed |
| `qaoa7_gpmc` | Rust/GPMC | 559.63 → 605.02 | +6.87% | 2.53%/1.14% | EQ→EQ | GPMC |
| `qft16_gpmc` | Rust/GPMC | 1394.48 → 1195.71 | -12.10% | 2.48%/2.79% | EQ*→EQ* | GPMC |
| `vqe4_ganak` | Rust/Ganak | 759.20 → 813.29 | +8.34% | 1.55%/1.89% | EQ*→NEQ | Ganak print-limited |
| `vqe4_ganak_python` | Python/Ganak | 960.82 → 1056.12 | +10.38% | 1.52%/2.25% | EQ*→NEQ | Ganak print-limited |
| `vqe4_gpmc` | Rust/GPMC | 608.91 → 570.43 | -18.43% | 8.20%/4.62% | EQ*→EQ* | GPMC noisy |
| `vqe4_gpmc_python` | Python/GPMC | 740.67 → 690.45 | -12.95% | 10.37%/12.91% | EQ*→EQ* | GPMC noisy |

兩組新增 QASM261 NEQ 均以 **`rr=1e-10`、`distance=1e-8`、`phase=1e-8`、GPMC `-prec=90`** 比較：舊版 `dev` 的 `TOLERANCE` 與實際 Rust adapter 90 位來源在執行時驗證，HEAD 使用公開 per-call 90 位設定；不是沿用舊實驗沒有真正套用的參數標籤。QFT16 median −59.81%、QAOA7 median −3.80% 是真實 CodSpeed **觀測**，非算術精度或顯著性認證。Ganak 三組為印出數值解析度不足的條件式計時，**不可視為科學 EQ PASS**。

目前九組工作 elapsed **266s**，歷史七組成功工作 **220s**，增加 46s 為跨次 CI 觀察差；快取/建置與併行 runner 差異未控制，不可直接當作兩個新增案例的邊際成本。六組 WMC-only/Python/Ganak 覆蓋候選已在後續 [manual Run #41600679301](https://github.com/PhysicsQoo/QuPRS/actions/runs/41600679301) 進行**單輪** CodSpeed 測試並上傳 [artifact #13213994435](https://github.com/PhysicsQoo/QuPRS/actions/runs/41600679301/artifacts/13213994435)；**逐案例 science JSONL、instrument/manifest 已實際核對：六組均 COMPLETED、exit=0、solver_invoked=true、verdict 符合研究案例假設；仍非獨立 operator/Solver 算術認證，未納入每 PR 正式測項。**詳見 [候選驗收文件](codspeed-qasm261-coverage-gap-pilot.md)。本節不是全體八個 PR workflow 已通過的宣告；仍須檢查完整 CodSpeed cross-validate 與其他 CI job。


## F. 2026-11-03 六組 Pilot 原始證據逐筆稽核（目前最新版）

本節直接讀取 [Actions #41600679301](https://github.com/PhysicsQoo/QuPRS/actions/runs/41600679301) 的 [原始 artifact #13213994435](https://github.com/PhysicsQoo/QuPRS/actions/runs/41600679301/artifacts/13213994435)（`candidate-pilot-science.jsonl`、`candidate-pilot-codspeed.json`、`manifest.json`），並核對 [CodSpeed 官方 run 6ae9962b](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6ae9962b054dbb193744c042) 及 `qasm_variant_audit.json` 來源登錄。六筆 JSONL 均 `COMPLETED`、退出碼 0、`solver_invoked=true`、實際判定符合 expected，6/6 為 `ELIGIBLE_FOR_INDEPENDENT_ORACLE_REVIEW`；0 timeout。原始 CodSpeed JSON SHA256 `68c35bfb104a1d3d1e5551b758a7f17ea6796faee7fe4f19607ff031071cf042` 與 manifest 相符，six unique case IDs 對 six official WallTime benchmark URIs 一對一。

| Candidate | Backend / Method / Solver | Actual stage / verdict | Single-round official CodSpeed WallTime | Scientific status |
|---|---|---|---:|---|
| `q261_gap_qaoa7_neq_wmconly_rust_gpmc` | Rust / WMC-only / GPMC | WMC, NEQ | 547.914 ms | Pilot eligible; independent operator oracle pending |
| `q261_gap_qaoa7_neq_wmconly_python_gpmc` | Python / WMC-only / GPMC | WMC, NEQ | 754.322 ms | Pilot eligible; independent operator oracle pending |
| `q261_gap_qaoa7_neq_hybrid_python_gpmc` | Python / Hybrid / GPMC | WMC, NEQ | 788.577 ms | Pilot eligible; independent operator oracle pending |
| `q261_gap_qft16_neq_hybrid_python_gpmc` | Python / Hybrid / GPMC | WMC, NEQ | 1379.078 ms | Pilot eligible; independent operator oracle pending |
| `q261_gap_vqe8_eq_wmconly_rust_gpmc` | Rust / WMC-only / GPMC | WMC, EQ | 876.605 ms | Pilot eligible; printed Solver arithmetic uncertified |
| `q261_gap_qaoa7_neq_hybrid_rust_ganak` | Rust / Hybrid / Ganak | WMC, NEQ | 717.095 ms | Pilot eligible; **Ganak print resolution caveat** |

**精度及科學界線：** 執行數值政策 `rr=1e-10`、`distance=1e-8`、`phase=1e-8`、GPMC 30 digits；Ganak case 的 `wmc_print_resolution_distance=1.1360936307389317e-05`，高於所求的 1e-8。獨立 `qasm_variant_audit.json` 中 QAOA7/QFT16/VQE8 的 Python/Rust × Hybrid/WMC-only 均有相符分類觀察，但負例 `full_operator_neq_certified=false`；這不是完整高精度算子真值證書。可**認證本次實際執行、Solver provenance 與 observation-vs-case-oracle 一致性**，不可認證 Solver 算術誤差上界或一切 full-operator correctness。保留 Ganak 科學／計時分離。

**量測界線：** 六組僅一輪，無 CV、沒有 base/HEAD，非 Macro Runner、服務端六組均有 WallTime reliability warning 及 unresolved flamegraph。workflow 約 127 秒、pytest 測試階段 16.09 秒，不是每個案例的 CI 邊際成本。**已觀測 WMC-only = 3，新正式 every-PR 晉升 = 0**；歷史未測不補值。詳細 machine-readable 維度見 [同名 JSON](codspeed-solver-coverage-matrix.json) 的 `post_merge_six_case_observations`。


## G. 2026-11-03 P5: independently sourced EQ/NEQ and first WMC-only same-SHA repeatability

**Independent science (no QuPRS Solver, no CodSpeed):** [Actions #41608129315](https://github.com/PhysicsQoo/QuPRS/actions/runs/41608129315) succeeded; [raw artifact #13217731272](https://github.com/PhysicsQoo/QuPRS/actions/runs/41608129315/artifacts/13217731272). Qiskit 2.6.1/QASM-sha-pinned complex128 evidence: QAOA7 7q positive phase-aligned dense-operator residual `6.21e-15`, negative residual **1.31256**; VQE8 8q positive dense-operator residual **8.51e-15**; QFT16 16q three input-state witnesses (0, 256, 65535) support source NEQ with a finite-precision derived conservative projective distance lower witness **≥0.00317**, without building 65536×65536 unitary. These are strong independent physical source observations, **not** rigorous floating-point intervals or solver arithmetic certification. Ganak's `1.136e-5` printed distance resolution vs requested `1e-8` remains separately annotated.

**One case only, same merged-dev verifier:** [Actions #41608434240](https://github.com/PhysicsQoo/QuPRS/actions/runs/41608434240) **SUCCESS**; [raw artifact #13218526409](https://github.com/PhysicsQoo/QuPRS/actions/runs/41608434240/artifacts/13218526409); [official CodSpeed run 6ae9a4d2](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6ae9a4d265e3e2a58617fac9). Only `q261_gap_qaoa7_neq_wmconly_rust_gpmc`: complete actual GPMC WMC-only verifier on fixed `dev@a4c7b126`, `rr=1e-10, distance=1e-8, phase=1e-8, GPMC digits=30`, exactly **3** measured rounds, one iteration per round, no pre-measurement warmup (the instrument reports one warmup iteration). Runner **AMD EPYC 7763** / GitHub-hosted non-Macro: min **797.016 ms**, median **810.083 ms**, max **817.131 ms**, mean **808.077 ms**, stdev **10.206 ms**, CV **1.26%**. Original six-case exploratory pilot ran on **AMD EPYC 9V45**: its **547.914 ms** cannot be compared to this new runner as a version effect. Current science JSON records one final `COMPLETED/solver_invoked=true/NEQ`; it does **not** independently log every one of the three timed invocations. Full workflow elapsed ~144 seconds, actual 3 measured benchmark rounds total ~2.425 seconds; incremental cost of adding to an existing paired Job **unmeasured**.

**Admission conclusion:** one Rust WMC-only QAOA7 NEQ candidate is **OPT_IN_SHORTLIST**, not yet `EVERY_PR`. Python QAOA7 WMC-only is conditional/periodic, VQE8 EQ WMC-only periodic, Python QFT16 Hybrid opt-in stress, and Ganak NEQ opt-in with print-limit provenance. Keep official nine paired identities, five shards and 32 protected historical Simulation IDs unchanged. New future verifier code changes can evaluate a real same-QASM/precision/instrument dev→PR-HEAD pair; no fictitious `dev@a4c7b126` vs itself benchmark is needed. Machine-readable stats/decisions are recorded in [coverage JSON](codspeed-solver-coverage-matrix.json) under `qoo165_one_case_same_sha_repeatability` and `qoo165_candidate_admission_decisions`.


## H. 2026-11-03 current merged-dev official 86-Simulation service inventory

Connected official CodSpeed read of [dev run 6ae99835](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6ae9983573a73c5663fc2a15), exact merged `dev@a4c7b12652b3c59c086f5d408a95e004df570bad`, yielded **86 actual Simulation benchmark identities**: 32 original legacy, 24 additive QASM261 Python/Rust/method URI identities, and 30 Rust native/core identities. All exact URIs and displayed rounded units (s/ms/µs) are preserved in [machine-readable coverage matrix](codspeed-solver-coverage-matrix.json) under `current_merged_dev_codspeed_simulation`. **The service's displayed numbers are rounded, not 86 full-precision per-case valgrind metrics**; hardware cohort per job is not proven identical.

The service flags **19 syscall-dominated Simulation rows** (CPU simulation ignores real syscall/subprocess time). Three directly queried, full-precision independent service examples:

| Exact source/URI representative | Modeled CPU total | Syscall time excluded | Syscalls | Interpretation |
|---|---:|---:|---:|---|
| QFT16 legacy Rust/GPMC | 57.9898 ms | 3251.684 ms | 1567 | Solver-related syscalls dominate; not end-to-end WallTime |
| QASM261 native Rust QFT16 Miter+RR | 42.7190 ms | 0.0159 ms | 5 | True native RR hot-path CPU measurement |
| QASM261 versioned Rust QAOA7/GPMC Simulation | 17.1680 ms | 0.2103 ms | 25 | Modeled CPU only; cannot infer external GPMC execution |

These rows are **not** a paired equal-workload comparison and must not be combined or compared as version speedups. The old formal PR nine-pair Solver-inclusive WallTime [workflow #41598328358](https://github.com/PhysicsQoo/QuPRS/actions/runs/41598328358) is a **different exact commit/run/instrument**, even though final PR tree and merged dev tree are equivalent. The same-sha 86-case CPU service record does not contain fresh dev vs new-HEAD paired Solver WallTime. A future verifier code PR can run that comparison with exact QASM, numerical policy and same-runner provenance.

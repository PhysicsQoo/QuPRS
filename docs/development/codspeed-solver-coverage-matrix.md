# QuPRS CodSpeed Solver-inclusive / Native RR 既有實驗測項覆蓋矩陣

> **2026-11-03 evidence-only snapshot.** Base `dev@2dd451e`, formal PR #131 `@542eded`, independent research branch `@91d7a62` before this documentation commit. All figures trace to official CodSpeed reports and GitHub Actions logs. **No new benchmarks were run.**

## 範圍及分類規則

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

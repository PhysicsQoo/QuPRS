# QOO-157 — GPMC tree-decomposition 38-digit scoped ablation (2026-11-04)

**New experimental result:** GPMC's default `-td -vs=1` was faster than `-no-td -vs=1` on two identical QuPRS weighted CNFs, while the source WMC counts remained concordant. This is **source-pinned, same-run, hosted CodSpeed WallTime OBSERVATION_ONLY**, not an ABBA/Macro Runner significance certificate or a measured explanation of *all* GPMC-versus-d4 performance differences.

## Evidence and scope

- [GitHub Actions SUCCESS #41833961150](https://github.com/PhysicsQoo/QuPRS/actions/runs/41833961150), measured QuPRS commit `c1a6126737f842efd42f1dca9d69119685a3da89`; [artifact 13324047224](https://github.com/PhysicsQoo/QuPRS/actions/runs/41833961150/artifacts/13324047224).
- [Official CodSpeed run 6aeb2c5f4988944a265b8fa3](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aeb2c5f4988944a265b8fa3), WallTime instrument, **4/4 cases, three measured rounds per case**, before CodSpeed service reports non-Macro-Runner WallTime reliability warning. CodSpeed also reports *no flamegraph* on the four benchmarks. Do not claim subroutine attribution from this run.
- Same fixed GPMC gitlink: `PhysicsQoo/GPMC@a1bda3489e959d3695b6798d327c5a1fc1bed305`. Freshly compiled native GPMC binary SHA256 `b4169bce97c995accfca5ef2246d7283af0ded3370391dec7cd852eb3fcb67ce`.
- Fixed source exact weighted CNFs from original [effective-precision CI #41822549728](https://github.com/PhysicsQoo/QuPRS/actions/runs/41822549728), SHA verified against its science report prior to ablation. Source precision identical in both variants: **GPMC `-prec=38` = 127 MPFR bits**, same printed 38 significant digits.
- This is **prepared-CNF, external-solver inclusive**; includes subprocess launch, input parse, GPMC preprocessing/TD/search, and stdout. Excludes QuPRS QASM parsing, RR, Path-sum and CNF generation. The two variants differ **only** in `-td` vs `-no-td`; `-vs=1` and all other GPMC defaults remain unchanged.
- Reproducible files: [gpmc_td_ablation.py](gpmc_td_ablation.py), [test_codspeed_gpmc_td_ablation.py](test_codspeed_gpmc_td_ablation.py), [isolated workflow](../../.github/workflows/qoo157-gpmc-td-ablation.yml). The original source-CNF structural audit is [SOURCE_CNF_STRUCTURE_AUDIT.md](SOURCE_CNF_STRUCTURE_AUDIT.md).

## Official CodSpeed v5 results and distinct statistics

| Same original source CNF | GPMC 38d + TD median | GPMC 38d no TD median | No-TD / TD | Fractional time saved by TD | TD / no-TD official **min** |
| --- | ---: | ---: | ---: | ---: | --- |
| QAOA7 genuine NEQ | **26.888376 ms** | 48.849411 ms | **1.81675×** | **44.96%** | 26.866789 / 48.527724 ms |
| QFT16 EQ | **1115.339836 ms** | 1269.598577 ms | **1.13831×** | **12.15%** | 1114.512656 / 1265.700632 ms |

**Do not combine medians with the CodSpeed official min headline.** Both come from this *same* experiment artifact but describe different statistics. For the official **minimum** comparison, no-TD/TD ratios are QAOA7 **1.80623×** and QFT16 **1.13565×**, preserving the observed advantage direction.

Scientific admission: both cases `COUNT_CONCORDANT_UNCERTIFIED` under the original 1e-12 scaled count screen. Maximum component differences between TD/no-TD printed complex counts are `2e-15` (QAOA7) and `2.6469779601697e-23` (QFT16). Supplementary exact **printed-value rational** comparison against the original 38-digit archived GPMC science report found the **TD-enabled** values exactly equal for both cases (not a bytewise stdout/text comparison); TD-disabled differs only in the tiny components noted above. Solver internal error remains **NOT_CERTIFIED**.

## Source-backed runtime mechanism

With `-td -vs=1`, both cases produced `FlowCutter is running...`; neither emitted `skip td` or `ignore td`. With `-no-td -vs=1`, no FlowCutter marker was observed. Under pinned [GPMC `Counter.cc::computeTDScore`](https://github.com/PhysicsQoo/GPMC/blob/a1bda3489e959d3695b6798d327c5a1fc1bed305/core/Counter.cc), the `ignore td` branch is taken if TD-based extra scores are not usable. Thus native logs are consistent with actual, accepted TD-based scores, **not a disabled or bypassed TD path**.

The `Primal graph` native line (computed **after** GPMC preprocessing) records:
- QAOA7 `nodes=316, edges=516` (original weighted CNF was 470 variables, 823 clauses).
- QFT16 `nodes=383, edges=820` (original weighted CNF was 486 variables, 1,144 clauses).

These are **not** counts of actual cache hits, branching decisions, or a direct measure of TD's individual preparation cost. They establish that GPMC's weighted preprocessing changes the Boolean instance prior to its TD heuristic. Do not compare these post-preprocessing graph edges to original clause count as though they were the same graph metric.

## Interpretation and next decisive experiment

This is the **first direct scoped measurement** supporting a concrete source mechanism: on the tested QAOA7 and QFT16, enabling GPMC's default tree decomposition/branching path improved solver-inclusive elapsed time within the same hosted CodSpeed run, with source and scientific count agreement. It cannot prove a universal improvement, explain GPMC/d4 ratios, or isolate whether the benefit comes from the TD scores rather than interactions with other default GPMC mechanisms.

**Next targeted ablation:** `-vs=0/1` × `-td/-no-td` on these two identical source CNFs at 38 digits, retaining first-party CodSpeed and original count admission. This would separate the main TD-score prioritization from the mixed frequency/activity heuristic, before attempting weighted-preprocessing `-pp_ee` on/off. Only widen to GPMC versus d4 after the benefit and underlying stage counters are reproducible. Preserve the existing GPMC default; do not rerun full five CodSpeed shards for this pilot.

**Execution caveat:** the initial workflow [#41833917076](https://github.com/PhysicsQoo/QuPRS/actions/runs/41833917076) passed its source and science preflight but failed its benchmark step because the fresh Python environment lacked `pytest`; it is a **non-scientific setup failure**, superseded by source-pinned successful [#41833961150](https://github.com/PhysicsQoo/QuPRS/actions/runs/41833961150), which explicitly installed `pytest-codspeed==5.0.3` and `pytest`. Do not treat the initial failed run as a solver or numeric failure.

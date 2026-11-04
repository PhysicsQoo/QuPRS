# QOO-157 P4 — GPMC cache capacity: safe bounds and native work (2026-11-05)

## Native science admission

[Actions #41931718059 SUCCESS](https://github.com/PhysicsQoo/QuPRS/actions/runs/41931718059) HEAD `9134d62fc57bccbd3cc59b0461fbb7a584597fa4`, artifact `13372585940`. Pinned unmodified GPMC `a1bda3489e959d3695b6798d327c5a1fc1bed305`; unchanged original weighted Grover4 EQ and QFT16 EQ CNF SHA from source science run `41822549728`. Effective 38 decimal digits / MPFR127; `-mode=1 -prec=38 -vs=1`, TD on/off, cache `-cs=16/64/4000`. **12/12** source-aligned complex WMC scientific count screens passed. **No performance measurement** in this Actions; native counters are not elapsed time.

### Why `-cs=1` is not a safe cache-disabled control

[Fixed GPMC `core/Config.cc` L12](https://github.com/PhysicsQoo/GPMC/blob/a1bda3489e959d3695b6798d327c5a1fc1bed305/core/Config.cc#L12) accepts `-cs` from **1 MB**; this is a capacity limit, **not** a `cache-off` option. [`ComponentCache.cc` L58–70](https://github.com/PhysicsQoo/GPMC/blob/a1bda3489e959d3695b6798d327c5a1fc1bed305/core/ComponentCache.cc#L58-L70) calls `table_.resize(900001,NULL)`, accounts for `sizeof(CacheBucket*) * table_.capacity()` and compares against `cachesize * 1048576`. On the 64-bit Linux target, the pointer table alone uses at least 7,200,008 bytes = ~6.87 MiB, before class and other allocations. Thus `-cs=1` is already below the internal accounted minimum before inserting the first cache entry.

[`createEntryFor` L74–83](https://github.com/PhysicsQoo/GPMC/blob/a1bda3489e959d3695b6798d327c5a1fc1bed305/core/ComponentCache.cc#L74-L83) calls `deleteEntries()` once the bound is met; [`deleteEntries` L179–188](https://github.com/PhysicsQoo/GPMC/blob/a1bda3489e959d3695b6798d327c5a1fc1bed305/core/ComponentCache.cc#L179-L188) indexes `scores[scores.size()/2]` without a nonempty guard. On first root insertion the entry list contains only a dummy, so no deletable candidates are available: **undefined-behavior risk from source**. No intentionally unsafe crash test was executed, no upstream solver patch or production change. A 1 MB cap must *not* be used as GPMC cache-off or benchmark evidence.

### Native decision and eviction controls

| Source | TD | 16 MiB cache evictions | 64 MiB evictions | 4000 MiB evictions | Decisions (16 / 64 / 4000 MiB) |
| --- | --- | ---: | ---: | ---: | ---: |
| Grover4 EQ | on | 0 | 0 | 0 | 2,508 / 2,508 / 2,508 |
| Grover4 EQ | off | **12** | 0 | 0 | **185,234 / 165,683 / 165,683** |
| QFT16 EQ | on | **2** | 0 | 0 | **67,294 / 66,695 / 66,695** |
| QFT16 EQ | off | **3** | 0 | 0 | **74,869 / 72,169 / 72,169** |

The 16 MiB cache causes **+11.800%** more decisions on Grover TD-off, **+0.898%** on QFT TD-on, and **+3.741%** on QFT TD-off relative to 64 MiB. All printed native `Cache hit` and `Cache lookup` counters are kept in immutable artifact `13372585940`; higher absolute cache hit counts with 16 MiB are **not** evidence of higher efficiency, because more search is performed. Across all four controls, 64 MiB and 4000 MiB have the **same entire native search counter vector**, not just equal decision totals, and no evictions. That does **not** prove identical heap allocations or elapsed time.

### Official CodSpeed follow-up (separate timing instrument)

[CodSpeed research workflow](../../.github/workflows/qoo157-gpmc-cache-capacity-codspeed.yml) introduced in [commit `1c9dd9c5`](https://github.com/PhysicsQoo/QuPRS/commit/1c9dd9c5c8d2a52a8eb1e04631b0af3f66a55b7b); [Actions #41932161536](https://github.com/PhysicsQoo/QuPRS/actions/runs/41932161536). Only 2 circuits × TD-on/off × cache 16/64 MiB **8 official CodSpeed v5 WallTime identities**, each gated by 12 **fresh same-run native WMC/structural science** settings on the actual compiled GPMC binary. Deliberately omits redundant 4000 MiB timed arm. **Timing verdict pending at document creation**; this science-only source cannot supply a performance ratio. Hosted WallTime without fixed Macro Runner ABBA/BAAB is **OBSERVATION_ONLY**, never a production numerical/performance acceptance gate.

Next research owner [QOO-157](https://linear.app/qoogohome/issue/QOO-157). Keep recommended default GPMC, d4 as research-only and Ganak precision qualification under QOO-98. No changes to dev/main or routine CodSpeed CI.

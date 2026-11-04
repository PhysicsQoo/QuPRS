# QOO-157 P3 — GPMC cache-query denominator native verification (2026-11-05)

## Verdict

**`GPMC_CACHE_DENOMINATOR_INDEPENDENT_NATIVE_COUNTER_PASS_8_OF_8`** on source-pinned experiment HEAD [`7efae9ec`](https://github.com/PhysicsQoo/QuPRS/commit/7efae9ecb649c57419f511b34d7665220c17e96f); [GitHub Actions #41930925045 SUCCESS](https://github.com/PhysicsQoo/QuPRS/actions/runs/41930925045), artifact `13372465327`. All four original QuPRS weighted-CNF sources × TD-on/off, fixed GPMC gitlink `a1bda3489e959d3695b6798d327c5a1fc1bed305`, 38 effective decimal digits / MPFR127, `-mode=1 -prec=38 -vs=1 -cs=4000`.

This **science-only** run independently compiled an **unmodified** pinned GPMC and an instrumented **temporary source copy**. Added two integer counters *only*: requests before the empty-bucket guard and failures caused by an absent bucket. No released third-party source, QuPRS submodule, dev/main, solver selection, routine CI, or CodSpeed changed. Binary SHA256 and the precise original-vs-instrumented source SHA256 diffs are included in the immutable artifact.

## Why the previous printed cache hit ratio was biased

At pinned [`ComponentCache.cc::requestValueOf` L152–175](https://github.com/PhysicsQoo/GPMC/blob/a1bda3489e959d3695b6798d327c5a1fc1bed305/core/ComponentCache.cc#L152-L175), the guard `if (!isBucketAt(v)) return false;` precedes incrementing `num_cache_look_ups_`. Thus the original `Cache lookup` excludes unoccupied hash-bucket misses; stdout `Cache hit / Cache lookup` is *conditional on an occupied bucket*, not the global cache-eligible hit rate.

For this exact pinned control flow, `Components` initially includes one root; subsequent non-singleton cache misses are included in `Components-1`, while cache hits are removed from the component stack. The conjectured identity was:

```text
all_eligible_queries = (Components - 1) + Cache hit
empty_bucket_misses = all_eligible_queries - Cache lookup
eligible_cache_hit_ratio = Cache hit / all_eligible_queries
```

The instrumented `all_queries` and `empty_bucket_misses` are **independent direct native counters**, not recomputed inside the C++ probe from `Components`; they matched those two predicted identities on **all eight configurations**. Same-run native **WMC printed complex values** and unmodified search counters `conflicts, decisions, propagations, Components, Split, Cache lookup, Cache hit, Cache reduce` agreed 8/8 between original and instrumented binary. Source count-screen remains `COUNT_CONCORDANT_UNCERTIFIED`, not an error bound on internal MPFR arithmetic.

| Original weighted source | TD | Direct eligible queries | Direct empty-bucket misses | Direct eligible hit rate | Matched baseline native search |
| --- | --- | ---: | ---: | ---: | --- |
| Grover4 EQ | on | 8,889 | 2,492 | 71.785% | PASS |
| Grover4 EQ | off | 786,766 | 151,188 | 78.941% | PASS |
| QAOA7 genuine NEQ | on | 3,526 | 997 | 71.526% | PASS |
| QAOA7 genuine NEQ | off | 11,096 | 2,623 | 76.136% | PASS |
| QPE exact8 EQ | on | 11,999 | 2,760 | 76.956% | PASS |
| QPE exact8 EQ | off | 17,390 | 4,798 | 72.312% | PASS |
| QFT16 EQ | on | 200,343 | 64,202 | 66.710% | PASS |
| QFT16 EQ | off | 221,791 | 69,343 | 67.461% | PASS |

**Scientific interpretation:** TD-on does not universally improve the actual cache hit percentage (decreases in Grover4, QAOA7, QFT16); instead it substantially reduces **number of newly explored cache-eligible subcomponents**: Grover4 786,766→8,889, QAOA7 11,096→3,526, QPE8 17,390→11,999, QFT16 221,791→200,343. This is search-work causality within GPMC, **not** a measured runtime multiplier or proven GPMC-vs-d4 cache-only share. Prior official [VS×TD CodSpeed #41836818679](https://github.com/PhysicsQoo/QuPRS/actions/runs/41836818679) and [shared-SCC P0 CodSpeed #41846122379](https://github.com/PhysicsQoo/QuPRS/actions/runs/41846122379) remain separate performance evidence.

## First failure is retained, not overwritten

First workflow [#41930491499](https://github.com/PhysicsQoo/QuPRS/actions/runs/41930491499), HEAD `0cf4481`, compiled both binaries and passed initial source prerequisites but **failed** because original vs instrumented `qpeexact8_eq / td_on` native search counters differed. Its partly generated artifact is `13371301834`. This run is **not a pass or performance result**. The follow-up [`7efae9ec`](https://github.com/PhysicsQoo/QuPRS/commit/7efae9ecb649c57419f511b34d7665220c17e96f) preserved the C++ instrument itself but added complete original/instrumented counter evidence, on-mismatch same-binary repeat controls and separate semantic-vs-search-identity gates. Its second CI [#41930925045](https://github.com/PhysicsQoo/QuPRS/actions/runs/41930925045) passed with **no cross-binary search mismatches** across eight configurations; as no repeat controls were activated on that successful run, the cause of the first-run divergence **remains unassigned**. One success does not certify all runners or compiler layouts reproducible; do not discard the first failure.

## Next bounded study and admission

1. Check whether direct cache-miss identities remain invariant under additional pinned source/runner repetition only if this would affect a decision; no need for routine test reruns.
2. Source-audit `-cs` (GPMC `Config.cc` minimum **1 MB**) and run untimed 1/16/4000 MB science screens on two source CNFs **before** any new CodSpeed. `Cache reduce=0` at 4000 MB is **not cache disabled**.
3. d4 pinned `OptionCacheManager.hpp` has `cache.isActivated` (default `true`) — unlike GPMC capacity-only controls, this can truly disable cache. Require original weighted-CNF/38-effective-digit agreement and source-pinned full WMC before any within-d4 on/off official CodSpeed. d4 warm start is separate: pinned `DpllStyleMethod.hpp::compute(warmStart=true)` calls `warmStart(29,11,…)`.
4. Only with a validated behavioral intervention and material difference, run minimal fixed-runner paired ABBA/BAAB **official CodSpeed** with honest end-to-end cost, RSS, timeout and identical science. Never estimate speed from native counters or GNU time.

GPMC remains QuPRS recommended default; d4 is research-only, Ganak independent precision/projection qualification stays in [QOO-98](https://linear.app/qoogohome/issue/QOO-98), and there is no v0.14.0 release blocker from this P3 science finding.

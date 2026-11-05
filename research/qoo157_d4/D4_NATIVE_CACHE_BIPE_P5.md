# QOO-157 P5 — d4 real cache on/off × BiPe, pinned native scientific screen (2026-11-05)

## Research question

The prior **GPMC cache capacity** pilot measured 16/64 MiB effects under a permanently **enabled** GPMC component cache. GPMC `-cs` is *not* a cache-disable option. To avoid falsely comparing non-equivalent treatments, this P5 experiments with the pinned d4 **real component caching switch** and controls BiPe separately.

**Source verified**: pinned d4 `be15f91f3e9769e1f5cb175fa27e3eca3a1ea690`, [`src/options/cache/OptionCacheManager.hpp`](https://github.com/jm62300/d4/blob/be15f91f3e9769e1f5cb175fa27e3eca3a1ea690/src/options/cache/OptionCacheManager.hpp) exposes `cache.isActivated` (default `true`); [`src/methods/DpllStyleMethod.hpp` L310–314 and L390–401](https://github.com/jm62300/d4/blob/be15f91f3e9769e1f5cb175fa27e3eca3a1ea690/src/methods/DpllStyleMethod.hpp) checks that option before both the `searchInCache` lookup and the `addInCache` insertion. When disabled, `cb` is undefined and `computeDecisionNode` must compute the component. Independent of caching, [`run()` L534–540](https://github.com/jm62300/d4/blob/be15f91f3e9769e1f5cb175fa27e3eca3a1ea690/src/methods/DpllStyleMethod.hpp) invokes `compute(setOfVar,m_out)` which defaults `warmStart=true`, calling `m_solver->warmStart(29,11,...)` at L475–484. **Warm-start is not changed in P5; its effect is not measured by P5.**

## Science-only workflow

[Source-pinned implementation commit `41984e2`](https://github.com/PhysicsQoo/QuPRS/commit/41984e235208949c542da456fbf142d0e1dec184), [GitHub Actions #41936727984](https://github.com/PhysicsQoo/QuPRS/actions/runs/41936727984).

- Source inputs: **original** QAOA7 NEQ and QFT16 EQ weighted CNF from immutable archived scientific source `41822549728`, each SHA-checked, without recompiling QASM or changing weights. The published printed d4-38 complex result is represented as exact rational text and used as the 1e-12 count-scale acceptance anchor. This is **COUNT_CONCORDANT_UNCERTIFIED**, *not an internal GMP numerical-error certificate*.
- d4 source checkout pinned to `be15f91f`; existing research-only `matched_precision_variant.py` patch and existing **output-only** `d4_bipe_instrument.py` in a temporary cloned tree (never in vendor submodule, dev or main). Requested 38 significant decimal digits and actual 128 GMP precision bits validated in native help. Record both resulting binary SHA and exact scratch patch.
- Independent controls: two original circuits × BiPe `auto` / genuinely `preproc-method=none` × `cache.isActivated=true` / `false`, **8 source-controlled native runs**. Native `-h` identifies the exact cache flag prefix; ambiguous help fails closed. Native printed complex value and native recursive calls / decisions / positive cache hits / negative hits are recorded; when caching is `false`, both native cache hits **must be zero**. BiPe `before/after` markers provide dimension controls.
- Each subprocess is capped at **30 seconds**. A cache-off timeout/error becomes **CENSORED**, never a false equality or inferred performance result. Count mismatch, invalid original source SHA, missing native stage markers, cache-off hit evidence or baseline failure blocks science. Original 38-digit WMC counts must concord as described above. **No CodSpeed or timing analysis** in this initial workflow.

## Expected experimental interpretation

A large cache-off increase in native calls while WMC remains concordant is direct source-pinned evidence that d4 benefits from memoized components under the given BiPe policy; it **cannot** by itself establish a d4-vs-GPMC speed gap. A cache-off timeout means only a lower-bound search-hardness observation under the censoring window, **not** an arbitrary slowdown factor. BiPe `auto` vs `none` is used as a **stratum**, not a single-algorithm variant; production d4 warm-start and preprocessing are kept unchanged within each on/off pair.

A conditional *official CodSpeed v5* follow-up should use **only full numeric-screen PASS paired variants** with demonstrated native-work differences; for very expensive cache-off runs, retain no-performance/censored status. Prefer fixed Macro Runner ABBA/BAAB; GitHub-hosted WallTime alone is observational, not production acceptance. No release blocker or solver-default change.

### Evidence status

The workflow was triggered at source commit `41984e2`. The completed gate results, if available, should be appended with the exact run outcome and artifact ID; no WMC/counter/time values are asserted before retrieval.


## Completed P5 scientific result — native 7/8 PASS, one censored (not a failure of WMC)

[Workflow #41937369604 SUCCESS](https://github.com/PhysicsQoo/QuPRS/actions/runs/41937369604), measured HEAD `464b86e4dabd6b7ff55cfef8df57858297041caf`, immutable [science artifact 13374532991](https://github.com/PhysicsQoo/QuPRS/actions/runs/41937369604/artifacts/13374532991), d4 scratch binary SHA256 `08b486858818cedddf19993d43db6e20800e76c5caed213cdda94da18363452e`.

The first [workflow #41936727984](https://github.com/PhysicsQoo/QuPRS/actions/runs/41936727984) compiled d4 but failed its help-format guard before executing any scientific cases: pinned optree prints a **hierarchical** `dpll/ → cache/ → isActivated`, not a literal expanded `--cache.isActivated`. The exact native cache flag is **`--dpll.cache.isActivated=(true|false)`**. The [guard fix `464b86e4`](https://github.com/PhysicsQoo/QuPRS/commit/464b86e4dabd6b7ff55cfef8df57858297041caf) was tested against the archived `-h` text and retained the same source/pinned numeric patch; the second workflow completed. Preserve both CI records; the first is **not** a solver numeric failure or timing result.

| Original weighted source | BiPe | d4 cache | Complex count screen | Native decisions | Native recursive calls | Native positive / negative hits | Final active clauses |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| QAOA7 genuine NEQ | auto | ON | PASS | 926 | 1,853 | 2,138 / 926 | 677 |
| QAOA7 genuine NEQ | auto | OFF | PASS | 2,346,830 | 4,693,661 | 0 / 0 | 677 |
| QAOA7 genuine NEQ | none | ON | PASS | 971 | 1,943 | 2,205 / 971 | 823 |
| QAOA7 genuine NEQ | none | OFF | PASS | 2,477,422 | 4,954,845 | 0 / 0 | 823 |
| QFT16 EQ | auto | ON | PASS | 66,695 | 133,391 | 133,084 / 66,695 | 1,058 |
| QFT16 EQ | auto | OFF | PASS | 590,177 | 1,180,355 | 0 / 0 | 1,058 |
| QFT16 EQ | none | ON | PASS | 426,163 | 852,327 | 917,484 / 426,163 | 1,144 |
| QFT16 EQ | none | OFF | **CENSORED_TIMEOUT 30s** | n/a | n/a | n/a | n/a |

For **each of the three completed cache ON/OFF pairs** the printed *complex* count (real and imaginary) was **exactly identical** between on and off. All seven completed settings also agreed with the archived original source d4-38 printed-rational reference under the explicit 1e-12 count-scale screen. Different BiPe strata may produce different last printed digits (the two QAOA7 strata and the two QFT16 strata do); these remain screen-concordant, not an exact internal arithmetic-error guarantee. Cache-disabled pairs produced exactly zero native cache hits, confirming the CLI flag took effect.

**Concrete search-work effects** (within same source / fixed BiPe / same d4 binary; *not* elapsed time):

- QAOA7 auto: decision count `926 → 2,346,830` (cache disabled: **2,534×** baseline); recursive calls `1,853 → 4,693,661` (**2,533×**). Extra decisions = **2,345,904**.
- QAOA7 none: decisions `971 → 2,477,422` (**2,551×**); recursive calls `1,943 → 4,954,845` (**2,550×**). Extra decisions = **2,476,451**.
- QFT16 auto: decisions `66,695 → 590,177` (**8.85×**); recursive calls `133,391 → 1,180,355` (**8.85×**). Extra decisions = **523,482**.
- QFT16 none: cache ON already visits 426,163 decision nodes (versus 66,695 with BiPe auto); cache OFF did not finish within the 30s science limit. This suggests an interaction of preprocessing and cache work on this original weighted source, **but** no cache-off numeric/WMC or runtime ratio is available for this stratum.

**Scope and causal limits:** d4 **actually disables** `searchInCache` and `addInCache`; thus it is a cleaner within-d4 cache-only intervention than GPMC `-cs`. BiPe auto versus none affects clause sets **and** preprocessing effort; do not attribute BiPe net WallTime to caching. Warm-start `warmStart(29,11,...)` remains unchanged. These counts are **source-pinned native mechanism measures**, not official performance. The 30s timeout is not a "speedup" or WMC verdict and must be retained as censored.

## Conditional official CodSpeed follow-up

[Official v5 scope commit `076a4f3`](https://github.com/PhysicsQoo/QuPRS/commit/076a4f3bd4d4751b5878eddef21921c0de5053a0), [Actions #41938239985](https://github.com/PhysicsQoo/QuPRS/actions/runs/41938239985).

Only QAOA7 auto, QAOA7 none, and QFT16 auto have valid cache-on/off numeric pairs, hence **6 benchmark identities**. The hosted runner rechecks original CNF SHA, actual native binary digest, **all eight** source science cases, same GMP128 / 38 effective digits, and each measured WMC against admitted preflight. QFT16 none/cache off is a **CENSORED exclusion**. Official CodSpeed v5 WallTime with `--codspeed-max-rounds=3 --codspeed-max-time=100` is the only timing instrument. At this document edit, **official runtime measurements were not yet available** and no speedup factor is claimed. Hosted non-Macro WallTime is observation only; formal fixed Macro Runner ABBA/BAAB is not established.

## CacheList native negative-hit semantics — source audit

**Critical semantic correction for interpreting the raw d4 counters:** pinned [`src/caching/CacheList.hpp` L99–120](https://github.com/jm62300/d4/blob/be15f91f3e9769e1f5cb175fa27e3eca3a1ea690/src/caching/CacheList.hpp#L99-L120) increments `m_nbPositiveHit` after the bucket's header and data match succeeds (L110–113); it increments `m_nbNegativeHit` **after the entire bucket chain has been traversed with no match** (L117–119). The confusing native field `Number of negative hit` therefore means **cache MISS**, not a successful hit. `CacheNoCollision.hpp` has the equivalent distinction. The previous on/off totals are native field names exactly, not counts of two different kinds of successful hits.

Thus the actual attempted-component cache *success rate* for the four cache-ON configurations is:
```
actual_cache_success_rate = positive_hits / (positive_hits + negative_hits)
QAOA7 auto = 2138 / (2138 + 926) = 69.7781%
QAOA7 none = 2205 / (2205 + 971) = 69.4270%
QFT16 auto = 133084 / (133084 + 66695) = 66.6156%
QFT16 none = 917484 / (917484 + 426163) = 68.2831%
```
When cache is off, no cache lookup happens and both counters remain 0; **0/0 is undefined**, not zero hit rate. These d4 rates are close in magnitude to the independently verified GPMC cache-eligible rates (66.7%–78.9% in the earlier P3 four-case sweep), **but the opportunity/case/branching distributions are not identical, so there is no justified direct solver ranking from their percentages**.

**Important P5 interaction evidence:** QFT16 BiPe none has **higher measured cache hit fraction** (68.28% vs 66.62% under auto BiPe) but **6.39× more cache-on decisions** (426,163 vs 66,695). Therefore the hit ratio alone is explicitly insufficient to explain search-work efficiency: residual CNF structure, branching and the **number of queried components** matter. This remains an untimed source-level mechanism conclusion, not a cross-solver speed estimate.

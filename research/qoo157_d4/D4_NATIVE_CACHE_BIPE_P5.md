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

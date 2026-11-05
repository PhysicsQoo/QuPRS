# QOO-157 P6 — d4 SAT warm-start mechanism (2026-11-05)

## Motivation and isolated variable

Pinned [d4 `be15f91f3e9769e1f5cb175fa27e3eca3a1ea690`](https://github.com/jm62300/d4/tree/be15f91f3e9769e1f5cb175fa27e3eca3a1ea690) uses [`DpllStyleMethod::run()`](https://github.com/jm62300/d4/blob/be15f91f3e9769e1f5cb175fa27e3eca3a1ea690/src/methods/DpllStyleMethod.hpp#L534-L540) → `compute(setOfVar,m_out)`, implicitly `warmStart=true`. [`compute`](https://github.com/jm62300/d4/blob/be15f91f3e9769e1f5cb175fa27e3eca3a1ea690/src/methods/DpllStyleMethod.hpp#L475-L491) calls `m_solver->warmStart(29,11,decisionVar,m_out)`, then search. [`WrapperSolver::warmStart`](https://github.com/jm62300/d4/blob/be15f91f3e9769e1f5cb175fa27e3eca3a1ea690/src/solvers/WrapperSolver.cpp#L160-L198) first solves with no assumptions to check SAT, then performs 29 SAT calls with up to 11 random-literal assumptions, per-round `solveLimited(...,500)` and `restart()`, then clears assumptions and restarts. This could change learned solver state and cost; it is not only fixed setup work.

**Intervention is solely at `run()`:**

```diff
-    T result = compute(setOfVar, m_out);
+    T result = compute(setOfVar, m_out, false);
```

This also bypasses initial SAT satisfiability screening, so **WMC correctness must be separately admitted**, especially for UNSAT cases. Crucially, the other `count(setOfVar,out,false)` API remains untouched. No unsupported user-facing CLI warm-start toggle is invented.

## Experiment controls

[Research commit `0efc7b3`](https://github.com/PhysicsQoo/QuPRS/commit/0efc7b33a8b2bed62aa8b7eac61402d00fa62002), [P6 scientific Actions `41940731310`](https://github.com/PhysicsQoo/QuPRS/actions/runs/41940731310). Dedicated P6 source-pair script: [`d4_warmstart_science.py`](d4_warmstart_science.py); workflow [`qoo157-d4-warmstart-science.yml`](../../.github/workflows/qoo157-d4-warmstart-science.yml).

1. Clone exact pinned d4 into disposable runner scratch. Apply the **same** established research-only 38-significant-decimal GMP precision patch to Main/Counter and same preprocessor output-only instrumentation. Build warm-**on** binary and archive SHA.
2. Assert the native `src/methods/DpllStyleMethod.hpp` is byte-for-byte equal to upstream commit's version. Patch **the sole run-call line**; preserve the distinct `count` method. Incrementally rebuild with same flags and record warm-**off** binary SHA. Preserve exact warm-off-only unified diff, source SHA and both build logs.
3. Science matrix: **four archived original QuPRS weighted CNFs** `grover4_eq`, `qaoa7_neq`, `qpeexact8_eq`, `qft16_eq` × BiPe default-auto vs `preproc.auto-config=false; preproc.preproc-method=none` × warm-on/off (**16** native source observations, eight matched pairs). All retain **d4 component caching ON**, preserving its important demonstrated benefit. The same original CNF SHA and reference d4-38 exact printed-rational complex values are required. Native precision **38 effective decimals / actual GMP 128 bits**.
4. Preflight compares both real/imag components with the archived d4-38 count-scale `close_enough` screen, logs native `recursive_calls`, `decisions`, `split_components`, positive cache hits and negative cache **misses**, plus BiPe before/after structural counters. Require identical native preprocessor dimensions **within** a warm-on/off pair. The precision screen is `COUNT_CONCORDANT_UNCERTIFIED` and is **not a rigorous GMP arithmetic interval/error certificate**.
5. Each call is capped at **45 seconds**; a timeout or native error is `CENSORED`, not a count mismatch, and not a speed measurement. A nonconcordant WMC or invalid source fails closed. The native workflow does **not** run CodSpeed. Deliberately do not combine this causal treatment with d4 cache-off, BiPe option-wide sweeps, or GPMC capacity changes.
6. Only after a complete numerically admitted pair **and observed material native-work change** may official CodSpeed be considered, preferably on a fixed Macro Runner using paired ABBA/BAAB and the same source/binaries within each run. Hosted WallTime alone is exploratory, not release approval. Record any same-binary repeat variability before ascribing native differences solely to warm-start.

## Interpretation policy

The warm-on arm includes SAT proof/sampling overhead and may benefit from a different learned-clause state. The off/on ratio of native decisions is **not** a runtime ratio. Within-d4 warm on/off cannot quantify which proportion of GPMC-vs-d4 performance comes from warm-start, since their SAT and caching implementations differ; do not change QuPRS default solver or routine CI based on these exploratory results.

**Science status is now confirmed** by Actions #41940731310 and detailed in the completed-source section below. Official CodSpeed timing remains a separate measurement and is not inferred from native counters.

Owners: [existing QOO-157](https://linear.app/qoogohome/issue/QOO-157), no duplicate issue; Ganak precision under QOO-98. GPMC remains QuPRS recommended solver.


## Completed source-pinned native result: 16/16 WMC PASS, 8/8 identical search vectors

[SCIENCE Actions #41940731310 SUCCESS](https://github.com/PhysicsQoo/QuPRS/actions/runs/41940731310), actual measured source commit `0efc7b33a8b2bed62aa8b7eac61402d00fa62002`, immutable artifact [`13376896940`](https://github.com/PhysicsQoo/QuPRS/actions/runs/41940731310/artifacts/13376896940). Source-paired scratch `src/methods/DpllStyleMethod.hpp` git diff exactly **one line**, no upstream/vendor algorithm modification.

- d4 original-pinned + common 38d/BiPe tracing **warm-on** binary SHA256: `97eac000a9d180ca5180ae72582fa33fdddf6793d1268c252058c120226ed0a7`.
- Identical except 1 source line **warm-off** binary SHA256: `9609fdcd8f4f27f07bb77de4727275f33f4e2ae33e75838979dc182e2930dbb2`.
- **All 16** source-original WMC numerical count-screen gates passed with **exact printed real/imag agreement across all eight pairs**, no timeouts or native errors, and **all eight warm-on/off native search counter vectors are exactly identical** (recursive calls, split components, decisions, positive cache hits, negative cache misses). BiPe `before/after` vectors also match within every pair.

| Original weighted CNF | BiPe | Decisions warm on = off | Recursive calls warm on = off | Cache positive hits on = off | Negative misses on = off |
| --- | --- | ---: | ---: | ---: | ---: |
| Grover4 EQ | auto | 3,105 | 6,211 | 7,516 | 3,105 |
| Grover4 EQ | none | 2,660 | 5,321 | 6,965 | 2,660 |
| QAOA7 genuine NEQ | auto | 926 | 1,853 | 2,138 | 926 |
| QAOA7 genuine NEQ | none | 971 | 1,943 | 2,205 | 971 |
| QPE-exact8 EQ | auto | 5,083 | 10,167 | 8,234 | 5,083 |
| QPE-exact8 EQ | none | 2,980 | 5,961 | 9,797 | 2,980 |
| QFT16 EQ | auto | 66,695 | 133,391 | 133,084 | 66,695 |
| QFT16 EQ | none | 426,163 | 852,327 | 917,484 | 426,163 |

**Mechanistic conclusion:** For these fixed original weighted QuPRS circuits, changing d4 warmStart has **no observable effect on counted component-search decisions, recursion, cache hits or miss counts**; thus a claim that prewarming improves subsequent component-search structure is **not supported** in this matrix. The prewarming SAT invocations themselves are outside these counters. Identical search work **does not imply identical end-to-end run time**; SAT initial check + 29 limited random SAT queries may have a pure overhead (or internal SAT effects not reflected in these counters).

**Official CodSpeed next step is justified by the missing SAT overhead, *not* a search-counter difference:** [official research commit `cd9e749`](https://github.com/PhysicsQoo/QuPRS/commit/cd9e7496f9dc63d8f0f02392d79086e3b73545a7), [Actions #41941617634](https://github.com/PhysicsQoo/QuPRS/actions/runs/41941617634), 10 benchmark IDs from five matched pairs (Grover4 auto, QAOA7 auto/none, QPE8 auto, QFT16 auto). **Fresh same-run 16/16 numeric science admission on the exact two recompiled binaries before timing**. CodSpeed v5 WallTime is the only authorized timing; hosted results will remain observational until fixed Macro Runner ABBA/BAAB. No QFT16 none timed arm, as it adds substantial CI cost without a new mechanism category.


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

**Evidence status at protocol creation:** native P6 run is in progress. Final exact result, censored variants, artifact and source SHA will be inserted after completed source-paired scientific admission.

Owners: [existing QOO-157](https://linear.app/qoogohome/issue/QOO-157), no duplicate issue; Ganak precision under QOO-98. GPMC remains QuPRS recommended solver.

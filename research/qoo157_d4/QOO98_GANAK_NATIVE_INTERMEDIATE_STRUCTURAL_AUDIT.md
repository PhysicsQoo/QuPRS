# QOO-98 — pinned Ganak Arjun→Puura native intermediate structural audit

**Scope**: science-only, **no benchmark timing**. Native pinned Ganak v2.8.0 binary, original source-CNF SHA from QuPRS artifact `13317939531`, native Ganak dialect exact signed complex literal weights, `--mode=6 --mpfrprec=127 --threads=1 --verb 1 --arjundebugcnf`. Official [source-locked CI #41861376500 SUCCESS](https://github.com/PhysicsQoo/QuPRS/actions/runs/41861376500), HEAD `6cba8679a461f1d32495461b4fea9d1666949ede`, [artifact `13338804783`](https://github.com/PhysicsQoo/QuPRS/actions/runs/41861376500/artifacts/13338804783). Initial [CI #41860803483 SUCCESS](https://github.com/PhysicsQoo/QuPRS/actions/runs/41860803483) precedes the stronger source-provenance capture. Five of five original-input native complex WMC printed-count screens passed at Ganak's nine-digit output resolution; this only guards the **original solver run when debug emission is enabled**, not an independent check of debug-CNF count preservation.

## Verified native debug snapshot structure (not yet a qualified WMC equivalent)

| Original case / knobs | debug CNF vars / clauses / literals | Native literal weight records | `c p show` | `c p optshow` | `c p exist` | `c MUST MULTIPLY BY` |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| QAOA7 NEQ Arjun=0/Puura=0 | 470 / 823 / 1817 | 638 | 470 | 470 | 0 | `1.00000000e+00 + 0.00000000e+00i` |
| QAOA7 NEQ Arjun=1/Puura=0 | **470 / 1130 / 2430** | 622 | 144 | 316 | **154** | `-4.57153712e-01 + -8.89387701e-01i` |
| QAOA7 NEQ Arjun=1/Puura=1 | **316 / 516 / 1204** | 622 | 144 | 316 | **0** | `-4.57153712e-01 + -8.89387701e-01i` |
| QFT16 EQ Arjun=0/Puura=0 | 486 / 1144 / 2600 | 800 | 486 | 486 | 0 | `1.00000000e+00 + 0.00000000e+00i` |
| QFT16 EQ Arjun=1/Puura=1 | **264 / 582 / 1358** | 528 | 70 | 264 | 0 | `-7.30491139e-01 + 6.82922174e-01i` |

All five debug files are **syntax-parsed `p cnf` + projection/weight/meta SHA only**. They are written after pinned Ganak's `cnf.remove_equiv_weights()` (main.cpp L794), so this snapshot is **not a direct output of each preprocessing stage**. Each debug file has an explicit optional/independent support partition and a `MUST MULTIPLY BY` complex global factor. Its weight values are printed with about nine significant digits. Consequently the debug CNF **must not** be passed to GPMC/d4 or re-counted and compared to the original *without* independently establishing the exact global factor, model/projection semantics, source variable mapping and output rounding envelope. `RESIDUAL_WMC_NOT_CERTIFIED` is the correct status.

## Stronger trace-based mechanism, beyond simple clause counts

The pinned native verbose output records:

- **QAOA7 Arjun-only, Puura disabled**: `WARNING. Not performing puura ... Number of sampling variables: 144 vs 10`, followed by a source-proven `470 vars / 1130 clauses` debug snapshot, `optshow=316`, **154 existential variables**. In the counter's two TD-component traces, respectively **`td nodes 176, nvars 261, edges 3833`** and **`td nodes 140, nvars 208, edges 2953`**. These are *native TD graph quantities*, not imported/independent primal-graph measurements.
- **QAOA7 Arjun+Puura enabled**: native `[puura-cnf] in 470 vars / 1130 clauses` → `[puura-cnf] out 316 vars / 516 clauses`, `[puura] Done` appears in stdout, confirming **the Puura stage was actually reached** (not merely requested). The debug snapshot has `optshow=316`, **0 existential variables**, and TD graphs **`176/176/288`** and **`140/140/228`** (nodes / nvars / edges). The corresponding TD edge counts are **13.31×** and **12.95×** smaller than Arjun-only, while projection support stays `144` shown variables.
- **QAOA7 Arjun disabled**: debug source remains `470/823`, and TD graphs are `261/261/373`, `208/208/296`. This is a third algorithm path (Arjun off skips Puura), **not** a fourth independent factorial arm.
- **QFT16 Arjun+Puura**: native `[puura-cnf] in 486 vars / 1349 clauses` → `out 264 vars / 582 clauses`, `[puura] Done` confirmed; debug projection `show=70, optshow=264, exist=0`; TD graph `264/264/582`. With Arjun disabled the source-like debug snapshot remains `486/1144`, native TD graph `485/485/1041`. The QFT16 Arjun-only/Puura-off case has **35 s scientific preflight timeout** in [#41857134111](https://github.com/PhysicsQoo/QuPRS/actions/runs/41857134111), so no native completed structure or formal CodSpeed value is inferred.

These observations give a **concrete structural mechanism candidate** for the science-gated [QAOA7 Arjun-only 62.2541× same-run CodSpeed slowdown](https://github.com/PhysicsQoo/QuPRS/actions/runs/41859346095): Arjun expands the serialized formula and retains many existential variables; without Puura the native TD graph is far denser. They do **not** prove the entire solver-inclusive runtime gap arises only from edge count, nor provide isolated native Puura stage CPU timing.

## Implications for GPMC / Ganak / d4 selection

Existing independent external **GPMC-style signed SCC** reductions from pinned QuPRS source CNFs produce **QAOA7 317 vars/517 clauses** and **QFT16 384/940**; Ganak's **own** full Arjun/Puura debug snapshots are **QAOA7 316/516** and **QFT16 264/582**, respectively. This *structural* contrast supports investigating why Ganak wins conditional same-requested-bits QFT16 whereas GPMC wins QAOA7. **Never interpret these snapshots as numerically interchangeable exact WMC residuals**; different projection, multiplier, and rounding contracts must be separately certified before same-residual cross-solver CodSpeed. Counting residual sizes alone cannot prove a causal speed ranking.

The native release's dependency source identity is not fully reconstructible from the Ganak main SHA alone because pinned Ganak CMake may `FetchContent` Arjun `master`; the **official release archive and binary SHA** are fixed, but transitive build-source provenance remains unqualified.

**Next science gate (do not re-run expensive benchmark until passed):** using official pinned Ganak native solver as an independent re-reader of each archived debug CNF, check whether the resulting nine-digit WMC multiplied by `MUST MULTIPLY BY` (accounting for **both** printed complex factor and count rounding) agrees with the archived original count. Validate `c p show / optshow / exist`, all positive/negative literal weights and any redundant clauses; only then design a carefully bounded external GPMC/d4 residual test. This is a *printed-count consistency screen*, never a certified 38-digit WMC proof. If insufficient provenance, retain `RESIDUAL_WMC_NOT_CERTIFIED`. Macro Runner ABBA/BAAB remains a separate performance admission.

[Obsidian research note](https://github.com/PhysicsQoo/obsidian/blob/main/程式開發/QuPRS/QuPRS_WMC_Solver_GPMC_Ganak_d4_比較研究_20261104.md) • [Linear QOO-98](https://linear.app/qoogohome/issue/QOO-98) • [QOO-157](https://linear.app/qoogohome/issue/QOO-157). No upstream solver, `dev`/`main`, or normal CodSpeed sharding change.

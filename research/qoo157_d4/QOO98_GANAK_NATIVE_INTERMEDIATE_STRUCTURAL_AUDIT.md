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

**Revised science gate after native debug-CNF reread:** the official Ganak counter **already applies** the parsed `c MUST MULTIPLY BY` factor through `cnf.get_multiplier_weight()`; **do not multiply it a second time**. The native 2-case unit/deleted/negated-factor controls prove this at the nine-digit print resolution (full evidence below). The no-Arjun roundoff audit also confirms 319/638 QAOA7 and 400/800 QFT16 signed complex weight records changed by diagnostic serialization alone. Therefore the debug CNF is a *native print-consistent but low-precision* serialization, not a certified exact weighted residual. Validate projection semantics, cumulative input-weight error and higher-precision source fidelity **before** any GPMC/d4 equal-residual comparison. `RESIDUAL_WMC_NOT_CERTIFIED` and `NOT_COMPARABLE_FOR_38D_OUTPUT` remain. No new performance measurement is admitted.

[Obsidian research note](https://github.com/PhysicsQoo/obsidian/blob/main/程式開發/QuPRS/QuPRS_WMC_Solver_GPMC_Ganak_d4_比較研究_20261104.md) • [Linear QOO-98](https://linear.app/qoogohome/issue/QOO-98) • [QOO-157](https://linear.app/qoogohome/issue/QOO-157). No upstream solver, `dev`/`main`, or normal CodSpeed sharding change.


## P3 — Native debug-CNF reread, factor negative controls and loss-of-precision audit

The first fixed-source [native debug replay #41925430019](https://github.com/PhysicsQoo/QuPRS/actions/runs/41925430019) (HEAD `7a2b0656f7376c705fde0aec69dd411241684445`, artifact `13367969884`) read **all 5 source-pinned diagnostic CNFs** with unchanged Ganak 2.8.0 Mode6 `--mpfrprec=127 --arjun=0 --puura=0`. All five parsed and returned native complex counts. Critically, each raw native replay **already closely resembled original native WMC**. A preliminary *hypothetical double multiplication* produced large discrepancies for 3/5 cases; that hypothesis was **wrong**. The previous result is retained as a documented negative finding, **not** evidence that Arjun/Puura changes original WMC. Pinned upstream [Ganak `main.cpp::run_weighted_counter()` L590–592](https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L590-L592) initializes `cnt` with `cnf.get_multiplier_weight()->dup()` **before** multiplying by `counter.count()`.

### P3.1 Native intervention on ONLY the multiplier line

[Six native negative-control runs #41926184444 SUCCESS](https://github.com/PhysicsQoo/QuPRS/actions/runs/41926184444), HEAD `53b91331c009a0f733a6cbd0d1762500fdaaf629`, [artifact #13368517944](https://github.com/PhysicsQoo/QuPRS/actions/runs/41926184444/artifacts/13368517944). For each archived default-on QAOA7/QFT16 debug CNF, only the `c MUST MULTIPLY BY` line was *deleted*, *replaced by exactly `1+0i`*, or *sign-inverted*. Original source binary, CNF clauses, literal weights and all `show/optshow/exist` projection lines retained byte-for-byte. All six controls returned native valid printed complex counts; this is **untimed SCIENCE**, not CodSpeed.

| Native pinned diagnostic source | Original factor | Native with factor removed | Native with explicit 1+0i | Native with factor sign-inverted |
| --- | --- | --- | --- | --- |
| QAOA7 NEQ Arjun+Puura | `-0.457153712-0.889387701i` | `3.82965830e22 - 7.45055965e22i` | **identical to removed** | **exact sign reversal of intact native print** |
| QFT16 EQ Arjun+Puura | `-0.730491139+0.682922174i` | `-1.53780403e15 + 1.64491981e15i` | **identical to removed** | **exact sign reversal of intact native print** |

The native complex count with explicit unit factor times the *printed source factor* agrees with the intact native print to normalized complex relative differences **7.132×10⁻¹⁰ QAOA7** and **2.210×10⁻⁹ QFT16**. Setting the factor to its negative flips the printed output exactly. Thus `NATIVE_AUTOMATIC_MULTIPLIER_APPLIED_PRINT_SCREEN` is supported on **2/2** source cases. **Do NOT manually multiply Ganak's already-multiplied output**. This is an isolated multiplier parser/control result, **not a certificate for exact projection or preprocessed weighted CNF interchangeability**.

### P3.2 Full source-vs-debug no-Arjun literal-weight rounding (without rerunning solver)

[Source-locked Decimal/Boolean audit #41926726197 SUCCESS](https://github.com/PhysicsQoo/QuPRS/actions/runs/41926726197), HEAD `a8294edb1231e2fed8ff0539a64d81c44b992c7c`, [artifact #13369167690](https://github.com/PhysicsQoo/QuPRS/actions/runs/41926726197/artifacts/13369167690). It reads immutable original source CNF artifact `13317939531` and pinned native debug artifact `13338804783`; no executable solver calls and no timing. Canonical clause *multisets* are exactly equal when `--arjun=0`, after ignoring line/literal order. Signed literal indices are identical in each pair, but source real/imag weights are **not** all retained exactly:

| Source → no-Arjun debug | Identical canonical Boolean clauses | Source/debug signed weights | Exactly retained signed weight pairs | **Rounded signed weight pairs** | Largest absolute complex pair change |
| --- | --- | ---: | ---: | ---: | ---: |
| QAOA7 genuine NEQ | 823/823 | 638 | 319 | **319** | **5.60331×10⁻¹⁰** |
| QFT16 EQ | 1144/1144 | 800 | 400 | **400** | **6.10026×10⁻¹⁰** |

All the rounded rows correspond to the nontrivial signed complex weights; exactly preserved rows were mainly unit negative-literal weights. Rounding the input weights makes even a formally correct count of the debug CNF a **different finite-precision WMC problem**, particularly for **high cancellation**. The simple sum of absolute per-literal changes is about `2.57e-8` (QAOA7) and `7.28e-8` (QFT16); **these are not bounds on WMC error** because model sums and cancellations amplify rounding.

For reference, in #41925430019 the native re-read counts (factor already auto-applied) differed from original native output in **complex-magnitude-normalized** terms by about `2.893e-9` for QAOA7 (all three cases), `3.639e-10` for QFT16 no-Arjun, and `4.456e-9` for QFT16 Arjun+Puura. However QAOA7's **small imaginary component** changes from roughly `1.14e9` (original) to `1.37e14` (debug native read), and QFT16's **small real component** changes from roughly `-34.33` to `+819281` (Arjun+Puura debug native read). Thus small *full-complex relative error* **does not certify the weak component near cancellation**. Neither 38-digit fidelity nor a rigorous internal MPFR error envelope is established.

### P3 decision and next cost-limited work

- **Resolved:** Factor metadata is automatically consumed by Ganak native parser/count path, so no manual second multiplication; original/dialect provenance is preserved. `AUTOMATIC_MULTIPLIER_PRINT_SCREEN_PASS_2_OF_2`.
- **Resolved:** Source-vs-no-Arjun debug Boolean clauses and signed literal IDs match exactly; nine-digit serialization **rounds 319/400 high-precision positive-weight pairs**. `SOURCE_DEBUG_ROUNDING_AUDIT_PASS_2_OF_2`.
- **Not resolved:** Verify complex-weighted WMC *projection/weight semantics and rigorous output error bounds*, especially the weak imaginary/real components under catastrophic cancellation. The source-only roundoff floor makes the debug CNF unsuitable for an equal-38d comparison by itself. Keep `RESIDUAL_WMC_NOT_CERTIFIED` and `NOT_COMPARABLE_FOR_38D_OUTPUT`.
- **Next priority:** use a minimal exact-Fraction complex-WMC toy case with nonunit phase and projected/existential variables to independently establish parser count semantics; then seek lossless high-precision residual serialization via a *wrapper/experimental exporter* without changing upstream solver. **No routine CI or additional CodSpeed until that scientific gate passes.**

The three scoped proof scripts and their individual SCIENCE workflows remain in the research branch: `qoo98_ganak_debug_replay.py` (hypothetical double-multiply negative evidence), `qoo98_ganak_multiplier_control.py` (actual parser factor controls), and `qoo98_ganak_debug_rounding_audit.py` (source-exact Decimal comparison). Source-specific results are archived in artifact IDs above. QuPRS `dev/main`, default solver, and official benchmark shards remain unchanged.

# QOO-157 P8 — Same-residual BiPe option cost attribution (2026-11-05)

## Motivation — not a repeat of existing six-option ablation

Earlier pinned [BiPe six-option official CodSpeed #41839512753](https://github.com/PhysicsQoo/QuPRS/actions/runs/41839512753) measured full prepared-CNF subprocesses. The existing [canonical residual audit #41841100007](https://github.com/PhysicsQoo/QuPRS/actions/runs/41841100007), native [BiPe v1.0.0 workload statistics #41847739344](https://github.com/PhysicsQoo/QuPRS/actions/runs/41847739344), and independent [P7 12/12 full-weight/projection/protected requalification #41942959399](https://github.com/PhysicsQoo/QuPRS/actions/runs/41942959399) all establish that QAOA7 original **auto_default**, **manual_sharp**, and **auto_no_vivif** result in **byte-identical full residual formula dumps**. Yet prior hosted CodSpeed saw 92.776, 64.500, 82.070 ms respectively. The critical remaining question is whether their cost differences occur **before** DPLL, rather than because of a changed residual formula.

The P8 intervention adds a **scratch-only** `QOO157_PREPROC_ONLY=1` early-return *after the existing `runPreproc(formula, optionPreproc)` and associated quantification update, before `counter(...)`*. It is not exposed as a production d4 option. The full and preproc-only paths use **the exact same compiled binary, original QAOA7 weighted CNF and BiPe options**.

## Source and scientific admission

- Pin upstream d4 `be15f91f3e9769e1f5cb175fa27e3eca3a1ea690` and output-precision GMP **38 effective decimal digits / actual 128 bits**, using existing research-only `matched_precision_variant.py` and `d4_bipe_instrument.py` in a disposable clone. Apply established P7 env-gated residual dump and P8 early-return gate; archive the **exact scratch patch**, binary SHA256 and native build record. No upstream/vendor/dev/main code change.
- Download original QAOA7 NEQ weighted-CNF/source-oracle artifact from immutable run [#41822549728](https://github.com/PhysicsQoo/QuPRS/actions/runs/41822549728) and the P7 source-pinned 12/12 artifact [#41942959399](https://github.com/PhysicsQoo/QuPRS/actions/runs/41942959399). Validate original CNF byte SHA against **both**.
- Before any CodSpeed, on that **same P8 binary**, run full native WMC and preproc-only native for *three* QAOA7 options, capturing `QOO157_RESIDUAL_DUMP`. All **six** residual-dump **byte SHA** must exactly equal the previously admitted P7 dump for the option; all 3 full native complex WMC counts must pass the archived exact-rational `COUNT_CONCORDANT_UNCERTIFIED` screen. Preproc-only is admitted only if it emits its explicit completion marker and **no** WMC (proof that DPLL was not accidentally invoked).
- Preflight is not a performance measurement; only **official CodSpeed v5 WallTime** may rank the cost. Record any source mismatch, timeout, native error or WMC mismatch as hard science failure/censored, never a speedup.

## Official paired 6-identity pilot

[Implementation commit `eeef211`](https://github.com/PhysicsQoo/QuPRS/commit/eeef211fc5e31033f041ae24a4369953bf7b968d), [research-only Actions #41944225225](https://github.com/PhysicsQoo/QuPRS/actions/runs/41944225225). Matrix: QAOA7 genuine NEQ × options `auto_default`, `manual_sharp`, `auto_no_vivif` × scopes `preproc_only` and `full`, **six CodSpeed v5 WallTime benchmark identities**, at most five actual rounds each, after all six science preflights. All same source and compiled binary.

**Critical interpretation policy:**

- `preproc_only` includes **native startup, CLI option parsing, weighted-CNF parsing, BiPe, diagnostic stdout and subprocess wrapper**. It is not a pure BiPe CPU/memory-stage counter.
- `full` additionally includes DPLL counting, arithmetic, final output and subprocess wrapper. Its distinction from `preproc_only` is *controlled program path*, not subtraction of two unpaired walltime medians into a rigorous isolated DPLL time.
- If both `manual_sharp` and `auto_no_vivif` show lower preproc-only CodSpeed cost while full is lower, this is evidence favoring a preprocessing-path contribution to the prior same-residual differential. If preproc-only does not differ or varies across rounds, the full difference may be internal downstream state or hosted runner noise; reject a single-stage causal claim.
- Any GitHub-hosted non-Macro Runner WallTime remains **OBSERVATION_ONLY**, not a production performance acceptance gate; do not compare absolute time with prior runs. A formal shipping choice requires fixed Macro Runner paired ABBA/BAAB, RSS and timeouts.
- Excludes QASM, Path-sum RR, CNF generation and end-to-end QuPRS Hybrid. No solver-default change, no new routine CI benchmark shard, no CodSpeed in other reports, Ganak science under QOO-98.

## Current evidence

The workflow completed SUCCESS with a full native science admission and official CodSpeed. The original evidence and methodological limitations are preserved in the following section.

Track under existing [QOO-157](https://linear.app/qoogohome/issue/QOO-157), rather than creating another issue.



## Completed P8 native science + six official CodSpeed v5 observations

**PASS:** [GitHub Actions #41944225225](https://github.com/PhysicsQoo/QuPRS/actions/runs/41944225225), measured HEAD `eeef211fc5e31033f041ae24a4369953bf7b968d`; [immutable artifact #13377553454](https://github.com/PhysicsQoo/QuPRS/actions/runs/41944225225/artifacts/13377553454), first-party [CodSpeed run `6aebd3b8ac5c0ebdb12478ef`](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aebd3b8ac5c0ebdb12478ef). The native scratch binary SHA256 was `0b9a892714f84c08c9fa77c4f8b2bc0e06352d29098bafca83881fdecc8020ae`, source weighted-CNF SHA256 `66375ceba75cd7b02e8f4a723c534618d5206dc2ebfaf02255d4c863f79a3123`, actual GMP 128 bits/38 effective digits. All 3 options × 2 scopes (**6/6**) passed fresh native science: every raw residual dump SHA256 exactly **`99d9100538b20ceab66dad1d0f6d06025de5d315720198da90656dff865067bf`** (the previously admitted P7 original data); all three full native complex counts concordant to the exact archived rational source-count screen; the three preproc-only runs returned the explicit marker without executing the counter. No timeout, source drift or scientific mismatch. WMC is **COUNT_CONCORDANT_UNCERTIFIED**, not an MPFR/GMP numerical error certificate.

Six **official CodSpeed v5 WallTime benchmarks completed** with **five actual rounds per identity**; first-party export reports **zero IQR and zero stdev outlier rounds**. The values below are original export **five-round medians**, not the CodSpeed UI minimum. This is same-run/same-binary prepared-original-CNF context:

| BiPe option, QAOA7 genuine NEQ | Preproc-only median | Full native subprocess median | Preproc-only vs default | Full vs default |
| --- | ---: | ---: | ---: | ---: |
| `auto_default` | **71.425351 ms** | **144.944134 ms** | — | — |
| `manual_sharp` | **26.448164 ms** | **91.608299 ms** | **−62.97%** | **−36.80%** |
| `auto_no_vivif` | **56.397074 ms** | **121.518124 ms** | **−21.04%** | **−16.16%** |

Preproc-only default vs manual difference is **44.977 ms** in the exported medians, while their full-subprocess median difference is **53.336 ms**. The differences are **not mathematically a paired decomposition of the same run into native stages**: each option/scope owns a separate distribution with subprocess startup, parser and wrapper effects. The agreement in direction and order of magnitude, however, supplies evidence that **option-dependent preprocessing/initialization work before DPLL is a major contributor** to QAOA7's previous within-d4 full WallTime gap despite byte-identical residual clauses, weight map, projection and protected set. No single rule is proven to account for that share: `manual_sharp` changes an option **bundle**, not only vivification, and source stage counts cannot identify unobserved SAT work. The full counter's internal heuristic state might also depend on preprocessing even when residual bytes are the same.

**Reliability:** The CodSpeed [run page](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aebd3b8ac5c0ebdb12478ef) explicitly flags **all six non-Macro Runner WallTime benchmarks as potentially unreliable**, with no resolved native flamegraph. Five rounds and zero outliers **do not certify statistical significance**, especially cross option comparisons; this is a **single hosted same-run observational pilot**, NOT fixed Macro Runner paired ABBA/BAAB. Do not splice these absolute medians into prior CodSpeed runs with different hosted runners or proclaim an end-to-end QuPRS performance gain. No experiment modified QuPRS production BiPe settings (there are none), default GPMC, d4 vendored source, dev/main or routine CI.

**Decision:** The crucial gap is narrowed: QAOA7’s preprocessor-only path itself can consume substantial time while yielding the same post-BiPe weighted formula; choosing a shallower/manual preproc option may reduce this work in that QAOA-shaped family. But the earlier [source-pinned BiPe native structural statistics #41847739344](https://github.com/PhysicsQoo/QuPRS/actions/runs/41847739344) found QFT16’s degeneracy-width proxy improving 11→8, while QAOA7 stayed 2→2, so a **global default “disable auto BiPe”** would be unjustified and may drastically hurt QFT-like circuits. Future P9 should first test a **narrow, original-source family-aware criterion** and fixed runner paired official CodSpeed if a concrete d4 integration policy decision needs it; otherwise retain completed P8 and leave d4 research-only.

Owner: [existing QOO-157](https://linear.app/qoogohome/issue/QOO-157). The parent issue remains In Progress for the larger d4 vs GPMC solver choice, not a v0.14.0 release blocker.

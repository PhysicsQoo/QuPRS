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

The workflow has been triggered. Fill in the actual same-run science/CodSpeed verdict, immutable artifact ID and official instrument medians only once the run is completed and verified. If the run fails, preserve the failure reason; do not promote any result or claim a speedup.

Track under existing [QOO-157](https://linear.app/qoogohome/issue/QOO-157), rather than creating another issue.

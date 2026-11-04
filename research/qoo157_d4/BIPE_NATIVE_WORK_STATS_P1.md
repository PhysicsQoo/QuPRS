# QOO-157 P1 — source-pinned BiPe v1.0.0 native work counters

This is the **next stage after source-quotient P0 science and CodSpeed**.
The P0 common weighted-quotient intervention showed d4 benefited 6–14%
across four input CNFs but remained slower than GPMC. To explain d4's
residual overhead, use the original source-pinned **BiPe v1.0.0** library:
`jm62300/bipe@219cc2a5f15a563e1965e5a5137f0fbadf0d166f`
built inside the pinned `jm62300/d4@be15f91...` counter.

BiPe's [PreprocManager.cpp](https://github.com/jm62300/bipe/blob/v1.0.0/src/preproc/PreprocManager.cpp)
already emits `c [STATS]` when `--preproc.verbosity=3`:
pre/post vars/clauses/literals/projection/estimated treewidth, gate
(AND/XOR/EQUIV) counts, BVE gate/resolution elimination counts,
bipartition input size, and BVA changes. It also emits a native
`t_total` value; **we drop it** because verbosity>=3 adds extra
treewidth-estimation work and **only official CodSpeed ranks performance**.
This observation should NOT be run as a CodSpeed task.

Science test: same original QAOA7 NEQ/QFT16 EQ source SHA, same six
BiPe configurations from the previous [d4 option CodSpeed](D4_BIPE_OPTION_ABLATION.md),
fixed original d4 source, fixed pinned BiPe commit, research-only GMP
38-effective-decimal variant, 12/12 printed count screen. Snapshot the
native counters in JSON. Experimental branch only; no d4/BiPe source
instrumentation, no QuPRS dev/main change.

After the native scientific counters, inspect whether `manual_sharp`,
`auto_no_vivif`, `auto_no_probing` (same exact post-BiPe residual
fingerprints in the earlier audit) had different stage work/hits; if
counters cannot disambiguate, keep stage-level attribution UNKNOWN
rather than converting internal `t_total` into a performance claim.
Formal time comparison still needs fixed Macro Runner paired
ABBA/BAAB CodSpeed for within-d4 variants.


## Verified BiPe v1.0.0 native work evidence

**PASS**: [Actions #41847739344](https://github.com/PhysicsQoo/QuPRS/actions/runs/41847739344) at commit `778ea52a85afea9106e7477e1b3e517fef093557`, [raw JSON evidence artifact #13331518772](https://github.com/PhysicsQoo/QuPRS/actions/runs/41847739344/artifacts/13331518772). The workflow verifies upstream d4 `be15f91…`, actual fetched BiPe v1.0.0 `219cc2a5f15a563e1965e5a5137f0fbadf0d166f`, 128 GMP bits (38 effective decimal digits), original source CNF SHA and **12/12 count concordance**. `-preproc.verbosity=3` adds a degeneracy estimate: this job is **science/structure only; no timing comparison**. The native emitted `t_total` field was intentionally excluded from the stored parsed statistics.

| Configuration | QAOA7 vars / clauses / literals | QAOA7 input size / gate-elim / approx TW | QFT16 vars / clauses / literals | QFT16 input size / gate-elim / approx TW |
| --- | --- | --- | --- | --- |
| `auto_default` | 470→470 / 823→677 / 1817→1379 | 324 / 147g, 0r / **2→2** | 486→486 / 1144→1058 / 2600→2342 | 400 / 87g, 0r / **11→8** |
| `manual_sharp` | same | same | same | same |
| `auto_no_vivif` | same | same | same | same |
| `auto_no_probing` | same | same | same | same |
| `auto_no_equiv_subst` | same *counts*, **different residual CNF SHA** | 324 /147g, 0r /2→2, **146 EQUIV gates** | same *counts*, **different residual CNF SHA** |400 /87g,0r /11→8, **86 EQUIV gates** |
| `none` | 470→470 /823→823 /1817→1817 | not applicable /2→2 |486→486 /1144→1144 /2600→2600 | not applicable /11→11 |

All enabled modes had **0 AND/OR and XOR detected gates**, **zero BVA variables and clauses removed**, and **zero resolution elimination**. Most `sharp-equiv` settings show 0 detected EQUIV gates because source equivalences were substituted *before* the gate statistics were gathered. With `equiv-subst=false`, the equivalence structures remain as EQUIV gates (146 QAOA7, 86 QFT16); earlier residual SHA audit independently shows the actual residual content differs. **Do not treat native gate count zero as proof that no equivalence relations existed**.

**Mechanism interpretation:** the pinned BiPe degeneracy-based *treewidth proxy* remains **2→2** for QAOA7 while **11→8** for QFT16, matching why d4 BiPe net CodSpeed cost may not pay on already trivial-width QAOA7 but does pay for QFT16 (where disabling BiPe was very expensive). The proxy is **not a certified exact treewidth or per-stage CPU trace**; identical native size/gate statistics under four residual-identical settings cannot distinguish their differing hosted CodSpeed WallTime. Need an independently science-gated stage hit/work trace if pursuing that narrower timing explanation. Never turn the native `t_total` into formal performance data.

**Next scope:** GPMC native cache/lookups/components and TD width (P1 after this), then conditional Ganak2.8.0 mode6 precision qualification (QOO-98). Do not change d4/GPMC default.

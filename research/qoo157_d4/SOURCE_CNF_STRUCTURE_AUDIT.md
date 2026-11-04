# QOO-157 — actual QuPRS CNF structure and weighted-variable protection audit

**Date:** 2026-11-04  
**Classification:** measured **input-structure** evidence; **NOT** runtime solver preprocessing or causal performance attribution.  
**Original scientific source:** QuPRS HEAD `efab7ccd132214758d4209d0b5c4f6488f30695e`; [CI #41822549728](https://github.com/PhysicsQoo/QuPRS/actions/runs/41822549728), artifact `13317939531`.  
**Reproducible follow-up:** [lightweight structure CI #41833033897](https://github.com/PhysicsQoo/QuPRS/actions/runs/41833033897) **SUCCESS** at audit HEAD `28e86b8e05df7f7b8b5cec0ec7d7f7b47a4b2f81`; artifact `13323366723`, SHA-verified four original `.cnf` files. No native solver build or CodSpeed rerun was needed.  
**Script:** [cnf_structure_audit.py](cnf_structure_audit.py) and [test_cnf_structure_audit.py](test_cnf_structure_audit.py).

## Direct observations

| Actual original source CNF | Variables | Clauses | Weighted variables | d4 source-string-protected variables | Numerically asymmetric variables | Binary clauses | Original primal components |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Grover4 EQ | 372 | 698 | 256 | 256 (68.82% of all) | 256 | 536 (76.79%) | 371 + 1 |
| QAOA7 genuine NEQ | 470 | 823 | 319 | 319 (67.87%) | 319 | 650 (78.98%) | 261 + 208 + 1 |
| QPEexact8 EQ | 250 | 495 | 178 | 178 (71.20%) | **175** | 370 (74.75%) | 249 + 1 |
| QFT16 EQ | 486 | 1144 | 400 | 400 (82.30%) | 400 | 830 (72.55%) | 485 + 1 |

All weighted variables have both positive and negative literal weights in the source. Across these four source CNFs, **no clause has more than one weighted variable**, and there are **zero weighted–weighted binary clauses**. Weighted–unweighted binary clauses are 528, 636, 354 and 798 respectively; the remaining binary clauses are unweighted–unweighted. These are input grammar/structure facts, NOT counts of components seen after GPMC or BiPe preprocessing.

QPEexact8 has a particularly useful three-variable *representation* boundary: variables **38, 134, 176** have positive weight `1.0000000000000000e0 0.0000000000000000e0` and negative weight `1.0 0.0`. They are **numerically identical** complex weights but different strings. In pinned d4 [`Main.cpp::runPreproc`](https://github.com/jm62300/d4/blob/be15f91f3e9769e1f5cb175fa27e3eca3a1ea690/c%2B%2B/counter/src/Main.cpp), `varProtected` compares serialized positive/negative strings, so **178/178 source weighted variables are protected, while only 175/178 are numerically asymmetric**. This does **not** establish the actual number of variables preserved by BiPe, its effectiveness, or a measurable d4 overhead.

The pinned GPMC [`Preprocessor.cc`](https://github.com/PhysicsQoo/GPMC/blob/a1bda3489e959d3695b6798d327c5a1fc1bed305/preprocessor/Preprocessor.cc) separately guards weighted-definitional elimination when positive/negative weights differ, but its equivalent-literal merge logic also updates literal weights by multiplication. Thus **GPMC is not universally free to eliminate every weighted variable**, nor can d4's source-string guard alone explain the CodSpeed differences.

## Extra raw graph diagnostic (not runtime TD evidence)

The unpreprocessed *simple primal graphs* constructed from co-occurring variables in each clause have edge counts Grover4=600, QAOA7=669, QPEexact8=426 and QFT16=1041. Corresponding edges/variables are 1.613, 1.423, 1.704 and 2.142. On these *raw source graphs only*, each passes GPMC's default density/edge-ratio prefilters (`edges/n^2 <= 0.10`, `edges/n <= 30`). **But GPMC calls TD on the preprocessed instance and subsequently tests decomposition-width limits**, so this cannot certify that FlowCutter ran, was accepted, or reduced runtime. The scoped TD pilot must record the actual native markers.

## Specific discriminating hypotheses and experiment scope

1. **H-preprocess:** weighted source variables occupy 68–82% of variables, with asymmetric source weights for almost all of them. A preprocessing strategy that preserves WMC yet merges equivalent literals may have a large effect. Measure before/after variable and clause counts, actual protected/eliminated variables, and count-preserving transformations on the *same* original SHA; **do not infer causality from guarded-variable counts**.
2. **H-TD:** source graphs are sparse, but the useful TD decision depends on the post-preprocessing instance and actual TD width. Compare pinned GPMC `-td` versus `-no-td` at `-vs=1` and **38-digit MPFR**, using identical source CNF and a numerical admission gate before CodSpeed. Start with **QAOA7 NEQ** (two large original components) and **QFT16 EQ** (one large component); treat missing `FlowCutter` markers as an explicit negative finding rather than a fake speedup.
3. **H-branch/cache:** only after TD is actually shown to run, expand to `-vs=0/1`, cache hits, decisions, backjumps and `-pp_ee/-no-pp_ee` one-factor ablations, each source/pair audited with science and CodSpeed. Do not modify GPMC or Ganak source or dev/main.
4. **Cost and decision:** No performance claim is valid from the structural CI. Use **CodSpeed** only for performance, and treat GitHub-hosted WallTime as `OBSERVATION_ONLY` until a qualified Macro Runner/paired ABBA design is available. The d4 default recommendation stays **NO-GO**.

The permanent source note intentionally does not reprint the original scientific floating count as a certified result. The original 8/8 fair-precision `COUNT_CONCORDANT_UNCERTIFIED` remains a **numerical concordance screen**, not a WMC arithmetic error certificate.

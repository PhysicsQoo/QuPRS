# RaWMoCS A0b / A1 — Pre-implementation research and mathematical safeguards

**Date:** 2026-11-05. **Linear:** QOO-173. **Scope:** Research-only in QuPRS experiment branch. No RaWMoCS repository or Rust implementation.

## 1. Counting modes must be typed: projected weight semantics differ

Full complex WMC, including all declared variables, is:

\[
\mathrm{FullWMC}(F,w)=\sum_{a\models F}\prod_{v\in V}w(v^{a_v}).
\]

Our optional **ExistentialDistinctProjectedWmc** semantics is deliberately *different*:

\[
\mathrm{EPWMC}_P(F,w_P)=\sum_{p\in\{0,1\}^P}[\exists e:F(p,e)]\prod_{v\in P}w_P(v^{p_v}).
\]

Only P may carry nonunit literal weights; all unprojected variables are existential witnesses, never counted separately. The Ganak2 CAV 2025 paper Section 2 instead explicitly states a **projected solution weight is the sum of full-assignment weights in that projection-equivalence class**. If these class weights are summed across projections, the value equals full WMC by a partition of the satisfying models, not the above distinct-projection count. **Do not call both modes simply PWMC without versioned formal input specification.** Paper wording does not establish the exact CLI mode of Ganak 2.8.0; independent black-box input/output tests are required before any purported cross-tool parity.

Example F=(x OR y), P={x}, w(x)=2, w(not x)=3, w(y)=w(not y)=1: EPWMC=5; full WMC or sum of extension-class weights=7. Empty projection P={} with satisfiable F has EPWMC=1, whereas FullWMC may be 0 by complex cancellation or larger than 1.

**Proposed separate request variants**: FullWmc (QuPRS), ExistentialDistinctProjectedWmc(P) (research optional), AggregatedProjectedClassWeights (research only; no implied implementation promise). Arithmetic flags: ExactGaussianRationalOracle, MultiprecisionComplexPoint (uncertified), CertifiedComplexInterval (only after a valid outward rounding/error bound). Never silently cast modes.

## 2. A1 full-WMC mathematical requirements and code-independent proof sketch

For declared counted support U, even variables absent from clauses have factors w(x)+w(not x). If F has an empty clause, the count is zero (logical contradiction). If F has no clauses, the count is a product of the factors for **all remaining declared U**, not automatically 1.

For branch x, sum weighted Shannon cofactors w(x) C(F|x,U\x) + w(not x) C(F|not x,U\x). Literal weights for unit propagation or forced assignments must be accounted **once**; component decomposition multiplies only disjoint counted supports and any extracted free-variable factors.

- QuPRS's existing GPMC and Ganak adapters produce **positive complex literal weight, negative literal = 1+0i**. This is a strict **integration profile**, not a general FullWmc restriction; the original 24 general fixtures test arbitrary positive/negative weights.
- QuPRS-profile fixtures demonstrate errors still occur with negative=1: pure-literal SAT rewriting changes WMC 11 to an incorrect 8; dropping one equivalent variable without multiplying its literal factors changes WMC 11 to 6; forced literal and propagation factors may yield WMC 6; a tautologically mentioned, otherwise free variable contributes 1+i when w(+x)=i.
- SAT=true does NOT imply FullWmc=1, even with all unit weights and an unconstrained variable (FullWmc=2). SAT and weighted cancellation may coexist with WMC=0. Only explicit projected existential suffix, or formal unique weighted extension/certified factor, permits SAT short-circuit.
- Exact zero of a complex weight is legal; numerical interval containing zero is not an exact zero proof. Avoid conflating SAT/UNSAT statuses, numerical verdict and resource failure.

**Cache semantic key** must include canonical residual clauses, counted remaining support (including free vars if cached), extracted weight-factor ownership, weight version/digest or a safe symbolic form, counting mode and projection, arithmetic precision/certificate policy and any protected variables. Hash may index candidates but deterministic exact mode must check full canonical equality. Instrument all eligible requests/hits/misses/evictions/resident bytes/peak bytes (hits + misses = eligible). Never carry scalar cache between different weight versions. Component graph nodes that have no remaining clauses still carry free-variable factors.

### Chronological backtracking requires a zero-weight-safe design

The Ganak2 paper CAV 2025 Section 4.3/Algorithm 3 compensates contributions by **dividing by a literal weight**, while explaining that learned clauses may propagate into a different component. Such division is undefined for zero literal weight; for near-zero complex values, it can magnify floating numerical error; a general semiring need not support inverse operations. Thus the Ganak2 ChronoBT algorithm is not directly portable to general complex or generic AMC.

**A1 decision:** defer ChronoBT. Use a self-designed reversible contribution/trail ownership mechanism that supports undo WITHOUT division, or simply chronological DPLL baseline. A future optimized ChronoBT must prove weighted cancellation, zero weights, learned-clause cross-component propagation, rollback, and inexact arithmetic provenance using independent property tests. Do not import its internal node/mark layout or magic constants.

### Branching and preprocessing policies

GPMC/SharpSAT-TD's decomposition and cache are the base. d4 dynamic hypergraph partitioning and static TD have incomparable theoretical strengths (SAT 2024); only official same-SHA CodSpeed on held-out QuPRS CNFs can establish a useful policy. Do not use a one-QAOA7-vs-one-QFT16 family switch. SAT safe pure-literal, BCE, BVE or equivalence rewrites must include weighted and projection-preservation witnesses. Zero-weight handling and old learned clauses invalidate naïve count/caching assumptions.

## 3. Finished A0b first-party fixture and research artifacts

- [24 original general Gaussian-rational full/projected fixtures](complex_count_fixtures.json)
- [24 original QuPRS weight-profile fixtures](quprs_literal_profile_fixtures.json)
- [Independent exact rational Python Oracle](exact_complex_oracle.py): now accepts both suites and enforces QuPRS negative-literal unity. Each suite has 24 exact count/SAT/projection expectations, metamorphic checks and projection-first existential checks.
- [Scoped GitHub research CI YAML](https://github.com/PhysicsQoo/QuPRS/blob/experiment/qoo157-d4-effective-digit-parity/.github/workflows/qoo157-rawmocs-a0-reference.yml): two separate output JSON reports and immutable HEAD provenance; runs without solver or performance timing, only on experiment branch/path triggers.

**Independent in-session arithmetic result:** generic suite 24/24, QuPRS profile suite 24/24, both compared with a separately written exact Gaussian-rational enumerator / Shannon recursion. This is NOT a GitHub CI pass, and not empirical solver parity; a run ID and artifact still need independent verification.

## 4. Source-specific upstream rights and dependency preflight

**GPMC** official Nagoya GitLab source mcc2022 LICENSE.md: MIT, Kenji Hashimoto, 2020, GitLab revision 32225835. Source link: https://git.trs.css.i.nagoya-u.ac.jp/k-hasimt/GPMC/-/blob/mcc2022/LICENSE.md . Earlier pending "original GPMC license" is now RESOLVED at this specific branch. The modified complex version https://github.com/System-Verification-Lab/GPMC/ describes patched ComplexMPFR and derived SharpSAT 12.08.1, Glucose 3.0, SharpSAT-TD preprocessing and FlowCutter. The complex fork's root LICENSE.md **has now been fetched directly** (Git blob 7d9950c527f21e3cb6dc183c29d93f33470f8dfd) and declares **MIT License**; the earlier search had looked for LICENSE rather than LICENSE.md. This establishes top-level source-license identity, but **not** the license obligations of copied Glucose/sharpSAT-TD/FlowCutter/clhash components. File-level derivative code and component notices still need review; MIT at one upstream does not certify all extensions/dependencies.

**sharpSAT** source describes MIT; **SharpSAT-TD** main LICENSE MIT but points to separate flowcutter and clhash licenses; **FlowCutter** BSD, with optional GPL library linkage depending on build; **Glucose sequential** MIT, but Sage's package documentation flags competition-use restrictions in some **parallel glucose-syrup** files (do not apply this to ordinary sequential Glucose by default). A planned MCC entry should avoid unverified restricted third-party code, even if installed elsewhere.

**Ganak release/v2.8.0** LICENSE.txt: MIT for core and BSD-2-style for Flow Cutter. Prior research already verified exact blob SHA. Its CAV 2025 paper discusses S-set/D-set, ChronoBT, and nonzero probabilistic hash collision risk; some argument proofs assume literal probabilities in [0,1] and cannot automatically be applied to arbitrary complex weights.

**d4** source-pinned QOO-157 fork jm62300/d4@be15f91f LICENSE LGPL 2.1; separate crillab/d4 main LICENSE LGPL 3.0, not interchangeable.

**Optional Rust SAT**: Varisat 0.2.2 (Rust CDCL SAT library, MIT/Apache-2.0 dual license); only a potential SAT oracle, not a model counter. **Optional Rust precise arithmetic**: Rug 1.30.0 (GMP/MPFR/MPC, LGPL-3.0-or-later), with native C linkage/build and redistribution tradeoffs; precision rounding alone is not a general source-exact certificate. No dependency chosen or incorporated.

**Independent implementation, not 'certified clean-room'**: prior researchers inspected some upstream source; independently authored mathematical specifications and original fixtures avoid copy-paste, but strict no-exposure clean room has NOT been established. Publication must retain paper citations, authorship, independent design history and later version-pinned license/notice audit; patent analysis is separate.

### Source reading

Ganak2 CAV 2025: https://doi.org/10.1007/978-3-031-98682-6_5 (Section 2, 4.2, 4.3, Algorithm 3).
d4 IJCAI 2017: https://doi.org/10.24963/ijcai.2017/93 .
Dynamic vs Static Top-Down Compilation SAT 2024: https://doi.org/10.4230/LIPIcs.SAT.2024.11 .
Dynamic Blocked Clause Elimination for Projected Model Counting SAT 2024: https://doi.org/10.4230/LIPIcs.SAT.2024.21 .

## 5. Gate before a standalone repository

A0/A0b scientific semantics and design research complete at local independent oracle level, **not** remote CI or live solver evaluation. Pending before actual public implementation: exact GitHub Actions run/retained artifact, complete complex fork & library-level license audit, crates.io/PyPI/trademark availability, pinned Cargo dependency build packaging, and future competition regulations.

No new repo, no Rust solver, no QuPRS main/dev/default/official CodSpeed change. Existing QOO-173 owns future implementation.


Additional independent evidence: [A0c MCC complex AMC format & dual arithmetic research](A0C_MCC_COMPLEX_AMC_FORMAT_AND_ARITHMETIC.md). A separate BigInt rational-complex independent recount of both original 24-case fixture files (39 FullWmc, 9 ProjectedWmc) reproduced all expected counts and cardinalities on 2026-11-05; remote GitHub workflow completion still UNVERIFIED. A0c is the primary MCC format document; avoid parallel duplicate format roadmaps.


## 6. A0d deterministic arithmetic research properties (no Rust solver)

To test mathematical invariants before implementing DPLL/cache, a *newly written* second BigInt rational-complex enumerator was run with deterministic LCG seed 173, giving **RANDOMIZED_EXACT_SEMANTICS_PASS: 620/620** exploratory exact properties:

| Property | Original deterministic cases | Core assertion |
| --- | ---: | --- |
| Weighted Shannon split | 200 | WMC(F)=WMC(F AND x)+WMC(F AND NOT x) for arbitrary rational complex weights |
| Unconstrained variable factor | 200 | WMC(F with new free z)=WMC(F) times (w(z)+w(NOT z)) |
| Existential distinct projection | 120 | Full-model enumeration with projection dedup agrees with independent projection-first existential enumeration |
| Disjoint counted components | 100 | WMC(F1 AND F2)=WMC(F1)*WMC(F2) for disjoint supports |

The re-runnable source is [exact_semantics_properties.mjs](exact_semantics_properties.mjs), completely self-contained Node/BigInt with no external solver or benchmark dependency. The **existing single scoped A0 research job** was extended to run it and retain JSON alongside the two 24-case exact oracle reports; this is a path-filtered research branch step, not an extra production CI shard or a CodSpeed measurement.

**Evidence limits:** The 620/620 outcome is an independent in-session calculation using the same deterministic mathematical test design, and the script is now source-controlled. **GitHub Actions execution of this committed script has not yet been independently verified** by a run ID/log/artifact. The tests validate identities by small exhaustive enumeration, NOT caching performance or correctness of a future Rust solver; the tested formulas are random small controls and cannot replace source-pinned QuPRS weighted-CNF cases.

MCC format research is centralized in [A0c](A0C_MCC_COMPLEX_AMC_FORMAT_AND_ARITHMETIC.md). This A1 RFC retains the GPMC original+complex-fork direct MIT license evidence, d4-version differences and Ganak2 ChronoBT zero-divisor caveat. Avoid adding parallel redundant format/algorithm files.


## 7. A0e component-cache context adversarial science (2026-11-05)

**Research-only original inputs**: [cache_context_fixtures.json](cache_context_fixtures.json), **20 paired comparisons / 40 counting states**. New original [cache_context_oracle.py](cache_context_oracle.py) independently reuses the existing Python Fraction brute-force oracle for validation; its result is now covered by the **existing one-job path-scoped** research workflow. **Independent second JS BigInt implementation crosschecked 20/20 original pair expected counts, SAT full-model cardinalities, and EPWMC projected cardinalities.** No Rust component cache exists and **no completed remote Actions run/artifact has been verified**. Do NOT call this cache implementation PASS or measured performance.

### Exact relation classes (all local expected counts matched)

| Class | Pairs | Exact purpose |
| --- | ---: | --- |
| Same complex count | 6 | Clause order, duplicate clause, tautology, explicit default literal weights, weight change on a provably unused polarity, extra existential free witness in EPWMC |
| Different complex count | 13 | Positive/negative literal weights, declared free support, free phase factor, Full WMC vs EPWMC, distinct P, same-shape opposite polarity, lost unit factor, QuPRS phase-forced vs free, 40-digit cancellation, weight change on projection |
| Equal arithmetic zero with different logical SAT status | 1 | SAT with a zero-weight forced literal vs UNSAT contradictory clauses: count=0 in both, but logical status differs |

An additional standalone proof counterexample deliberately violates *disjoint support*: A=(x OR y) has #SAT=3 over {x,y}, B=(NOT x OR z) has #SAT=3 over {x,z}, while A AND B over {x,y,z} has #SAT=**4**, NOT 9. **Clause/variable support must truly be disjoint after conditioning** to multiply independent component counts. A second counterexample tracks F=x, weight of positive x=i: after the forced assignment the residual empty formula count is 1, while the *caller-owned prefix factor* is i and the full count is i. **Do not contaminate the cached residual value with a caller-specific prefix**, and do not silently drop forced-literal factors.

### Proposed exact scalar cache contract (not implemented)

A cached *sub-count* is a pure function of:
- The complete residual Boolean formula with **canonicalized clauses/literals** and explicit **remaining counted support** (including unmentioned free variables);
- The mode (FullWmc, distinct EPWMC(P), or other explicitly defined projection semantics), the projection mask and proper existential-variable treatment;
- The relevant effective positive and negative literal weights for that subproblem, weight table/version and any *proven* normalization;
- The arithmetic lane (ExactGaussianRational vs noncertified multiprecision vs certified interval) and, **for approximate point caches**, the precision/rounding/error policy; exact count values do not become valid approximation certificates by assertion;
- Any preprocessing transformation witness that changes the representation without preserving all original weight/free/projection semantics by construction.

**Important normalization**: a *caller-side* previously accumulated assignment factor may stay **outside** the sub-count key precisely when the cache stores only the conditioned remaining-component count; if the implementation caches a partially scaled value, factor ownership must be part of the semantics. Thus a blanket "prefix factor must always be in every cache key" is **incorrect**. Similarly, if the implementation uses exact symbolic polynomial/compiled structure rather than numerical scalar entries, weight-version reuse can be sound through re-evaluation and is a *different cache type*, not scalar cache reuse.

A HashMap hash is only an index. Deterministic exact results require a full canonical equality comparison (or a separately proven injective ID scheme). Key collision must not silently act as equivalence. Free variables must be included in count ownership **once**, not counted again after component multiplication. The cache retrieval operation must have an unambiguous returned status: cached exact count 0 **does not** certify UNSAT. If the public result requires logical SAT/UNSAT, cache the Boolean existence witness or compute it in a separate sound logical oracle.

### Why learning+decomposition is a separate proof obligation

[Sang, Bacchus, Beame, Kautz & Pitassi, *Combining Component Caching and Clause Learning for Effective Model Counting* (SAT 2004)](https://homes.cs.washington.edu/~beame/papers/cachet.pdf) and [Sang, Beame & Kautz, *Heuristics for Fast Exact Model Counting* (SAT 2005)](https://homes.cs.washington.edu/~beame/papers/cachet-heuristics.pdf) explicitly discuss the correctness difficulty of learned-clause implications crossing previously separated components and necessary cache/propagation bookkeeping. These are published mathematical/algorithmic lessons, not an instruction to copy Cachet's implementation or eviction rules.

**A1 recommendation**: first build a deterministic, no-cross-component-learning weighted DPLL+decomposition+canonical scalar cache. Add modern CDCL/learned-clause sharing only after a *separate* proof or independent oracle test of cross-component dependencies, conflict backtracking, forced-weight ownership, and cache invalidation. Do not assume the existing 620 arithmetic identities test these dynamic learned-clause contexts. Avoid adopting paper-specific cache ages/magic constants without independently deriving and testing a policy.

### Concrete work completed vs outstanding

Completed: original 20 cache-context pairs and their expected rational-complex counts, independent in-session JS verification 20/20, original Python reference validator, an added **step** to the existing low-cost branch-scoped A0 workflow, and this mathematical A1 contract/literature review.

Outstanding: actual GitHub Actions **run ID, conclusion and artifact** for the updated branch; live Rust cache implementation/evaluation; source-CNF solver conformance and held-out CodSpeed; any third-party code reuse/license approval. A0e outcomes are **LOCAL_REFERENCE_CHECK_PASS / REMOTE_CI_UNVERIFIED / RUST_NOT_STARTED**. No new RaWMoCS repo or QuPRS main/dev/default change.


## 8. A0f exhaustive exact-complex preprocessing-soundness study (2026-11-05)

**Source-controlled independently authored mathematical reference:** [exhaustive_weighted_rewrite_safety.mjs](exhaustive_weighted_rewrite_safety.mjs). This is separate from GPMC/d4/Ganak and previous Python oracles, using **exact Gaussian integer** operations (not f64 or MPFR). Enumerates all 256 CNF subsets of two Boolean variables formed from 8 unique non-tautological length-1/length-2 clauses. Each of 4 literal polarities independently has a weight from {0,1,-1,i}, yielding 256 weight configurations per CNF.

**In-session reference result: 65,536/65,536 states** verified. This is not GitHub Actions PASS, Rust solver verification or a CodSpeed performance result.

| Mathematical check | Exact checks | Result |
| --- | ---: | --- |
| Add an existing duplicate clause (same variable universe) | 65,536 | PASS |
| Add tautology x OR NOT x (retaining declared support) | 65,536 | PASS |
| Add a logically redundant clause subsumed by an existing clause | 65,280 | PASS |
| Factor weight for forced unit assignment exactly once | 49,152 | PASS |
| Isolated equivalence x iff y, with weights combined on elimination | 256 | PASS |
| Satisfiable but weighted count exactly zero | 10,049 cases | Witness count, not failures |
| Force a pure literal without count compensation | Explicit counterexample | UNSOUND |
| Drop an equivalence variable without reweighting | Explicit counterexample | UNSOUND |

**Pure literal witness:** F=(x OR y), w(x)=0, w(NOT x)=1, w(y)=1, w(NOT y)=0. Then **WMC(F)=1**, but forcing positive-pure x=1 changes full WMC to **0**, despite preserving SAT truth. An even simpler all-weights-one example has full model count 3 versus 2 if x is forced. SAT-safe pure-literal elimination is therefore not a generally valid counting simplification.

**Equivalence witness:** For the **isolated constraint** F=(x iff y), the exact full count is w(x)w(y)+w(NOT x)w(NOT y). Eliminating counted y can be correct by reweighting x as w'(x)=w(x)w(y), w'(NOT x)=w(NOT x)w(NOT y). Simply removing y is incorrect. More formula clauses involving x/y or changes to projection require separate formal rewrite obligations; this example does not authorize a general unconstrained equivalence-substitution pass.

### General theorem, separate from the finite tests

With a FIXED declared Boolean universe V, fixed literal weights w and a commutative semiring, if formulas F and G are logically equivalent on every assignment over V, then they have exactly the same set of satisfying assignments and thus WMC_V(F,w)=WMC_V(G,w). This is true even for zero, negative and complex weights. The finite test validates the named transformations in its small universe; the theorem itself follows directly from the WMC definition. **Do not remove declared free variables** when simplifying an equivalent CNF: a free counted variable still contributes w(x)+w(NOT x).

For distinct EPWMC over P, preserving the full truth function of the existential projection (existentially quantify V\P) for every projected assignment is sufficient; preserving only global SAT/UNSAT of F is not. Changes of projection or weight semantics require an explicit mapping/factor witness.

| Proposed preprocessing | Mathematical requirement for full Complex WMC | A1 decision |
| --- | --- | --- |
| Clause/literal ordering and duplicate clause deletion | Same models on V | Allow exact canonicalization |
| Tautology deletion and subsumption | Same models on V, keep free counted support | Allow with exact support bookkeeping |
| Add a globally implied learned clause | Implication must hold at the exact residual component/cache scope | Later only, requires dependency/scoping proof |
| Unit propagation and remove assigned variable | Apply the forced literal factor once | Allow with trail/factor ownership |
| Pure literal forcing | SAT preserving only, may change weighted count | Disable absent special proof |
| Blocked Clause Elimination | General SAT-safe BCE is count-changing | Disable absent complex-WMC proof |
| SAT-style existential variable forgetting | Loses extension multiplicity | Disable for full WMC absent extension-weight witness |
| Literal-equivalence substitution | Combine polarity weights, preserve projection/extension mappings | Future optional guarded rewrite |
| Residual SAT for distinct EPWMC | Valid for purely existential suffix after projected assignments/weights fixed | Separate typed mode only |

Relevant published mathematical ideas: Lagniez/Marquis/Biere, [Dynamic Blocked Clause Elimination for Projected Model Counting (SAT 2024)](https://arxiv.org/abs/2408.06199), demonstrates SAT-safe BCE generally changes projected model count and supplies a specialized projected-safe rule. Lai/Meel/Yap, [The Power of Literal Equivalence in Model Counting (AAAI 2021)](https://doi.org/10.1609/aaai.v35i5.16503), motivates counting-aware literal equivalence; neither licenses copying external code or ignoring complex weights.

The SAME one-job path-filtered A0 research workflow now adds this lightweight source-only property test and writes the evidence artifact named rawmocs-a0f-exhaustive-rewrite-safety.json. This does not create a new production CI shard. **A completed GitHub Actions run ID, logs and artifact have not yet been independently verified** with the available tools. Preserve REMOTE_CI_UNVERIFIED.

**Decision:** The first Rust MVP should restrict preprocessing to model-set-preserving canonicalization and explicitly weighted unit propagation. SAT-only shortcuts, unconstrained BCE, pure-literal forcing, or cross-component learned clauses need separate proof and held-out scientific gates; no claim of runtime improvement or change to QuPRS GPMC default follows from this study.

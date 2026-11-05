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

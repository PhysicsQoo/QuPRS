# RaWMoCS A0 — Exact Complex WMC semantics, independent oracle, A1 implementation contract

Date: 2026-11-05. Owner: Linear QOO-173. Status: A0 mathematical/science specification with 24 exact reference cases and independently verified expected values. This is NOT the RaWMoCS Rust solver. Research stays on the existing QuPRS experiment branch. QuPRS main/dev, default GPMC and release CI remain unchanged.

## 1. Mathematical domain and two distinct counting semantics

Let V={x1,...,xn} be the declared variable universe, F a CNF, and w(x),w(¬x) arbitrary rational complex numbers (Q[i]) for this exact oracle. Both literal weights are explicit or default INDEPENDENTLY to 1+0i; do not normalize to probabilities or impose w(x)+w(¬x)=1.

**Full complex WMC** (QuPRS's current requirement):

\[
\mathrm{WMC}_V(F,w)=\sum_{a\in\{0,1\}^{V},\,a\models F}
\prod_{x\in V}w(x^{a_x}), \qquad x^1=x,\ x^0=\neg x.
\]

Every satisfying FULL assignment contributes exactly once. A declared variable absent from every surviving clause contributes w(x)+w(¬x), NOT automatically 1. With weights 1 for both polarities, this specializes to #SAT (each free variable contributes 2).

**Existential distinct-projection weighted semantics (EPWMC)** (a separate OPTIONAL mode, not QuPRS's default; see the A0b RFC below for another projected-weight convention in the Ganak2 paper):

\[
\mathrm{PWMC}_P(F,w)=\sum_{p\in\{0,1\}^{P}}
[\exists e\in\{0,1\}^{V\setminus P}:F(p,e)]
\prod_{x\in P}w(x^{p_x}).
\]

Only projection variables P may have explicit weights. Nonprojection variables are existential witnesses, not separately weighted models. Multiple satisfying extensions of a projected assignment count ONCE. For P empty, PWMC=1 if SAT, 0 otherwise. Full WMC != projected WMC in general.

This reference oracle uses exact rational-complex arithmetic solely for scientific verification. Quantum source phases exp(i theta) are generally not rational complex. MPFR high working precision or printed digits alone do NOT certify numeric error or source-exact quantum equivalence. RaWMoCS returns counts and precision/status provenance; QuPRS retains final equivalence verdict and tolerances.

## 2. Independent 24-case fixture corpus

- Original JSON reference data: [complex_count_fixtures.json](complex_count_fixtures.json) (24 cases, 0–8 variables, exact rational complex weights, clauses, expected real/imaginary count, SAT cardinality and projected model cardinality).
- Independent Python stdlib oracle: [exact_complex_oracle.py](exact_complex_oracle.py), using Fraction-based exhaustive full-assignment counting, plus a SECOND projection-first existential oracle, and metamorphic checks of clause order, idempotence, variable bijection and tautology insertion.
- Path-scoped 5-minute, research-only GitHub workflow: [.github/workflows/qoo157-rawmocs-a0-reference.yml](../../../.github/workflows/qoo157-rawmocs-a0-reference.yml). NO solver execution, CodSpeed, or production CI. Do not claim workflow PASS without a verified completed run and artifact.

### Key exact acceptance anchors

| Case | Intent | Exact count | Logical/cardinality fact |
| --- | --- | --- | --- |
| empty_true | Zero variables, no clauses | 1 | One empty model |
| empty_false | Zero variables, empty clause | 0 | UNSAT |
| free_unit_weights | Free x, weights 1/1 | 2 | SAT, 2 full models |
| free_asymmetric | Free x, weights 3 and -1/2 | 5/2 | Two models |
| positive_complex_unit | x forced, weight 1/3+2/5i | 1/3+2/5i | One |
| sat_real_cancel_zero | Free x, weights +1/-1 | 0 | SAT, two models |
| sat_imag_cancel_zero | Free x, weights +i/-i | 0 | SAT, two models |
| sat_zero_weight | x forced with weight 0 | 0 | SAT, one model |
| unsat_contradiction | x and not x | 0 | UNSAT, zero models |
| disconnected_complex_units | (2+3i)(1-i) | 5+i | Multiplicative |
| disconnected_complex_free | (2+1)(i+2i) | 9i | Four models |
| or_two_weighted | x or y, asymmetric positive weights | 30 | Three full models |
| xor_complex_cancel | XOR complex cancellation | 0 | SAT, two models |
| equivalence_complex | Equivalence on two variables | -3i | Two models |
| same_cnf_weights_v1 and v2 | Identical CNF, weights changed | 3 and 0 | Cache scalar must be versioned |
| projected_or_dedup | F=x or y, P={x}, weights 2/3 | 5 | Three full extensions but two projections |
| projected_empty_sat / unsat | Empty projection | 1 / 0 | Existential truth |
| projected_free_factor | P={x,y}, F=x, y weights 3/5 | 16 | Two projections |
| forty_digit_cancellation | 10^40 + (-10^40+1) | 1 | Naive f64 yields 0 |
| tiny_imag_residual | (1+i·10^-30) + (-1) | i·10^-30 | Nonzero exact imaginary |
| eight_vars_free_factor | 8 vars, two forced, nonunit others | 320i | 64 full models |

An independently written local SECOND exhaustive enumerator reproduced 24/24 exact expected values on 2026-11-05. This is a small-fixture science result, not mathematical proof of future algorithms or confirmation of GitHub CI.

### Unsound optimization counterexamples

1. SAT => WMC=1 is FALSE: F=true, w(x)=1 and w(¬x)=-1 gives SAT but WMC=0. Even when both weights=1, WMC=2 rather than 1.
2. Therefore even an all-unweighted residual FULL-WMC problem CANNOT generally be reduced to a mere SAT decision. A unique-weighted-extension certificate (or an equivalent explicitly accounted factor) would be required. In PWMC ONLY, existential suffix SAT is legitimate AFTER projected weights and multiplicity are already correctly handled.
3. Declared free variables contribute w(x)+w(¬x); removing a tautology alone does not justify removing its remaining free variable from the counted universe.
4. A weighted result zero does not imply logical UNSAT; SAT zero-weight and UNSAT zero must have distinct evidence.
5. Same residual clause bytes with different weight context cannot reuse a cached scalar count.

## 3. A1 independent DPLL and component accounting contract

An independently designed mathematical core should obey:

- Contradiction gives arithmetic 0; distinguish logical UNSAT from arithmetic zero from cancellation.
- Maintain remaining counted support SEPARATELY from surviving clauses; account for all declared free variables. Assigned literals, including unit-propagated assignments, contribute weights exactly once.
- For a branch on unassigned x:
\[
C(F,U,w)=w(x)C(F|_{x=1},U\setminus\{x\},w)
+w(\neg x)C(F|_{x=0},U\setminus\{x\},w).
\]
- For components on mutually disjoint remaining variable supports, with separate truly free variables:
\[
C(F,U,w)=\left[\prod_j C(F_j,U_j,w)\right]
\left[\prod_{x\in U\setminus\cup_j U_j}(w(x)+w(\neg x))\right].
\]
Only apply this formula in the appropriate full-WMC commutative semiring; projected-existential counting requires a separate proof.
- Cache exact semantics: normalized residual clause set, remaining-counted-variable universe (including free support), compatible weight identity/version, projection/mode (if present), arithmetic precision/provenance, factor normalization. A hash may index but MUST be checked against canonical content for deterministic exact matching.
- Record all eligible cache queries, hits, misses, evictions, resident/peak allocated bytes, component count, work counters, free factors. Ensure hits+misses=eligible. Memory budget is on allocated bytes and actual owner structures.
- Generic SAT transformations, BCE, equivalent-literal substitutions are NOT automatically weight-preserving, even if SAT preserving or #SAT preserving. Every accepted transformation needs a count-preservation proof/witness for real/imaginary weights, projection, and multiplicity.
- Solving statuses distinguish invalid input, logical SAT/UNSAT, arithmetic exact-zero, certified interval potentially containing zero, uncertified numerical estimate, timeout, cancellation, OOM, and internal failure. No internal QuPRS equivalence verdict.

### Interface design candidates (NOT implemented)

CountRequest: weighted CNF; counting semantics FullWmc vs ExistentialDistinctProjectedWmc(P); arithmetic ExactQComplex vs MPFRPoint vs CertifiedInterval; deadline; resource budget. The label PWMC in this original study is shorthand only for the explicitly stated existential distinct-projection equation, and must not be assumed to match arbitrary solver PWMC CLI contracts.

CountObservation: typed complex count; exact/interval/point-estimate precision provenance; source CNF fingerprint and separate weight fingerprint; work/memory stats; solver status. SAT oracle is isolated and cannot silently change a full-weighted count into a Boolean.

Reuse existing QuPRS solver boundary (wmc_problem.rs, solver_adapter.rs, precise_weight.rs, solver_process.rs) only on future integration; QuPRS retains all tolerance decisions. Full external solver startup/setup/serialization time must be counted in official CodSpeed comparisons.

## 4. Algorithm literature and actual license-file audit

**GPMC**: projected model counting with component decomposition and SAT residual conditions: [official Nagoya source page](https://www.trs.css.i.nagoya-u.ac.jp/projects/PMC/) (Suzuki–Hashimoto–Sakai 2017). QuPRS [NOTICE.md](https://github.com/PhysicsQoo/QuPRS/blob/main/NOTICE.md) says its bundled GPMC is MIT. **Update 2026-11-05**: official original Nagoya GPMC GitLab mcc2022 LICENSE.md was subsequently confirmed to state MIT (copyright Kenji Hashimoto, revision 32225835). This certifies that upstream branch's declared license, not all files or the QuPRS complex GPMC extension's complete derivative dependency chain; refer to the A0b RFC.

**d4**: Lagniez–Marquis [IJCAI 2017](https://doi.org/10.24963/ijcai.2017/93) describes disjoint components, caching and sparse hypergraph decomposition.
- Research pinned d4 source jm62300/d4@be15f91f3e9769e1f5cb175fa27e3eca3a1ea690 LICENSE blob c6ae956eff5e7a60d9683d7e39e2382571583c3b identifies **LGPL 2.1**.
- Separate crillab/d4@main LICENSE blob ce20624b22680921d521a86b8ada263d8229c2ed identifies **LGPL 3.0**.
- The prior blanket assertion that every d4 version is LGPL-3.0 is WRONG. Version- and component-specific license review remains required before linking/reuse/distribution.

**Ganak2**: [CAV 2025](https://doi.org/10.1007/978-3-031-98682-6_5); [Ganak IJCAI 2019](https://doi.org/10.24963/ijcai.2019/163). Current upstream release/v2.8.0 LICENSE.txt blob bd0fd659367922355a61aed8d7f8da85c2cf3323 states Ganak non-Flow-Cutter code MIT, Flow Cutter BSD-2-style. Current Ganak offers --prob 0 NON-probabilistic mode; probabilistic caching is a choice, not a universal restriction. Ganak2 separates SAT eligibility S-set and decision D-set; authors warn that weighted variables cannot be eliminated from SAT-eligibility without extra synthesis evidence.

**AMC**: [Algebraic Model Counting (2017)](https://doi.org/10.1016/j.jal.2016.11.031). Complex (+,×) is ONE instance of the commutative semiring framework; first release must not imply generic symbolic algebra or fully generic semiring support.

**MCC**: [2026 tracks](https://mccompetition.org/2026/mc_description) included experimental 5B complex AMC and 2B negative weights. [Submission rules](https://mccompetition.org/2026/submission) use build.sh/run.sh and resource limits. Future competition rules cannot be assumed unchanged.

### Attribution/independence requirements

Choose independent implementation from published mathematical specification, original data structures, original tests, fixed scientific provenance and explicit citations. Do NOT label it strict clean room: previous QOO-157 researchers inspected upstream implementation code; a separate independent uninformed implementation team has not been constituted. No upstream source, comments, magic constants, or vendor test text copied into RaWMoCS. License, copyright, patents and attribution each require their own assessment.

## 5. Research gate and outstanding items

**A0 science completed:** formalized full and projected counting separately, 24 source-controlled original exact fixtures, second independent local 24/24 reference check, original Python reference oracle, metamorphic tests, experiment-only CI definition, source-specific license notes and A1 invariants.

**CI verification pending:** obtain a real completed workflow run ID and retained JSON artifact before asserting CI PASS. Never invent a run.

**Only tasks needing future RaWMoCS repo:** Rust solver implementation; Cargo workspace and actual dependency licensing; package/release workflow; future CodSpeed same-SHA fixed Macro Runner ABBA/BAAB and solver-inclusive/end-to-end comparisons. Remaining pre-publication business checks: crates.io/PyPI name ownership/trademark, full upstream/subdependency license pins, MCC version-specific format.

No new repository or Rust solver has been created; no QuPRS production/default/CI changes.


## 6. A0b new evidence, QuPRS literal profile, and semantic cautions

* 24 additional QuPRS-specific literal-profile exact Gaussian rational fixtures: [quprs_literal_profile_fixtures.json](quprs_literal_profile_fixtures.json). Positive literal has complex weight and negative literal always weight 1, as pinned to QuPRS `main` in `rust/pathsum/src/solver_adapter.rs` and `wmc_problem.rs`.
* [A0b / A1 independent algorithm RFC](A1_PREIMPLEMENTATION_ARCHITECTURE_AND_LITERATURE.md) documents **Ganak2 projected weight-class aggregation vs EPWMC semantics**; Ganak2 ChronoBT compensation uses division by weights, which is NOT valid for zero weights or general semirings, hence not a safe first-version Complex WMC optimization.
* Both 24-case fixture suites independently reproduced at exact arithmetic level; still **no independently verified GitHub Actions completion/retained artifact**, no solver implementation, no CodSpeed performance measurement. Experiment branch workflow now runs both suites and retains separate reports.
* **Do not claim the prior study's generic projected example is identical to Ganak2 2.8.0 projected mode** without real input/output contract verification. In the next solver implementation, make `FullWmc` and `ExistentialDistinctProjectedWmc` distinct typed variants.

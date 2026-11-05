# RaWMoCS A0 — MCC 2026 wire formats, upstream provenance and independent engineering gate

Date: 2026-11-05. Owner QOO-173. Research-only existing QuPRS experiment branch; no new repository, Rust solver or production CI modification.

## Decisions supported by official specifications

1. **Exact complex WMC is materially different from MPFR complex WMC.** MCC 2026 experimental Track 5B is an Algebraic Model Counter over the complex field. Exact count for rational/finite-decimal weights can use unlimited-precision rational real/imaginary components. An MPFR point estimate, even with a large requested number of digits, is not a mathematical exactness certificate.
2. **QuPRS CNF wire syntax and MCC complex input have different grammars.** Current QuPRS source WmcProblem emits header c t wmc, GPMC pair re/im weight fields with -mode=1, and Ganak complex-i fields with --mode=6; negative literal weights are 1 by default in the QuPRS encoding. The competition format expects c t amc-complex, and literal weights may independently apply to both signs. Implement distinct named parsers/adapters, not implicit fallbacks.
3. **PWMC and full WMC must have different types.** The official 2025/2026 format constrains PWMC explicit weights to projection variables. Multiple satisfiable existential extensions of one projection are counted ONCE; full WMC counts every satisfying full assignment.
4. **SAT status and numerical count status must be independent.** A satisfiable formula can have complex count exactly zero or a floating estimate near zero. MCC asks for an s SATISFIABLE/UNSATISFIABLE/UNKNOWN line IN ADDITION to separate result data. Boolean SAT cannot be inferred from complex weighted count.
5. **An MIT top-level license never automatically relicenses copied or linked dependency code.** Cite mathematical papers, derive independent Rust data structures, and check the precise source/component licenses before any redistribution.

### Intended parser and adapter compatibility

| Format | Header mode | Weight notation example invented for this spec | Status |
| --- | --- | --- | --- |
| QuPRS -> GPMC complex extension | c t wmc; -mode=1 | c p weight 1 2.0 -0.5 0 | Existing QuPRS code verified |
| QuPRS -> Ganak mode 6 | c t wmc; --mode=6 | c p weight 1 2.0 - 0.5i 0 | Existing QuPRS code verified |
| MCC real/negative WMC | c t wmc | c p weight 1 -3/4 0 | Future dialect contract only |
| MCC projected WMC | c t pwmc + c p show 1 0 | c p weight 1 2/3 0 | Future, projection weights only |
| MCC complex AMC | c t amc-complex | c p weight 1 2/3-1/5i 0 | Future, both signs must be representable |

For MCC, separate original input fields for positive and negative literals must be parsed, including explicit zero, negative, real and imaginary components. The invented examples are proposed test strings, NOT confirmed parser acceptance by an existing solver. Read the exact allowed lexical forms and decimal precision from the official format before publishing a parser; the specification still contains prose inherited from nonnegative real WMC even in its complex section, so 0<=complex is NOT a coherent mathematical invariant.

Output preflight:
- A logical satisfiability line s SATISFIABLE / UNSATISFIABLE / UNKNOWN from valid Boolean evidence.
- c s type amc-complex.
- Real and imaginary separate log10-estimate fields with sign and zero handling.
- High-precision output c s SOLVERTYPE PRECISION NOTATION COMPLEX, where exact arb frac is legitimate only for a truly exact rational-complex count; MPFR point computation must not be mislabeled exact.
- Distinguish timeout, memory, malformed input, invalid precision, scientific uncertainty; output fields must match the supported competition format.

Validation negative controls:
- Reject missing/duplicate CNF headers, unexpected problem types, mismatched clause counts, invalid literal indices, zero denominators, contradictory weights and unsupported numeric notation.
- Never treat a declared free variable as absent from the count: its factor is positive_weight + negative_weight.
- FullWmc SAT-but-zero: true formula with one free variable weighted +1/-1 must report logical SAT and count 0.
- FullWmc all-ones: true formula with one free variable weights 1/1 must return 2, not SAT=1.
- ProjectedWmc: multiple existential extensions must not multiply a projected model's weight.
- Same CNF with changed weights must not reuse a scalar cached result.
- Roundtrip original A0 24-case JSON through each accepted dialect, then compare parsed semantic structures and exact rational-complex values. The adapters/parser and that roundtrip test are A1 IMPLEMENTATION WORK, not completed research code.

**Official documents**: [2026 Tracks](https://mccompetition.org/2026/mc_description), [Submission](https://mccompetition.org/2026/submission), [Model Counting Data Format v1.2, updated May 2026](https://mccompetition.org/assets/files/mccomp_format_25.pdf). 2026 rules require build.sh, run.sh, 3600-second time limit, 32GB memory, and competition solver submission by PRIVATE GitHub repository. Therefore public repo release is NOT a prerequisite to participation in this specific year's competition. New rules must be checked for any later year.

## Independently checked upstream license and transitive-code sources

| Component | Reproducible source | Verification |
| --- | --- | --- |
| **Original GPMC** | [Kenji Hashimoto GitLab mcc2022/LICENSE.md](https://git.trs.css.i.nagoya-u.ac.jp/k-hasimt/GPMC/-/blob/mcc2022/LICENSE.md) historical file commit 32225835 (2020-08-04) | MIT text directly published by original author. |
| **Complex MPFR GPMC extension** | [System-Verification-Lab/GPMC](https://github.com/System-Verification-Lab/GPMC), LICENSE.md blob 7d9950c527f21e3cb6dc183c29d93f33470f8dfd | MIT license; README identifies Glucose, sharpSAT, sharpSAT-TD and FlowCutter ingredients. |
| sharpSAT | [marcthurley/sharpSAT](https://github.com/marcthurley/sharpSAT) | Upstream MIT indicated; exact imported version and files require pins if reused. |
| sharpSAT-TD | [Laakeri/sharpsat-td/LICENSE](https://github.com/Laakeri/sharpsat-td/blob/main/LICENSE) | MIT; points to additional flowcutter and clhash licenses. |
| FlowCutter PACE17 | [kit-algo/flow-cutter-pace17](https://github.com/kit-algo/flow-cutter-pace17) | Upstream BSD-2-Clause. |
| Glucose 3 / MiniSat family | [audemard/glucose](https://github.com/audemard/glucose), [Sage Glucose license guidance](https://doc.sagemath.org/html/en/reference/spkg/glucose.html) | Sequential Glucose MIT; parallel Glucose-Syrup carries a specific competition-use restriction in the described version. DO NOT assume competition permission from the Glucose name alone. |
| **d4 used for QOO-157 experiments** | jm62300/d4 pinned be15f91f3e9769e1f5cb175fa27e3eca3a1ea690, LICENSE blob c6ae956eff5e7a60d9683d7e39e2382571583c3b | LGPL 2.1. |
| Other older d4 repository | crillab/d4 main, LICENSE blob ce20624b22680921d521a86b8ada263d8229c2ed | LGPL 3.0. Must not aggregate as one universal license. |
| **Ganak 2.8.0** | meelgroup/ganak release/v2.8.0, LICENSE.txt blob bd0fd659367922355a61aed8d7f8da85c2cf3323 | Ganak main MIT; bundled Flow Cutter BSD-2-style. |

This is an upstream source and version *preflight*, not a recursively complete Software Bill of Materials for a future solver. No third-party implementation code is proposed for reuse at A0, and no chosen Rust dependency is licensed by this table. Strict no-exposure clean-room cannot be claimed because prior QOO-157 work inspected some upstream code. Independent derivation with mathematical specification, original IR, self-authored tests and complete scholarly citations remains the correct approach.

**Published algorithms (citations)**: GPMC original project (Nagoya, 2017); Lagniez/Marquis d4 [IJCAI 2017](https://doi.org/10.24963/ijcai.2017/93); Ganak [IJCAI 2019](https://doi.org/10.24963/ijcai.2019/163); Ganak2 [CAV 2025](https://doi.org/10.1007/978-3-031-98682-6_5). Search heuristics, S/D-set, d-DNNF and decomposition papers describe reusable ideas but are not code-import licenses.

## Gate conclusion — still no new repo

A0 is sufficiently specified for independent A1 planning: 24 oracle cases, full-vs-projected proof obligations, complex rational vs MPFR distinction, semantic parser compatibility, cache invariants, named algorithm citations, exact author-license evidence and transitive license risk notes.

Pending before release: official CI run/artifact evidence for the existing scoped reference workflow (tools here did not provide a verified completed run), complete license/SBOM of any ACTUAL dependencies selected, new crate name/registries/trademark preflight, and version-specific future MCC rules. These are not grounds to change QuPRS main/dev, ship new solver, or claim CodSpeed performance.

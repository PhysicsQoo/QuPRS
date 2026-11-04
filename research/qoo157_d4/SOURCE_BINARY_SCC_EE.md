# QOO-157 — original binary implication SCC audit against native GPMC EE

A bounded **source-only** double-entry audit of original four QuPRS weighted
CNFs. From source DIMACS binary clauses `(a ∨ b)`, construct implications
`¬a→b` and `¬b→a`. Compute strongly connected components on the
2n-literal graph, group variables equivalent modulo negation, count how many
could be merged by binary-only literal equivalence, and how many source-weighted
variables occur in nontrivial groups.

For QAOA7/QFT16 only, compare independent source SCC reduction count with
source-identical [GPMC verbose native EE-stage](GPMC_NATIVE_STAGE_TRACE.md)
at the same pinned source CNF SHA, **without running or modifying solvers**.
Exact agreement provides a strong mechanism hypothesis; it does not by
itself prove per-variable native mapping, WMC arithmetic precision, or the
complete causal source of GPMC-versus-d4 performance.

CI is zero-build, reuses original archived source CNFs and immutable native
trace, and performs **no performance measurement**. Do not use elapsed CI
time for ranking. Coupled native and source evidence can guide future
weight-preserving binary-equivalence preprocessor experiments, but no solver
replacement is approved by this audit.


## Completed independent binary-implication SCC/native-GPMC cross-check

**SUCCESS**: [GitHub Actions #41841992767](https://github.com/PhysicsQoo/QuPRS/actions/runs/41841992767), [artifact #13329292272](https://github.com/PhysicsQoo/QuPRS/actions/runs/41841992767/artifacts/13329292272), source SHA `aa6eb48b99c8a7f40ed8827d0abcef91221bb698`. Zero native builds; original 4 CNF source SHA256 checked against original archive, native QAOA7/QFT16 EE stage claims checked against [source-fixed GPMC native artifact #13327644747](https://github.com/PhysicsQoo/QuPRS/actions/runs/41839854976/artifacts/13327644747).

| Original QuPRS CNF | Binary implication SCC equivalent-var reduction | Nontrivial class histogram | Source-weighted vars appearing in nontrivial classes | Native GPMC EquivEl reduction |
| --- | ---: | --- | ---: | ---: |
| Grover4 EQ | 103 | 92 × size2; 1 × size3; 3 × size4 | 99 / 256 weighted | Not independently run |
| QAOA7 genuine NEQ | **153** | 132 × size2; 7 × size4 | **146 / 319 weighted** | **153 vars, 306 clauses** — exact match |
| QPE exact8 EQ | 66 | 43 × size2; 1 × size3; 7 × size4 | 58 / 178 weighted | Not independently run |
| QFT16 EQ | **102** | 54 × size2; 16 × size4 | **86 / 400 weighted** | **102 vars, 204 clauses** — exact match |

For QAOA7/QFT16, the variable reductions computed **solely from original binary-clause implication SCCs** coincide exactly with actual source-pinned GPMC `EquivEl` native var reduction. Every merged equivalence group shown in the source audit has at least one source-weighted variable (one in size2 groups, two in size4 groups). This gives a **strong, specific, independently reproducible candidate mechanism**: literal-equivalence merging with correct weight aggregation exploits low-width binary implication patterns already present in QuPRS-generated WMC CNF.

**Proof/interpretation limits:** an SCC quotient is a conservative *source 2-SAT implication relation*. Agreement of total counts does not prove the native solver merged precisely the same variable IDs, nor that the 306/204 deleted clauses individually correspond to every SCC edge; a per-variable mapping audit would be needed. It is not a demonstration of GPMC-versus-d4 walltime causality, solver arithmetic exactness, or a license to disable d4 weighted-variable protection. d4 BiPe treats asymmetric-weight variables as protected, and cannot simply merge their literals without count-preserving **positive/negative weight multiplication** and correct free-variable/projection handling. No solver/default or upstream code was changed.

**Next bounded science step:** source-to-residual per-variable equivalence map and weight-product validation on a small rational/complex oracle, **before** any attempt to adapt a GPMC-like merge to d4. Production default remains GPMC; d4 PoC research only; Ganak remains separately qualified in QOO-98.

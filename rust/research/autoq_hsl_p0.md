# AQ-R4 native HSL adapter (candidate)

Source pin 7eed39ad7ba5615a87c3f532a24f866e08967c12; immutable fixtures embedded directly from these GitHub blobs:
- BV/03/pre.hsl: c5d58ba0764d33099613e49aea8a20f174be9ca0
- BV/03/post.hsl: 3bcc54d9fc6bf3ca618a67808f2d3da3c3fb86b6
- BV/03/circuit.qasm: f399669db5b5e8ac469f70de179491e2008694fb
- Grover/03/pre.hsl: 9c369a362f5e504cd5d4cc64b4b5297a06661b42
- Grover/03/post.hsl: 5d45f38067d9e95ff0afe997c5f175cc1082e7e4
- Grover/03/circuit.qasm: 79604029953261a0cd419b9ec932b055dd9ea0c8

P lane (QOO-212), QOO-268 A4/A5; this adapter reuses native_rr_checkpoint/guarded_native_step (which call existing PathSum try_reduce rules), compact and native_dyadic_cnf::Cnf. No separate reducer, solver, mode or production API. Not evidence of future shared Conditional RR completion. Normalized singleton, fixed basis pre, same-scale disjoint exact-real HSL only; other syntax fail closed. Symbolic multiplicity guard and unique basis binding eliminated by output equality, no frontend path or ket enumeration. HSL textual leftmost bit maps to native qubit 0. Both original and post-relative mutants, plus global sign UTS control. Pure RR reports UNKNOWN when nonterminal; WMC uses raw, Hybrid residual; exact norm of overlap from packed phase counts. GPMC primary, Ganak independent counts on identical CNF; 10s per query envelope, no approximate results. The existing CI workflow builds the test, exports fixtures and invokes helper. No AutoQ executable or native verification accepted until CI receipts; no throughput or novelty claims. Stop after these 18 arms, not more synthetic controls; next source/AST semantic refinement and actual AutoQ executable comparison.

## R5 candidate — label-preserving StateSet

R4 exact CI 45924296579: 18 arms, 15 definite, 3 Grover RR UNKNOWN; all 9 GPMC and 9 Ganak bins match. BV hidden 8→0, Grover 17→7. No speedup claim. R5 reuses MOGrover/03 pinned source: 286d24f8d0e43e07535658526682566d4897823d, 413ee90158043d0e17dc9285261b05de694793d1, 4a5cc0a405f2c67172de5a7fe2ca16fcfac77bdc. Restricted one outer binder (≤3 bits), fixed basis input, disjoint same-scale normalized real target; instantiate only 8 external labels, not coherent paths. Prefix-support and raw/reduced native ANF identity prove unique possible matching target label; no general pointwise conversion. Independent dense gate oracle per label, sharing HSL target parser; forall aggregation. Existing R4 18 arms plus 72 MOGrover arms; nine source blobs rehashed before solvers. No new workflow or reducer. No actual AutoQ executable / general StateSet / speed claim. Candidate until CI. Stop at these 90 arms; unsupported cases remain outside admission.

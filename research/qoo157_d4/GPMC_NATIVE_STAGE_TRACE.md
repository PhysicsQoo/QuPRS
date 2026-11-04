# QOO-157 — native GPMC equivalence-elimination stage transitions

This follow-up instruments **no solver code**: it enables the existing
source-pinned GPMC `-ppverb=1` output, capturing `[Init]`, `[EquivEl]`,
`[VE]`, `[DefVE]`, `[Simp]` actual variables, projected variables,
clauses, and native stage repetition for QAOA7 NEQ and QFT16 EQ.

Two configurations: all defaults fixed at 38-effective-decimal digits /
`-mode=1 -prec=38 -vs=1 -td`, only `-pp_ee` on/off changes. Original
weighted CNF SHA256 and archived exact-rational complex count are checked.
Accept under 1e-12 *count-scale* screen only, not certified arithmetic.

**Not a performance benchmark.** Existing QOO-157 CodSpeed #41837297080
already measured the total effect of GPMC EE on/off. This stage trace
identifies where variables disappear, and separates EE from downstream
variable elimination or other preprocessing. No Python wall-clock timing,
flamegraph or surrogate comparison. No dev/main changes.

This experiment can rule out claims like 'every difference in final vars
was due to EE', by showing the native stage transitions explicitly.


## Completed original GPMC native trace: actual EE attribution

**CI SUCCESS**: [Actions #41839854976](https://github.com/PhysicsQoo/QuPRS/actions/runs/41839854976), [raw source and trace artifact #13327644747](https://github.com/PhysicsQoo/QuPRS/actions/runs/41839854976/artifacts/13327644747), measurement SHA `2e79057abcf6777750ffaac5a17e9c5275b6d62e`, pinned GPMC native binary SHA256 `b4169bce97c995accfca5ef2246d7283af0ded3370391dec7cd852eb3fcb67ce`. Scientific complex printed count screens pass for both cases and EE configurations under the original 1e-12 count scale criterion (not certified arithmetic).

| Case | Native step | Vars/clauses BEFORE | Vars/clauses AFTER | Main contribution |
| --- | --- | --- | --- | --- |
| QAOA7 genuine NEQ | `SAT_FLE` | 470/822 | 469/822 | −1 var |
| QAOA7 | first `EquivEl` | 469/822 | **316/516** | **−153 vars, −306 clauses** |
| QAOA7 | `DefVE` and second `EquivEl` | 316/516 | 316/516 | **0 additional** |
| QFT16 EQ | `SAT_FLE` | 486/1143 | 485/1143 | −1 var |
| QFT16 | first `EquivEl` | 485/1143 | **383/939** | **−102 vars, −204 clauses** |
| QFT16 | `DefVE` and second `EquivEl` | 383/939 | 383/939 | **0 additional** |

With `-no-pp_ee`, the native `EquivEl` stage does not run; GPMC reaches 469/822 (QAOA7) and 485/1143 (QFT16), and `DefVE` does not recover the missing structural reduction. The exact **2 deleted clauses per eliminated variable** in the EquivEl stage is consistent with paired binary implication patterns, but is not itself a one-to-one proof that every removed clause is one direction of a literal equivalence; inspect actual input/residual clauses before asserting that stronger claim.

The stage trace proves *where* the reduction happened without instrumenting solver source or measuring its elapsed time. It does not isolate EE's own CPU time; the prior official CodSpeed [#41837297080](https://github.com/PhysicsQoo/QuPRS/actions/runs/41837297080) only gives its **solver-inclusive net** effect (QAOA7 ~+1.2%, QFT16 ~−28.8%, hosted observation). **Do not infer a formal GPMC-vs-d4 speed ratio from these source-only counters.**

The phase-weight / projected semantics are preserved up to the prior count screen only; a source-to-residual weight mapping can still be audited more strongly. Proposed next step: compare exact canonicalized residual Boolean clause multiset and literal-weight mapping against d4 BiPe, rather than treating matching *counts* as matching residual formulas. Ganak remains separately gated in QOO-98.

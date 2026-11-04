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

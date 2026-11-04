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

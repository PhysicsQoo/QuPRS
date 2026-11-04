# QOO-157 P1 — pinned d4/BiPe native stage counters, no performance measurement

Prior P0 successful [CodSpeed #41846122379](https://github.com/PhysicsQoo/QuPRS/actions/runs/41846122379) showed d4 within-solver prepared CNF saves **6–14%** after the externally shared SCC quotient, but remains far behind GPMC; performance reason still incomplete.

The next P1 test uses pinned d4 `be15f91` + BiPe `v1.0.0` pinned to exact commit `219cc2a5`, two original QAOA7 and QFT16 source CNFs and four relevant d4 options: auto/default, manual-sharp, no-vivif, no-probing. Archived [canonical residual identity artifact #13329836269](https://github.com/PhysicsQoo/QuPRS/actions/runs/41841100007/artifacts/13329836269) establishes byte-for-byte *same post-BiPe CNF* for each circuit. Run each option with `--preproc.verbosity=3` for built-in `c [STATS]` telemetry, and an environment-gated source-only residual dump. Enforce exact original source SHA, original d4-38 printed complex WMC count and canonical + raw residual SHA from the prior artifact. Do not run d4 upstream on a changed precision or different CNF.

Available built-in counters: before/after vars, clauses, literals, projected, estimated primal degeneracy/treewidth, bipartition input set, gate AND/XOR/EQUIV, gate/resolution elimination, BVA added vars/removed clauses.

**Critical**: BiPe v1.0.0 calculates additional before/after graph degeneracy at verbosity >=3; the `c [STATS] t_total` internal clock is neither the total subprocess nor a fixed-overhead performance instrument. The science parser **discards t_total** by contract. This branch job runs no CodSpeed, and no relative performance conclusions may be inferred from it. Later stage-specific CodSpeed designs require a fixed runner and ABBA/BAAB; no generic run time performance log. Unknown work inside native stages remains a research gap.

Do not edit upstream d4/BiPe, production QuPRS defaults, dev/main or regular CI. This dedicated workflow is triggered only for its own isolated files.

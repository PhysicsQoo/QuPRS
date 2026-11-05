# QOO-157 P9 — pre-BiPe structural source audit

[GitHub Actions #41946719250 — SUCCESS](https://github.com/PhysicsQoo/QuPRS/actions/runs/41946719250), measured HEAD `866ae87d8081d799d3faef0bfd245f71f2642753`; [artifact 13379320903](https://github.com/PhysicsQoo/QuPRS/actions/runs/41946719250/artifacts/13379320903). Original four weighted CNF bytes from artifact `13317939531` passed exact SHA checks. Source-only Python, no native solver builds, no CodSpeed timing.

| Original CNF | Variables | Clauses | Primal graph degeneracy | Text-weight protected variables |
|---|---:|---:|---:|---:|
| Grover4 EQ |372|698|4|256|
| QAOA7 NEQ |470|823|2|319|
| QPE exact8 EQ |250|495|4|178|
| QFT16 EQ |486|1144|11|400|

Matches historical BiPe input degeneracy k=2/11 for QAOA7/QFT16. Degeneracy is not exact treewidth; sample cannot establish a generalizable conditional BiPe policy. QAOA9/11 and QFT20/22 and matching EQ/NEQ input-source-science holdouts are still missing. Production policy is **not approved**; proposed cutoffs are post-hoc. P9 scope / Rust design: [P9 report](P9_FAMILY_AWARE_BIPE_AND_HOLDOUT.md) and [Rust WMC study](QUprs_RUST_WMC_SOLVER_STUDY.md).

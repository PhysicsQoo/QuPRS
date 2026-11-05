# QuPRS-native Rust complex WMC solver — evidence-led research architecture (2026-11-05)

**Decision: worthwhile as a bounded research prototype / long-term optional backend, NOT an immediate GPMC replacement or v0.14.0 blocker.** This is an algorithmic specification, not a performance promise or an implementation PR. Reuse existing QOO-157 solver evidence; do not fork/copy upstream solver code or introduce another parallel release roadmap.

## 1. Existing empirical data that are genuinely transferable

| Component | Source-controlled evidence | Correct interpretation for a Rust prototype |
| --- | --- | --- |
| Cached component decomposition | [d4 cache on/off official CodSpeed #41938239985](https://github.com/PhysicsQoo/QuPRS/actions/runs/41938239985), native 8/8 count science / six timed identities. Disabling d4 cache increased QAOA7 auto/none observed WallTime ~97×/~167× and QFT16 auto ~2.72×; search decisions increased by far more. | **Implement component memoization from the first WMC MVP**. A naive depth-first weighted-DPLL baseline without caching is intentionally a science oracle for small cases, not a scalable target. No assertion Rust gets these ratios. |
| Tree-decomposition-aware decision ordering | [GPMC TD source-native counts #41930925045](https://github.com/PhysicsQoo/QuPRS/actions/runs/41930925045) 8/8. Grover4 TD off/on cache-eligible queries 786,766/8,889; QFT16 221,791/200,343. | **Branching/decomposition strongly affects work**, but query-count ratio ≠ time ratio. Evaluate TD/graph heuristics by real source CNF + official CodSpeed; keep expensive TD optional. |
| Cache-rate denominator semantics | P3 GPMC `Cache lookup` excludes empty hash buckets; independently instrumented eligible hit ratios were 66.7–78.9%, not original occupied-bucket ~99%. d4 `negative hit` denotes **miss**, not successful hit. | Native Rust counters must report **all eligible requests, hits, misses, evictions, actual stored nodes and byte footprint**, each with an unambiguous denominator. Build unit/property tests on every identity. |
| Capacity and memory | [GPMC 16/64 MiB source & CodSpeed #41932161536](https://github.com/PhysicsQoo/QuPRS/actions/runs/41932161536): Grover TD-off eviction 12 events / +11.8% decisions / +11.5% hosted median; Grover TD-on no eviction and stable time. 64/4000 MiB same native work for four source controls. | Budget cache by **allocated bytes**, observe root/index fixed overhead, bounded eviction and memory safety. Do not equate small limit with cache disabled. Memory policy can dominate latency. |
| Weight/projection safety in preprocessing | [P7 12/12 residual weight/projection/protected SHA science #41942959399](https://github.com/PhysicsQoo/QuPRS/actions/runs/41942959399). Same clause count can hide distinct actual residual content (QAOA7 166 deleted/166 added, QFT16 350/350 after disabling equivalence substitution), while weight/projection/protected hashes remained equal in those audited variants. | Rust rewrite MUST carry an invertible/validated `TransformationWitness` and preserve complex literal weights and projected/model-counting semantics. Canonical clause hash is a *representation identity*, not equivalence proof. |
| BiPe / family strategy | [P8 same-residual paired-path CodSpeed #41944225225](https://github.com/PhysicsQoo/QuPRS/actions/runs/41944225225). QAOA7 default/manual/no-vivif share byte-identical weighted residual, but preproc-path hosted medians 71.425/26.448/56.397ms. [P1 BiPe stats #41847739344](https://github.com/PhysicsQoo/QuPRS/actions/runs/41847739344) k proxy QAOA7 2→2, QFT16 11→8. | Treat preprocessing as a **budgeted choice**, not an always-on graph rewrite. QAOA7/QFT16 are two training anecdotes only; independent same-family, EQ/NEQ holdouts precede automated policy. P9 criteria in [separate report](P9_FAMILY_AWARE_BIPE_AND_HOLDOUT.md). |
| SAT warm-start | [P6 16/16 native / 10/10 hosted CodSpeed #41941617634](https://github.com/PhysicsQoo/QuPRS/actions/runs/41941617634): identical component search counters, median signed changes ~1–1.8%, mixed. | **Do not prioritize replicating d4's 29×11 warmStart**. This setting is not a proven major cross-solver cause and may be SAT-engine-specific. |

All cited **timed** observations were produced by official CodSpeed but on GitHub-hosted non-Macro runners, so none alone establishes production-level statistically significant speed. Never compare absolute times across such runs to rank a native Rust prototype.

## 2. Proposed separation of concerns

```text
(existing Rust RR/Path-sum)
   ↓
WeightedCnfIr { clause_arena, var_map, weights, projection,
                protected_lits, source_sha, transform_witness }
   ↓
structural_probe { primal_components, degeneracy, cheap equiv opportunities }
   ↓
preproc_choice { skip, cheap-simplify, guarded-full }  [default conservative]
   ↓
count_components { SAT oracle, component search/branching, cache, memory budget }
   ↓
ComplexWmcValue + PrecisionProvenance + SearchProvenance + ResourceProvenance
   ↓
(existing QuPRS WMC verdict / phase / approximate_distance policy)
```

- **SAT search subengine**: start with a documented, independently testable assumption-capable SAT interface; a pure Rust candidate is [varisat](https://docs.rs/varisat/latest/varisat/), CDCL with assumptions and proof APIs. It is a *candidate*, not a validated WMC engine and cannot simply be invoked as a black-box SAT solver for every weighted branch without a cost model. Isolate `SatOracle` so future comparison with a C-backed engine or a specialized rust one is possible.
- **Component cache and decomposition**: use exact residual formula identity under propagated assignments, retained projection context and variable/literal-weight provenance, with stable variable remapping and cache allocation metrics. For **scalar result caching**, cache keys must also include the effective weight version / semiring precision (or be invalidated). Reusing a cached *compiled structure* while updating weights can be safe when the representation and evaluation semantics explicitly support it; it is a later optional capability, not an assumed routine QuPRS workload.
- **Complex arithmetic**: fast `f64` may be used only as an *internally verified candidate* when numeric conditioning and requested tolerances make it safe. Near cancellation, zero WMC, small global phase and EQ/NEQ boundaries require well-defined precision escalation and warnings. [`rug`](https://docs.rs/crate/rug/latest) supports GMP/MPFR/MPC high-precision arithmetic from Rust (not pure-Rust arithmetic); it is a viable optional high-precision implementation dependency subject to build, portability, license and actual performance qualification. Preserve QuPRS's independent RR tolerance, WMC phase tolerance and approximate projective-distance contract rather than silently defining new solver verdicts.
- **Projection**: distinguish ordinary weighted model counting from projected weighted model counting. The existential/projection semantics must be explicit and tested; free-variable factors `w(v)+w(¬v)` must be treated according to the **actual semiring and scope**. With complex weights, destructive cancellation means weight magnitude is not a monotonic count bound, and `|WMC|=0` does not itself certify an internal algorithm was accurate.
- **Preprocessing**: first exact unit propagation, safe literal equivalence/SCC detection and witness-preserving substitution, then optionally more expensive branching/decomposition assistance. Complex weight/projection constraints can invalidate seemingly innocent SAT-equivalent transformations; every rewrite must pass WMC and projection provenance tests. Do not directly port BiPe's complete algorithm.
- **Knowledge compilation**: storing a reusable decision-DNNF/SDD may be useful **only** if real QuPRS workloads repeatedly solve **the same fixed CNF with changed literal weights or assumptions**; currently this reuse is a hypothesis, not a core product need. [`decdnnf_rs`](https://docs.rs/crate/decdnnf_rs/latest) can work with already compiled d4-style decision-DNNF, but is not by itself a replacement for the search/compiler and does not certify complex weighted QuPRS semantics. Check licensing before adoption.
- **Robustness**: every native interface supports explicit `timeout`, `max_memory_bytes`, cancellation, partial-precision provenance and fail-closed error/unknown handling. Integrate with existing Rust CLI work QOO-156 and cross-backend conformance QOO-8; instrumented diagnostics must not contaminate CodSpeed timing.

## 3. Engineering roadmap, science and admission gates

**Stage R0 — contract/spec + tiny exact reference:** No new production dependency; define `WeightedCnfIr`, `SolverOutcome`, `PrecisionProvenance`, `ComponentCacheCounters`, `TransformationWitness`. Roundtrip and exhaustive tiny-CNF complex WMC / known protected-variable/projected fixtures compared with Python and pinned GPMC/d4, including zero, cancellation, equivalent/NEQ. Reuse QOO-152 phase-literal provenance, QOO-103 parity and QOO-136 tolerance contracts.

**Stage R1 — minimal component-WMC prototype:** weighted DPLL, unit propagation, decomposition by current residual primal graph, scalar cache keyed rigorously. Precise cache misses including empty-bucket, eviction and byte accounting; deterministic canonical IR. For initial scientific correctness, no complicated preproc, no TD, no speculative f64 verdict. All source fixtures record circuit/QASM/CNF hash and independent WMC reference.

**Stage R2 — guided branching + conservative preprocessing:** add cheap structural heuristics, optionally TD/variable scoring, and witness-preserving safe equivalence substitution; independently benchmark **same original CNF** with feature computation overhead included. Preserve no-preproc and GPMC as controls; do not infer speed from native counters.

**Stage R3 — precision/reuse/architecture qualification:** adaptive MPFR escalation and complex error controls with QOO-105 post-release owner; optional reusable compiled-DNNF if repeated-weight workloads are proven frequent; bounded cache memory, lifecycle and cancellation stress (QOO-156). Cross-platform support and binary distribution are distinct tasks, not assumed from a Linux-only pilot.

**Release-orientation gate:** For any prototype, require 100% scientific conformance on covered EQ/NEQ and near-cancellation cases and official CodSpeed v5 on the same runner/source with ABBA–BAAB; track end-to-end QuPRS RR+CNF+WMC as well as solver-inclusive prepared-CNF, P95/tails, peak RSS, timeout and CI cost. Reject/revise unless actual nontrivial workloads gain enough without unacceptable worst-case regressions; retain GPMC default otherwise. This is **post-release discovery**, not a v0.14.0 blocker.

## 4. External technical background

- [2026 Model Counting Competitions 2021–2023 survey](https://doi.org/10.1016/j.artint.2026.104605): documents GPMC's component caching and integration with a Glucose-style SAT core, and explains why caching, branching and knowledge compilation have different strengths.
- [Solving Projected Model Counting by Utilizing Treewidth and its Limits](https://www.sciencedirect.com/science/article/pii/S0004370222001503): exact projected-model-counting treewidth research, not a promise for QuPRS complex weighted inputs.
- [Engineering an Efficient Probabilistic Exact Model Counter](https://link.springer.com/chapter/10.1007/978-3-031-98682-6_5): supporting broader component-caching practice; QuPRS complex weights require additional scientific gates.
- [Rust varisat](https://docs.rs/varisat/latest/varisat/), [rug](https://docs.rs/crate/rug/latest) and [decdnnf-rs](https://docs.rs/crate/decdnnf_rs/latest) are **candidate libraries to evaluate**, not a finalized dependency selection.

Existing Linear owners to keep aligned: [QOO-157](https://linear.app/qoogohome/issue/QOO-157), [QOO-7](https://linear.app/qoogohome/issue/QOO-7), [QOO-8](https://linear.app/qoogohome/issue/QOO-8), [QOO-105](https://linear.app/qoogohome/issue/QOO-105), [QOO-156](https://linear.app/qoogohome/issue/QOO-156), [QOO-152](https://linear.app/qoogohome/issue/QOO-152). No duplicate new issue or production PR.

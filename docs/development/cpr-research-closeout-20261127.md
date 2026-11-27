# CPR research closeout — 2026-11-27

SCOPED EXPERIMENTAL ADMISSION PASS; STABLE PRODUCT ADMISSION HOLD.
Evidence revision b6b825a234e418dacf3b88fa6e1b19e43b787500, tree 60d260df83ace7d10a1eb85739ca5f1406fd3497. This synthesis does not run a new experiment.

## Algorithm

CPR is a bounded cost-aware representation policy for strict numeric Hybrid/Difference/GPMC, independent of Conditional RR. Consume the original Myers gate stream once from identity; trigger inverse-HH input/output lifting on growth estimates; use bounded original RR; consider terminal legal half-phase integrator extraction; select Raw or All extracted constraints by the frozen structural router; reuse native WMC/classification, with at most one solver call. RR-decisive residuals may bypass WMC. Reject incomplete construction, untracked Elim and approximation rather than produce a partial verdict.

For n qubits, h hidden bits, each extracted z independent of output and previous guards, with pure half-phase z*g/2, sums to 2 times the indicator g=0. For m legal sequential extractions, C_raw=2^m C_ext. Use the unscaled count with denominator 2^((2n+h-2m)/2), not 2^((2n+h-m)/2); never restore the factor twice. Preserve the original final_ps. This assumes the source residual is correct and no untracked scale changes occurred; it is not a full implementation proof.

Frozen limits: 4096 terms, 32 lift pairs, 16 saturation iterations/8 local trials, 15 s build ceiling; graph 4096 vertices/65536 clauses/250000 edges/250 ms analysis deadline, bounded by request deadline. Choose Extracted only when both profiles complete, heuristic width does not increase, and weighted variable count and weighted degree sum strictly decrease. Otherwise Raw. These are heuristics; cooperative time checks do not bound individual native operations.

## Evidence index

| Gate | CI | Scoped result |
| --- | --- | --- |
| C1/C2 | [45961711761](https://github.com/PhysicsQoo/QuPRS/actions/runs/45961711761), [45962280960](https://github.com/PhysicsQoo/QuPRS/actions/runs/45962280960) | Structure and router PASS; not universal speedup |
| N1–N5 | [45999130623](https://github.com/PhysicsQoo/QuPRS/actions/runs/45999130623), [46001208649](https://github.com/PhysicsQoo/QuPRS/actions/runs/46001208649), [46001663734](https://github.com/PhysicsQoo/QuPRS/actions/runs/46001663734), [46002676358](https://github.com/PhysicsQoo/QuPRS/actions/runs/46002676358), [46005149022](https://github.com/PhysicsQoo/QuPRS/actions/runs/46005149022) | Exact local receipts, reachable external HH defect and guard, bounded Elim audit, heavy paired regression |
| I1a/I1b | [46008624589](https://github.com/PhysicsQoo/QuPRS/actions/runs/46008624589), [46011072991](https://github.com/PhysicsQoo/QuPRS/actions/runs/46011072991) | Shared native handoff and builder |
| I2a | [46011786054](https://github.com/PhysicsQoo/QuPRS/actions/runs/46011786054) | 6/6 raw/extracted verdict pairs, 12 native solves |
| I2b | [46012781748](https://github.com/PhysicsQoo/QuPRS/actions/runs/46012781748) | 5/5 native shape, router and independent source/count parity; max normalized count delta ~1.19e-37 |
| I3a | [46014598873](https://github.com/PhysicsQoo/QuPRS/actions/runs/46014598873) | 120/120 ordinary-path source parity, 12/12 time/RSS screens; [CodSpeed](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6b0991b440dceb70df55aa36) vs [main](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6b03dbe363385668ede6de1a), displayed core values within 5%, four syscall warnings |
| I3b | [46015941510](https://github.com/PhysicsQoo/QuPRS/actions/runs/46015941510), job 140562947757 | CPR 80/80, main 60/80, independent source parity 140/140; zero errors/drift/perf blocks |

## I3b matched native evaluation

Main b398f07d6845efc23540549ccbfec717c27b1722 vs candidate b6b825a234e418dacf3b88fa6e1b19e43b787500. Ubuntu 24.04, Rust 1.100.0, release locked, same GPMC binary/source bytes/request parameters: Hybrid/Difference, strict RR, 90 digits, phase/distance 1e-8, 27 s request, 35 s watchdog, 3 GiB address cap. CPR additionally retains build/term/lift ceilings. Native dynamic weights, not historical fixed 256-bit/12s solver-only configuration. 80 paired/160 fresh processes, AB/BA.

| Easy coordinate | Main median ms | CPR median ms | Paired delta us | Paired RSS delta KiB |
| --- | ---: | ---: | ---: | ---: |
| GHZ32 EQ | 0.148743 | 0.160570 | 8.4675 | -26 |
| GHZ32 NEQ | 11.995771 | 10.801580 | -1193.2745 | 38 |
| QPE8 EQ | 12.754372 | 11.623725 | -1130.087 | -70 |
| QPE8 NEQ | 36.849957 | 35.499135 | -1350.740 | -12 |
| VQE4 EQ | 23.489342 | 22.370528 | -1127.0965 | 0 |
| VQE4 NEQ | 23.460299 | 22.349248 | -1109.5615 | 10 |

Easy 60/60 completed per arm; all 12 screens pass existing max(5%,25 us), max(5%,512 KiB). Outer time resolution-limited. GHZ32 EQ overhead is not zero.

| Heavy coordinate | Main completed | CPR completed | CPR median s | CPR median peak RSS KiB |
| --- | ---: | ---: | ---: | ---: |
| QWalk5 EQ | 0/4 | 4/4 | 6.257755567 | 96840 |
| QWalk5 NEQ | 0/4 | 4/4 | 7.392246210 | 112516 |
| Grover6 EQ | 0/4 | 4/4 | 5.421270594 | 128152 |
| Wstate16 EQ | 0/4 | 4/4 | 4.152683128 | 183554 |
| Wstate16 NEQ | 0/4 | 4/4 | 4.876325404 | 196076 |

Main 12 outer watchdog exit 124, 8 native Timeout exit 0. All 20 CPR heavy rows invoked solver: 12 EquivalentUpToGlobalPhase, 8 NotEquivalent. No heavy completed matched pair; no numeric speedup claim. Five heavy coordinates are known design cases, not independent family generalization. I3b source parity is projective verdict only; I2b supplies complex count evidence. Main vs branch differs in 13 source/lock files (+962/-404 per log); whole-pipeline comparison, not isolated attribution.

I3b artifact ZIP digest from log: 66fc8efde944a288e79c3037708c5cbadc7941b50ff10e5e48080996610874ca (not independently rehashed). Reproduction: checkout exact evidence revision, consult .github/workflows/qasm-source-semantics-experiment.yml job cpr-native-i3b and rust/research/cpr_native_i3b.py; retain full trial, paired, source and SHA256SUMS receipts. Use pinned main and recorded GPMC/oracle environment, not latest tag. This document adds no timing samples.

## Academic positioning and negative evidence

Targeted abstract-level prior-art check: [Amy 2018](https://arxiv.org/abs/1805.06908) establishes path-sum verification/rewrite framework; [Vilmart 2024](https://lmcs.episciences.org/13200) dyadic SOP rewriting/completeness; [Amy et al. 2023](https://arxiv.org/abs/2306.16369) unbalanced SOP/local summation/equational theories; [CAV 2024 model counting](https://arxiv.org/abs/2403.18813) WMC equivalence; [QuPRS TACAS 2026](https://doi.org/10.1007/978-3-032-22749-2_21) hybrid baseline. [IJCAI 2016 definability preprocessing](https://ijcai.org/proceedings/2016/112) and [WMC Without Parameter Variables](https://atiro.turing.ac.uk/esploro/outputs/conferencePaper/Weighted-Model-Counting-Without-Parameter-Variables/9920164109548) establish related encoding/preprocessing research. Do not claim first introduction/elimination of variables, inverse-HH identity, scalar transport, graph width, WMC, or completeness. Candidate contribution: coordination of bounded representation growth, original RR, exact cancellation-derived constraints and one native WMC solve, with measured completion gains. Full rule-level subsumption and publication novelty remain OPEN.

Retain A4c Grover6 NEQ 0/9 complete; QNN12 no proven gain; online HH pivot/frontier NO-GO; no positive adaptive holdout generalization; Wstate weak extraction-only benefit. No new heuristics, threshold tuning, solver work, rerun-to-pass, or scope expansion. C1/C2/C3 selected-cohort and I1–I3 scoped PASS; C3c full attribution/flamegraph limited, C4 full novelty OPEN, SourceTrust BLOCKED.

## Product integration review (HOLD)

Do not wholesale merge the long-lived research branch. Port minimal relevant changes onto a clean integration branch from then-current main, including HH internal-pivot guard and its reachable regression witness. Preserve ordinary default API and explicit opt-in domain. Existing experimental entry duplicates request validation and maps BuildStop to anyhow error; stable semantics for deadline/cap/unsupported/untracked normalization must be explicit. No automatic fallback or partial verdict. I2b libtest worker currently unwraps CRR_SOURCE/CRR_TARGET; unfiltered libtest suite has not been demonstrated, so isolate worker or provide test-owned fixture before production. Native GPMC tests need controlled provisioning. Preserve historical receipts while avoiding active duplicate policy implementations. Require focused diff, full existing tests, candidate-head matched regression if runtime changes, source gates and independent release review. No stable/Python admission, no default enablement, no merge/release authorization. QOO-275 remains in progress for these bounded gates and C4 review.

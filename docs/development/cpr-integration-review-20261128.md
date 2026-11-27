# CPR integration review — G5 pre-admission

Status: SCOPED G1–G4 PASS; G5a permanent test-profile candidate pending; STABLE PRODUCT HOLD.
This is not a merge/release authorization.

## Exact evidence and scope

Main and dev observed at b398f07d6845efc23540549ccbfec717c27b1722 (tree 1dc21015f0f4f69f057c4685b886b686d82b882d).
G4b candidate c02a9b2f750099c7b1a493a626aa983fbceeb605 (tree ec8fc83dd6237b068d4dc95d7b8ebe369c2ed9b1). G4a/G4b changed harness/workflow only after G3; exact source equality checked.

| Gate | Receipt | Result |
| --- | --- | --- |
| G1 | [46021176784](https://github.com/PhysicsQoo/QuPRS/actions/runs/46021176784) | HH guard and reachable witness PASS |
| G2a | [46022061898](https://github.com/PhysicsQoo/QuPRS/actions/runs/46022061898) | Private builder/handoff and 6 raw/extracted parity PASS |
| G2b | [46023043998](https://github.com/PhysicsQoo/QuPRS/actions/runs/46023043998) | Native routed count/shape and independent source 5/5 PASS |
| G3 | [46025768010](https://github.com/PhysicsQoo/QuPRS/actions/runs/46025768010) | Checked optimized 226, default release 191, opt-in release 193 pass; zero fails; two ignored in each |
| G4a | [46027205209](https://github.com/PhysicsQoo/QuPRS/actions/runs/46027205209) | CPR80/80 vs main60/80; heavy20/20 vs0/20; 140/140 source; all 12 easy paired time/RSS gates |
| G4b | [46029861791](https://github.com/PhysicsQoo/QuPRS/actions/runs/46029861791) | ordinary default API120/120 complete, 120/120 independent source, 12/12 time/RSS gates, zero public contract drift/errors |

G4b jobs 140610632207 and 140610632661. Native paired delta us / RSS KiB: GHZ EQ +4.7715/+16, NEQ -28.023/-10; QPE EQ +19.8805/+36, NEQ +60.694/+14; VQE EQ -18.856/+6, NEQ +21.973/-2. Outer wall resolution-limited, not a zero-overhead claim. Artifacts 15214740033 sha256:9647b349552c2cfcc7cffc2ce31ed62a3ba2987ddf48e162323db05ecf324e3d and 15213433310 sha256:211707fdb0812da4fe3ccdfa33494a68a67946e08d10d183b8296e1aef220d91 from logs/metadata, not independently rehashed.

[CodSpeed actual comparison](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/compare/6b03dbe363385668ede6de1a..6b09a994338aef5ba4f3c2d1). Exact Simulation CPU time changes (% candidate/main-1) via benchmark result API: Elim -2.672, HH direct -0.443, HH pipeline +0.097, non-Clifford +1.109, omega +0.819, q261 graphstate16 +3.446, QPE8 +2.200, QFT16 +1.333, GHZ32 +1.081, VQE4 +2.376. Ten scoped screens within 5%; all ten have no per-benchmark issue. Candidate measured 36 core benchmarks, not all carried-over repository tests. CPU changed EPYC 7763 to 9V45, simulation cache model confound; four other candidate core syscall warnings. No causality or exact zero-regression claim. No threshold breach requiring flamegraph. Native independent matched gate is primary admission evidence.

## Permanent integration blocker

The original dev-fast command runs cargo test --locked --manifest-path rust/Cargo.toml -p quprs -p QuPRS_cli. CLI fault-injection requires debug_assertions; initial release CI failed 12 tests [46024103281](https://github.com/PhysicsQoo/QuPRS/actions/runs/46024103281). Unoptimized Debug fixed CLI22/22 but CPR source-locked heavy construction hit its 15s deadline [46024691820](https://github.com/PhysicsQoo/QuPRS/actions/runs/46024691820). G3 explicitly set optimized checked test profile in branch-only environment, not a durable workspace setting.

G5a proposes only [profile.test] opt-level=3/debug-assertions=true/overflow-checks=true in rust/Cargo.toml, reproducing G3 settings for the existing cargo test command without environment overrides. No [profile.dev] or [profile.release] change, no gate/test skip/deadline relaxation. Workspace-wide test profile change is a review decision, not a production runtime change; optimized debugging and cold compile times can differ, so it requires maintainer review. Branch-only CI must prove the manifest configuration; retain all G3 checks. This is not evidence for unoptimized Debug or cross-platform completeness. Do not add a permanent workflow for CPR; remove temporary integration workflow before merge and retain reproduction pointers to exact commits/runs. G5b review must decide test-profile acceptance, existing CI compatibility, evidence retention, public experimental-only contract and rollback.

## Admission boundary

Only consider non-default native experimental-cpr opt-in with strict Hybrid/Difference/GPMC, numeric inputs, explicit stop/error and no partial verdict/fallback. No Python/default/WASM/stable admission. Preserve source-locked negative evidence and bounded claims from research closeout (Grover6 NEQ 0/9, QNN12 no proven gain, no positive adaptive holdout generalization). SourceTrust remains BLOCKED (not complete source-level formal proof), C4 prior-art rule-level novelty OPEN. No full implementation soundness/completeness proof or independent family-generalization claim. Stable, default, release and merge HOLD; human review required. No main/dev change.

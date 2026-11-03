# Exact Bra-CX specialization: QFT16 / QPE / Decimal / Mixed evidence

> **Integration status, 2026-11-03:** The exact guarded-XOR / direct Bra-CX verifier changes described below were subsequently merged through [PR #131](https://github.com/PhysicsQoo/QuPRS/pull/131) into `dev@a4c7b12652b3c59c086f5d408a95e004df570bad`. This file remains the **historical source-matched experimental evidence record**. Sentences below saying that the formal PR was Draft/untouched/not yet integrated describe the **then-current experimental gate**, not today's branch status. The Native CPU gains are established for the specified same-source comparison; the recorded solver-inclusive QFT16 WallTime result remains **PERFORMANCE_INCONCLUSIVE** because observed drift exceeds its gain. Future benchmark admission and cross-instrument joins follow the [active v3 plan](https://github.com/PhysicsQoo/QuPRS/blob/experiment/qoo160-qasm261-codspeed-selection/docs/development/codspeed-v3-plan.md).

Date: 2026-11-03 (Asia/Taipei). This document is an **isolated
experiment record**, not a production merge approval.

## Immutable comparison

- Previous guarded-XOR baseline: `1ebe7442d5004a522a915f18e163b1c78da648ab`
- Exact Bra-CX experimental candidate: `2c6f68a578bb84dc916a5c871e0bcd9e1f0f6132`
- GitHub Actions science and official CodSpeed native CI:
  <https://github.com/PhysicsQoo/QuPRS/actions/runs/41576581098>
  **ALL TWO JOBS SUCCESS**
- Source-matched, same-run official CodSpeed Simulation:
  <https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6ae9605d381332605c0dbac7>
- Both copied A/B benchmark sources are byte-identical. The QFT16 and
  QPE-exact8 original/transpiled QASM input bytes are byte-identical.
  Both use the same Rust toolchain, `VerificationStrategy::Proportional`,
  `rr_tolerance=1e-10`, and initial/final RR procedure. Measured CPU scope
  excludes input parse/clone and external WMC subprocesses.
- Formal PR #131 `2e3c5f1b160324445240db8ee204988c5d1aed70`
  is untouched and Draft.

## Scientific equivalence gates

The experiment enables the opt-out Rust `bra-cx-direct` feature on the
isolated branch only. The old path also compiles with
`--no-default-features --features high-precision-gpmc`.

The exact Bra-CX phase algebra uses
`R*x_t -> R*x_t + R*x_c - 2R*x_t*x_c`. If `R` contains `x_c`,
Boolean idempotence simplifies this to `R - R*x_t`. Pure half-cycle
coefficients omit the `-2` term *exactly* modulo 1, never by numerical
tolerance. Unaffected sources remain unchanged; **all** affected source
terms are removed before destination insertion, preserving collisions.
BooleanState `F` uses its original generic transformation.

All three focused Rust Bra-CX oracle tests pass, including canonical Boolean
collisions, control overlap, Clifford, rational, exact QASM decimal-radian,
symbolic and mixed coefficients, zero/one affected terms, and full `P/F`
semantics.

| Oracle | Exact canonical digest (Base = HEAD) | Gate |
|---|---|---|
| QFT16 final P/F/path variables/RR statistics | `058fa6f8dc6fa1c64173b8f6e37e720bdf3e54e734efe1becf9d9f972ed4721f` | PASS |
| QPE-exact8 final P/F/path variables/RR statistics | `0451e8b289476b3bb6200910f2f9f203cdb65fa20e45fbcc82e5d52a6ed2ffe8` | PASS |
| Exact Decimal Bra-CX `P/F` | `85d8abd1ad2b9d9cc0d2a33f9cac7c801c670dc2b57240d2f5902c30bb4e5406` | PASS |
| Exact Mixed Bra-CX `P/F` | `a1ca9279c0bcc8c4c936a5adacfc5ebcdbb4c42b4d901d1c40058e4185f5a252` | PASS |

## Official CodSpeed Simulation native CPU model

Negative change means lower modeled CPU time, HEAD vs the
**previous guarded-XOR version**, not vs formal PR #131.

| Source-identical benchmark | Previous Base (ms) | Direct Bra-CX HEAD (ms) | CPU change | Speedup |
|---|---:|---:|---:|---:|
| QFT16 complete native Miter + RR | 45.801595 | 30.641331 | **-33.0999%** | **1.4948x** |
| QPE-exact8 complete native Miter + RR | 4.972925 | 4.624761 | **-7.0012%** | 1.0753x |
| Exact Decimal Bra-CX focused case | 1.198795 | 1.118058 | **-6.7349%** | 1.0722x |
| Exact Mixed Bra-CX focused case | 0.296769 | 0.229207 | **-22.7660%** | 1.2948x |

All eight individual Simulation measurements were available with no CodSpeed
benchmark issues. On QFT16, instruction penalty fell 32.47%, cache miss
penalty fell 37.01%, and memory-access penalty rose 2.10% from a small
absolute base; the total modeled CPU improvement is 33.10%.

### Same-run differential QFT16 callgraph

The following are **inclusive, overlapping** native CPU subtree costs;
do not add them.

| Subtree | Prior guarded-XOR | Direct Bra-CX |
|---|---:|---:|
| `PathSum::apply_cx` | 36.4 ms (79.54%) | 21.2 ms (69.16%) |
| Bra-CX phase substitution | general `substitute_var_with_poly` ~33.5 ms (73.16%) | specialized `substitute_bra_cx` ~18.2 ms (59.55%) |
| All-source `expand_xor_to_arithmetic` | 8.1 ms (17.70%) | 1.1 ms (3.72%) |
| All-source `PhasePolynomial::add_term` | 9.0 ms (19.57%) | 7.6 ms (24.93%) |

Remaining native hot spots are phase-key scan/clone, term insertion/merge and
exact coefficient arithmetic. An entirely new PhasePolynomial container is
**not yet justified** by this experiment alone.

## Scope and unresolved admission

- **PASS**: direct Bra-CX semantic parity, pinned QFT16/QPE8 real-source
  parity, Decimal/Mixed precision preservation, native Simulation
  performance in four paired same-run cases.
- **NOT YET CERTIFIED**: incremental Solver-inclusive GPMC/Ganak WallTime
  gain, larger QFT/QPE workload representativeness, whole QuPRS production
  speedup, formal Python/Rust cross-surface release gates.
- Existing historical solver-inclusive ABBA results for the prior candidate
  were inconclusive and must not be presented as direct Bra-CX end-to-end
  evidence.
- The dedicated benchmarks are experimental identities and do not replace
  or silently retire any legacy CodSpeed benchmark identifiers.
- Gate for eventual formal integration: source-pinned solver-inclusive
  CodSpeed verdict consistency and no material walltime regression. Keep
  formal PR #131 untouched until that evidence exists.

Markdown-only updates to this report do **not** trigger expensive workflows.

## Incremental Solver-inclusive CodSpeed — 2026-11-03

**Full CI succeeded:** [GitHub Actions 41578375935](https://github.com/PhysicsQoo/QuPRS/actions/runs/41578375935), both jobs PASS, 36/36 benchmark identities. [Official CodSpeed Run 6ae9657e](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6ae9657e381332605c0dbb1d) completed. CodSpeed reports its standard **non-Macro Runner WallTime reliability warning on all 36 identities**.

Source-pinned comparison:
- Baseline: prior guarded-XOR `1ebe7442d5004a522a915f18e163b1c78da648ab`
- Exact direct Bra-CX: native-certified source `2c6f68a578bb84dc916a5c871e0bcd9e1f0f6132`
- Final CI HEAD: `d5ca40348ba9a561a447632ca0fdbf417e8a56d2`. The source guard confirms exactly the same verifier code as the native-certified source; only isolated experiment CI/report files differ.
- Cases: QFT16 Rust/GPMC, VQE4 Rust/GPMC and VQE4 Python/GPMC drift control. QPE-exact8 is RR-terminating and stays in native RR/semantic admission, never forced to WMC.
- Same-host three blocks A1–B1–B2–A2 each, five official CodSpeed rounds per position. Full verifier including GPMC subprocess, fixed `rr=1e-10`, `distance=1e-8`, `wmc_phase=1e-8`, `GPMC digits=30`. The CI report verifies all source hashes, Solver invocation, full verdict consistency and records every WMC numerical observation.
- GitHub run artifact: `rr-cx-solver-inclusive-abba` (CodSpeed export, source/provenance JSONL, arithmetic observations, block report, SHA manifest, dependency freezes).

| Complete Solver-inclusive workload | Block 0 | Block 1 | Block 2 | Median HEAD/Base | Max Base A1/A2 drift |
|---|---:|---:|---:|---:|---:|
| QFT16 Rust/GPMC | -1.908% | -1.229% | +0.507% | **-1.229%** | 2.636% |
| VQE4 Rust/GPMC | -0.553% | +4.090% | -0.351% | **-0.351%** | 3.514% |
| VQE4 Python/GPMC | +2.831% | +1.184% | +6.167% | **+2.831%** | 6.529% |

Deltas are `100*((B1+B2)/(A1+A2)-1)` from official CodSpeed position medians. **Scientific and Solver stage PASS, native CPU gain previously established; complete end-to-end performance remains INCONCLUSIVE.** QFT16's -1.229% median is below measured 2.636% baseline drift, and Python control shows several-percent variation. No statistically certified end-to-end speedup or regression is asserted.

**Decision: retain exact direct Bra-CX on this isolated experiment branch; do not integrate into formal Draft PR #131 yet.** Additional EQ/NEQ boundary, Python/Rust consistency and release review gates remain. The new CI is scoped to its own workflow/test/reporter/manifest; Markdown changes do not retrigger costly measurement. Earlier failed E2E attempts stopped before Solver because of shallow Git checkout; corrected full-history source guard passed in the final run.

## Scientific admission: exact EQ/NEQ, RR residual and Python/Rust

**Date**: 2026-11-03 Asia/Taipei. **All scientific gates passed** on
the same isolated experiment branch.

- Final [GitHub Actions Run 41581168137](https://github.com/PhysicsQoo/QuPRS/actions/runs/41581168137):
  **SUCCESS**. Earlier [Run 41580695361](https://github.com/PhysicsQoo/QuPRS/actions/runs/41580695361)
  also passed the full EQ/NEQ classification; the final run additionally
  asserts *full returned RR-only vs Hybrid residual PathSum equality*.
- Baseline: previous guarded XOR `1ebe7442d5004a522a915f18e163b1c78da648ab`;
  candidate: exact direct Bra-CX source `2c6f68a578bb84dc916a5c871e0bcd9e1f0f6132`.
  Both built in **independent** Python 3.12/Rust `maturin develop --release`
  environments; the experimental workflow verifies that verifier source
  matches the native-certified candidate and does not rebuild/add tolerance
  rules.
- Reproducible science source:
  `benchmarks/rr_cx_boundary/check.py`,
  `benchmarks/rr_cx_boundary/audit.py`,
  `.github/workflows/rr-cx-boundary-science.yml`.
  The CI artifact `rr-cx-boundary-eq-neq-science` (GitHub artifact ID
  **13205911958**) preserves Base and HEAD full JSON per-result observations,
  source QASM SHA256, exact input angle strings, precision diagnostics,
  dependency lists, and cross-revision audit JSON.
- Fixed independent reference `rr_tolerance=0`, projective
  `approximate_distance_tolerance=1e-8`, `wmc_phase_tolerance=1e-8`,
  `GPMC digits=30`, Proportional strategy, public Python and Rust API.
  This isolates source-exact phase transformations from RR approximation.
  Earlier default-like `rr=1e-10` source-pinned solver-inclusive CodSpeed
  already passed its separate stage/verdict audit (above).

### Source-independent physical EQ/NEQ truth

For a right-multiplied single-qubit `RZ(theta)`, the exact projective
operator distance from identity is `|sin(theta/2)|`, unaffected by
the shared preceding unitary. An inserted `CX^2` is exactly identity.
Thus no reference tool's numerical label is used to establish truth.

| Case (each of Decimal and Mixed) | Angle difference | Independent projective-distance range | Expected | Observed Python/Rust Base/HEAD |
|---|---:|---:|---|---|
| Exact identity CX pair | 0 | 0 | EQ | PASS |
| Near EQ | `1e-9` rad | < `1e-9` | EQ | PASS |
| Near NEQ | `1e-6` rad | > `1e-7` | NEQ | PASS |
| Obvious NEQ | `0.125` rad | > `1e-2` | NEQ | PASS |
| VQE4 original/transpiled | existing real pair | real-source equivalence witness | EQ | PASS (`equivalent*`) |
| VQE4 transpiled + `RZ(0.125)` | 0.125 rad additional | > `1e-2` | NEQ | PASS |

**68 public API calls**, representing **34 distinct case × method × backend
identities** across **two revisions**, passed source-expected EQ/NEQ,
Python/Rust parity and source-preserving Base/HEAD physical classification.
`equivalent` versus `equivalent*` is recorded but deliberately treated
as the same physical EQ class. Python GPMC printed numerical log witnesses
for each near-NEQ pair include `log2(WMC)=1.9999999999998153` against
expected `2.0` in the Hybrid normalization; the WMC-only normalization
is near `3.9999999999998153` versus expected `4.0`. Both correctly
classify NEQ. The raw JSON retains every solver numerical field, including
print-resolution warnings; no secondary magnitude guard overrides distance.

### Direct RR-only residual identity with Hybrid

For **Decimal exact EQ, Mixed exact EQ and real VQE4 EQ**, each backend and
revision separately compares the **entire returned RR residual PathSum** from
`reduction_rules` against `hybrid`, not merely the verifier status.

- **12/12 full residual comparisons PASS**, including equal SHA256 of
  each backend's two representations. These hashes are compared **within
  the same backend and same revision**; Rust and Python print formats are
  different and their hash values are not expected to match one another.
- Real VQE4: RR-only is `unknown`, no Solver; Hybrid on exactly the same
  residual invokes real GPMC and returns `equivalent*`. Observed for both
  Python and Rust on both revisions (**4/4 stage transition witnesses**).
- None of the 68 requests used RR numerical approximation
  (`rr_approximate=false`). The experiment does not conflate RR-only
  `unknown` with WMC precision uncertainty.
- Original exact Decimal source literal
  `0.12345678901234567890123456789` is preserved in generated QASM and
  source SHA metadata. Python Qiskit imports decimal literals into floating
  parameters, whereas Rust source parsing can preserve exact rational
  radians; tests establish **classification parity at the requested
  resolution**, not bitwise identity across these internal representations.

**Scientific gate result: PASS.** This is bounded empirical coverage of
source-accurate QASM pairs, not a mathematical proof of all quantum circuits
or of GPMC arithmetic error bounds. Ganak and larger negative QFT/QPE
cases are not included in this focused gate. The preceding
Solver-inclusive WallTime remains **PERFORMANCE_INCONCLUSIVE**;
the new scientific tests do not time execution and did not rerun any
expensive CodSpeed family. Formal PR #131 remains untouched/Draft.

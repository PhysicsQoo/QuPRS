# Exact Bra-CX specialization: QFT16 / QPE / Decimal / Mixed evidence

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

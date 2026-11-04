# QOO-157: d4 / GPMC *effective significant digit* fairness audit

## Requirement

A valid solver-performance recommendation cannot compare d4 fixed 426-bit
GMP work with GPMC at `-prec=30/90` and present that as an equal-precision
race. That earlier CodSpeed result remains historical *configuration-specific*
evidence only, not an equal-effective-digit speedup/regression certificate.

QuPRS GPMC is pinned at submodule
`PhysicsQoo/GPMC@a1bda3489e959d3695b6798d327c5a1fc1bed305`.
`core/Main.cc` applies `mpfr::mpreal::set_default_prec(mpfr::digits2bits(N))`.
`mpfr/mpreal.h` defines `digits2bits(N) = ceil(N*log2(10))`,
`bits2digits(B) = floor(B*log10(2))`. d4 is based on pinned upstream
`jm62300/d4@be15f91f3e9769e1f5cb175fa27e3eca3a1ea690` and GMP
`mpf_set_default_prec`. GMP rounds requested working bits up to its limb
precision; therefore identical *requested bits* do not imply identical
*actual effective decimal digits*. Record `mpf_get_default_prec`.

## Stage 1: equal requested decimal digits (completed)

[Actions 41821100811](https://github.com/PhysicsQoo/QuPRS/actions/runs/41821100811),
[official CodSpeed 6aeb18beefdbc51abcbc403f](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aeb18beefdbc51abcbc403f),
measured SHA `de9a4b0d9ae8ce2026e35a1a8ad59d265135780b`;
[original artifact](https://github.com/PhysicsQoo/QuPRS/actions/runs/41821100811/artifacts/13317182936).

| Requested and printed decimal digits | GPMC MPFR actual bits | d4 GMP requested bits | d4 GMP actual bits | Actual decimal digits |
| --- | ---: | ---: | ---: | --- |
| 30 | 100 | 100 | 128 | GPMC 30 / d4 38 |
| 90 | 299 | 299 | 320 | GPMC 90 / d4 96 |

All 8 source-identical CNF GPMC/d4 count comparisons passed the 1e-12
source-WMC numerical screening threshold (not a proof or an original
quantum-circuit equivalence certificate). CodSpeed v5 WallTime, three rounds
per result, **prepared CNF external solver inclusive**, excludes QASM/RR/CNF
building. The d4/GPMC median speed ratios in the SAME job are:
Grover4: 4.44x (30) / 2.97x (90); QAOA7 true NEQ: 2.96x / 2.96x;
QPE-exact8: 2.32x / 2.32x; QFT16: 1.49x / 1.45x.
This is **not equal actual effective decimal precision** and therefore not
the definitive fair test. CodSpeed warns that hosted-runner WallTime
outside a Macro Runner can be unreliable. Do not pool with old 426-bit runs.

## Stage 2: equal *effective* decimal digits, minimal bit gap

[Isolated branch](https://github.com/PhysicsQoo/QuPRS/tree/experiment/qoo157-d4-effective-digit-parity)
with native patched GMP preparse and output precision:

| Printed/effective decimal digits | MPFR actual bits | GMP actual bits | Bit gap |
| --- | ---: | ---: | ---: |
| 38 | 127 | 128 | 1 |
| 96 | 319 | 320 | 1 |

The branch's science preflight **fails closed** if actual GMP bits differ by
more than 1 from GPMC MPFR, or the
`floor(actual_bits*log10(2))` significant digits differ on either side.
Original QASM SHA and emitted CNF SHA are held constant across solvers.
Each variant is a scratch-compiled external d4 binary; binary SHA and
patched C++ source diff are retained, binaries are never shipped/bundled.

CodSpeed v5 WallTime still measures complete child solve / I/O / count
parsing, but excludes source circuit work. An untimed SHA-256 precheck of
an immutable CI-only binary avoids an unfair per-call d4 hash overhead.
Science parity and timeout are gated before measuring.

## Interpretation and release scope

- The GMP/MPFR 1-bit difference is the nearest practical match on this
  host for the chosen effective digit counts, **not exact identical
  arithmetic implementation, algorithm, roundoff modes or error bound**.
- A matched decimal-digit output interval describes **printed rounding**,
  not internal arithmetic uncertainty; do not collapse `unknown` by fiat.
- Neither hosted CodSpeed run is a qualified Macro Runner statistical gate.
  A preference reversal would need same-host paired ABBA/BAAB repeatability
  with source-pinned science and full Solver-inclusive Hybrid/WMC-only
  workload coverage.
- GPMC remains dev/main default. d4 remains research-only due precision
  provenance, C++ GPL-3+ source file licensing, Windows `get_d()` truncation,
  portability and distribution questions.

## Stage 2 completed: same effective decimal digits and 1-bit gap

The stronger comparison ran successfully on the *pre-documentation* pinned
code SHA `efab7ccd132214758d4209d0b5c4f6488f30695e`:
[Actions #41822549728](https://github.com/PhysicsQoo/QuPRS/actions/runs/41822549728),
[official CodSpeed 6aeb1b9fefdbc51abcbc4108](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aeb1b9fefdbc51abcbc4108);
[source-CNF, patched C++, actual GMP bits, numerical counts and 16 WallTime
 measurements](https://github.com/PhysicsQoo/QuPRS/actions/runs/41822549728/artifacts/13317939531).

The scratch d4 native binaries **actually reported** 128-bit GMP at requested
127 bits, and 320-bit GMP at requested 319 bits. In both comparisons
`floor(actual_bits*log10(2))` matches MPFR's 38 or 96 effective
decimal digits; the bit gap is exactly 1. d4 output formatting is changed
to 38 / 96 significant digits, matching GPMC `-prec=38/96`. There is no
precision mismatch hidden in the metadata.

All **8/8** source-identical CNF solver pairs passed
`COUNT_CONCORDANT_UNCERTIFIED` (the conservative 1e-12 *count* numerical
screen), with no source/solver/timeout censoring. This is empirical
agreement between two approximate counters, **not proof of an original
quantum equivalence verdict or internal error certification**.

Original first-party CodSpeed v5 WallTime instrument, three-round
**medians** in milliseconds (not unrelated run comparisons):

| Same actual effective digits | Circuit | GPMC | d4 | d4/GPMC |
| --- | --- | ---: | ---: | ---: |
| 38 | Grover4 EQ | 61.148 | 222.231 | 3.63x |
| 38 | QAOA7 true NEQ | 41.134 | 161.813 | 3.93x |
| 38 | QPEexact8 EQ | 61.162 | 182.051 | 2.98x |
| 38 | QFT16 EQ | 1127.108 | 1750.719 | 1.55x |
| 96 | Grover4 EQ | 61.206 | 222.243 | 3.63x |
| 96 | QAOA7 true NEQ | 41.029 | 141.906 | 3.46x |
| 96 | QPEexact8 EQ | 61.100 | 182.056 | 2.98x |
| 96 | QFT16 EQ | 1248.176 | 1852.095 | 1.48x |

**Decision under nearly-bit-identical precision:** every observed
same-CNF, solver-inclusive pair favors GPMC. The initial 426-bit
comparison's unbalanced arithmetic cannot explain this entire difference,
although the ratios and cross-host values must **never be pooled**
or mistaken for a Macro Runner-certified significance test.

The first-party CodSpeed service warns **Walltime results may be unreliable
outside Macro Runners**; specifically the QAOA7/38-digit d4 series had
an observed median around 161.8 ms but a minimum around 141.9 ms.
This is a qualitative **OBSERVATION_ONLY** outcome, not a reliable
regression threshold or a general proof that d4 is inferior on any
possible CNF or reuse workload. The measurement excludes QASM parsing,
CNF generation, RR and whole Hybrid verification.

Do not change GPMC defaults/recommendations based on d4's source-only
capabilities. Retain d4 as research-only optional third Solver and only
revisit a *specific* advantage if source-scoped d-DNNF reuse or
GPMC-hard CNFs produce a scientifically sound, bounded and CodSpeed
reproducible benefit. Patched upstream binaries are NOT licensed or
approved for QuPRS wheels.

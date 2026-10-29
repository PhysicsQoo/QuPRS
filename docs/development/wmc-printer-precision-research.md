# GPMC single-pass output precision and QPE source observations (research only)

Source-pinned experiment dated 2026-10-29. This file is an observational
research note, not a release contract or universal numerical error certificate.

## Reproduction and provenance

- Research branch: `experiment/numerical-tolerance-calibration-20261027`
- Research study commit: `03115d5e31dd5bf499262e394b7d7524da7a8913`
- Public verifier sampled from pinned dev tree: `55e78c7597966617c1a193b89056ff4e99c3ddfb`
- GPMC submodule gitlink: `a1bda3489e959d3695b6798d327c5a1fc1bed305`
- [Experiment workflow #40845845676](https://github.com/PhysicsQoo/QuPRS/actions/runs/40845845676): SUCCESS
- Artifact: `dev-public-single-pass-boundary-experiment`, ID `12885360831`,
  SHA-256 `5feff91a6d46fdf694032f9575bcb8881b063e02d21aeb819c5b770abccbd728`.
  Artifact ZIP CRC passed and its **26/26** internal SHA256SUMS verified.
- Experimental script: `.diagnostics/tolerance_calibration/public_api_boundary_probe.py`.
- Analysis: `scripts/research_gpmc_printer_precision_ab.py --artifact-folder <extracted-artifact-folder>`.

The experiment did not check out or change dev/main, and did not create a PR.
One extra GPMC solve for a public-path CNF was performed **only inside this
research protocol** to observe raw stdout. Production still launches the chosen
solver once per WMC stage.

## Root cause in the pinned native printer

At 90 *decimal* working digits, the native stdout contains:

```text
c o precision 90
c s exact double prec-sci 1+0i
```

For the one-qubit global phase `S X S X = iI` it contains:

```text
c o precision 90
c s exact double prec-sci 0-2i
```

GPMC `core/Main.cc` uses `cout.precision(mpfr::bits2digits(default_prec))`.
`mpfr/mpreal.h` implements stream insertion via `mpfr_asprintf` with the
`%.*Rg` significant-digit format when no fixed/scientific mode is selected.
Thus a shorter displayed integer does **not** in itself imply one significant
digit of precision. Current QuPRS `precision_count._number_and_unit()`
infers the rounding half-unit only from decimal characters, assigning `1/2`
to `1` and `-2`. A source-scoped significant-digit bound is a candidate,
not a valid general parsing rule for other Solver adapters.

For a nonzero integer `x` with base-10 exponent
`e=floor(log10(abs(x)))`, a **conditional printer-only** half-unit is
`0.5 * 10**(e - p + 1)` with `p=90`. Zero retains a zero half-unit.
No bound on source angle conversion, Solver internal MPFR arithmetic, RR
approximation, or all GPMC build variants follows from this alone.

## Experimental readback and A/B

The native GPMC forced-unit CNF families had exactly one satisfying assignment
and observed `1+0i` at each size. All four measured native counts were correct.

| CNF | Actual stdout | Existing classifier | Candidate p=90 printer-only interval | Remaining conditional error |
| --- | --- | --- | --- | --- |
| Forced 12 variables | `1+0i` | `unknown` | `equivalent` | ~1.58e-30 |
| Forced 128 variables | `1+0i` | `unknown` | `unknown` | ~9.54e-7 |
| Forced 160 variables | `1+0i` | `unknown` | `unknown` | ~1.76e13 |
| Forced 512 variables | `1+0i` | `unknown` | `unknown` | ~1.48e225 |
| S X S X global phase | `0-2i` | `unknown` | `equivalent*` | ~3.16e-30 |

Forced CNF uses `epsilon_D=1e-8`, SXSX uses `epsilon_D=2e-4`.
The right column was calculated from the sealed stdout as a **hypothetical**
precision-aware postprocessor: it was not yet fed to the public verifier.
It follows that the parser is demonstrably conservative for short integer
GPMC output, while much of the larger-CNF inconclusiveness originates in the
separate `2**(2*n+20 - MPFR_bits)` *assumed* operation-error term.

Real 1q Rz inside/outside controls at `epsilon_D=2e-4` returned respectively
`equivalent` and `not_equivalent`; one production solve each matched
independent raw-output research replay. Their native output already contains
many printed fractional digits.

## QPEexact8 on one exact source pair

The two original corpus QASMs have SHA256:
- `8d514d06f7c9e81abda1042796cc34227624c9ed66097bee1ce5e97a87884dda`
- `227ab45a4eb033889aa57bb53e54938e74d757fea30eaa3d276b495048dc6141`

Python Hybrid returned `equivalent*` from the RR symbolic path, with **no**
solver process, in 0.066s. Rust Hybrid returned `unknown`, invoked GPMC,
and reported `wmc_printed_verdict=equivalent` plus
`wmc_precision_reason=uncertain_f64_input_or_print_resolution`, in 0.013s.
This is inconclusive, not proven native misclassification. Its root cannot
be fixed solely by adjusting a Python GPMC print-interval parser.

A nearby source-angle pair separated by `1e-30` radians collapses to the
same binary64 value. That is a representability witness, not proof that this
particular QPEexact8 verdict is caused by such an alias.

## Next experiment before a promotion PR

1. Prove or disprove the `%.*Rg` 90-significant-digit rounding enclosure on
   controlled 90-digit MPFR values near integers and on non-integral results,
   using the exact pinned native printer. Bind interpretation to the selected
   GPMC adapter, effective precision and confirmed stdout provenance.
2. Keep the conditional GPMC source/solver component budget separate; test
   whether the rapid n-dependent growth for real QFT/QPE CNFs is supported by
   observed source-to-weight arithmetic or is an unnecessarily coarse bound.
3. Isolate Rust QPEexact8's reduction residual and its `f64` weight-domain
   uncertainty using source-pinned, independent tiny reference circuits;
   preserve RR-first Hybrid and do not force an `equivalent` label.
4. Only after experiment-level tests are stable, promote a minimal fix and
   corresponding deterministic regressions into a single integration PR.

This note does not justify widening `epsilon`, reintroducing a fixed guard,
or adding a second GPMC production solve.


## Phase 2: actual 90-digit MPFR, real algorithm CNFs, Rust source (2026-10-29)

**Research-only, no PR or production algorithm change.** The pinned public
verifier remained dev \`55e78c7597966617c1a193b89056ff4e99c3ddfb\`
and GPMC gitlink \`a1bda3489e959d3695b6798d327c5a1fc1bed305\`.
All experimental code runs on
\`experiment/numerical-tolerance-calibration-20261027\`.

### 1. Real MPFR printer precision (not a general solver certificate)

- Research commit \`f5e7b1ad42d5863fe7ad59255ec811c6da7b843e\`,
  [scoped Actions #40884902755](https://github.com/PhysicsQoo/QuPRS/actions/runs/40884902755):
  **SUCCESS**.
- [Artifact 12902920146](https://github.com/PhysicsQoo/QuPRS/actions/runs/40884902755/artifacts/12902920146)
  ZIP SHA-256 \`04e361a2bdaf0323be8a276ba89fe86e07d46fa76b1e04aa7418396cc27a64a9\`,
  verified ZIP CRC and 28/28 SHA256SUMS.
- The C++ probe includes the exact pinned \`mpfr/mpreal.h\`, sets
  \`mpfr::digits2bits(90)\` (299 bits) and the same
  \`std::ostringstream::precision(90)\` behavior as GPMC. It independently
  extracts the exact **binary** MPFR mantissa and exponent using
  \`mpfr_get_z_2exp\`. The Python reference reconstructs the exact rational
  and checks the candidate *decimal printing* enclosure.
- Eight controls including \`1\`, \`-2\`, near-unit decimal inputs,
  very small/large magnitudes, negative fractional values and zero:
  **8/8 enclosure tests passed**.
- The candidate is a *provider-specific* stream-format bound, not evidence
  for all MPFR arithmetic and not valid for Ganak without its own contract.
  In particular, a short integer \`1\` from the pinned
  \`c o precision 90\` and \`%.*Rg\` printer should not automatically have
  a half-unit rounding error of \`1/2\`.

### 2. Native Rust QPEexact8 with unchanged source and solver count

The source pair SHA256 is unchanged:
\`8d514d06f7c9e81abda1042796cc34227624c9ed66097bee1ce5e97a87884dda\` /
\`227ab45a4eb033889aa57bb53e54938e74d757fea30eaa3d276b495048dc6141\`.

| Rust method, epsilon_D | Solver | Native printed verdict | Public verdict |
| --- | --- | --- | --- |
| RR, 1e-8 | not invoked | N/A | \`unknown\` |
| Hybrid, 1e-8 | GPMC once | \`equivalent\` | \`unknown\` |
| Hybrid, 1e-6 | GPMC once | \`equivalent\` | \`equivalent*\` |

Both Hybrid counts produced identical 90-digit native stdout on the same
31-variable CNF containing **17 numerical weights**. The conditional Rust
normalized component input bound is at least
\`(17+1) / 2^49 ≈ 3.19744e-14\`, compared with an approximate normalized
magnitude defect of \`5e-17\` at \`epsilon_D=1e-8\`. Hence the conservative
input error term alone explains why the positive classifier can remain
unresolved, without proving actual weight errors that large. Widening the
requested epsilon to \`1e-6\` changes the policy outcome; it is **not a
scientifically valid fix** for a stricter requested threshold.

Inspection of the *actual captured Rust CNF decimal weight bytes* shows
trigonometric binary64 residues such as \`-1.0000000000000000e0 +
1.2246467991473532e-16i\`. Of the 17 positive weighted literals,
the maximum absolute decimal \`||w||² - 1|\` is approximately
\`2.65896032e-17\`. This is observable source-to-weight numerical drift
and needs phase-polynomial source attribution before deciding which
Clifford phases can be made exact. It is **not** by itself a bound on the
output WMC count or a proof of an incorrect public verdict.

### 3. Actual original-corpus WMC-only CNFs with one native GPMC count each

The first cohort captured the exact emitted CNFs and solved QPEexact8;
a bounded second cohort raised only the *research* source-CNF cap from
250 to 700 for the other three original-corpus pairs.

- Research commit \`6bef0ffd098b5676c42d12e81b5a75e631c63979\`
  [scoped Actions #40885739008](https://github.com/PhysicsQoo/QuPRS/actions/runs/40885739008)
  **SUCCESS**; printer and Rust QPE already-evidenced stages intentionally skipped.
- [Artifact 12902208791](https://github.com/PhysicsQoo/QuPRS/actions/runs/40885739008/artifacts/12902208791)
  ZIP SHA-256 \`da6544b2a38dbe522cdb45303f1c5ecffaa1084adfb8d153ed2671233a236675\`,
  ZIP CRC and 15/15 SHA256SUMS verified.
- Each workload uses the existing *WMC-only* API, one native GPMC
  \`-prec=90\` counting invocation on its emitted CNF, a separate worker
  with wall/memory cap and source SHA256. No production replay or alternative
  solver fallback.

| Original pair | Actual CNF variables | Weighted literals | GPMC printed value classification | Public epsilon_D=1e-8 verdict | Reason |
| --- | ---: | ---: | --- | --- | --- |
| QPEexact8 | 246 | 175 | \`equivalent\` | \`unknown\` | conditionally model-insufficient |
| QFT16 | 486 | 400 | \`equivalent\` | \`unknown\` | conditionally model-insufficient |
| Graphstate16 | 623 | 423 | \`equivalent\` | \`unknown\` | unsupported beyond 512-variable model |
| QAOA7 | 624 | 433 | \`equivalent\` | \`unknown\` | unsupported beyond 512-variable model |

All four actual solvers completed; no resource timeout in these four.
But **4/4 unknown is specific to WMC-only, epsilon_D=1e-8, these
sources and this candidate model**. Existing original RR-first Hybrid may
resolve without WMC; do not extrapolate the rate to Hybrid, to all circuits,
or to strict paper correctness results. The raw printed count classification
does not account for source-angle, weight, or solver arithmetic uncertainty
and must not be advertised as a proven equivalent result.

The conditional Solver operation-error exponent
\`2*n+20 - (floor(90*log2(10))-2)\` is respectively
\`216\` (QPE8), \`696\` (QFT16), \`970\` (Graphstate16) and
\`972\` (QAOA7), where the latter two are outside the model's n<=512
scope. These are **assumed error allowances in absolute count units**,
not measured actual GPMC errors. The rapid growth and coarse n-only
scaling, along with the >512 cutoff, are the present obstacles to
numerically decisive large-CNF WMC-only verdicts.

### Promotion decision

**No production PR yet.** These results verify the pinned MPFR printer
rounding issue and exhibit overly broad Rust and large-CNF conditional
error assumptions. They do **not** provide a rigorous source-weight /
GPMC internal arithmetic enclosure for arbitrary quantum circuits.

Next research: compare actual per-phase Rust source exact coefficients
against their f64 and high-precision weights, including precise Clifford
quarter turns; audit meaningful GPMC solver arithmetic/cancellation
operation budgets using actual CNF structure rather than a coarse
\`2^(2*n)\` allowance; add numerical adversarial/cancellation controls
for any candidate provider-bound precision rule. Keep RR-first Hybrid,
one production GPMC solve, separate source/solver/printing uncertainty
and appropriate \`unknown\` outcomes.


## Phase 3 — actual native Rust source-weight gaps and exact separable CNFs

Research-only source commit `0b9f38929e2de4bb074016c8e0e1798509063bc4`,
[Actions #40896543559](https://github.com/PhysicsQoo/QuPRS/actions/runs/40896543559)
**SUCCESS**, evidence [artifact 12906424706](https://github.com/PhysicsQoo/QuPRS/actions/runs/40896543559/artifacts/12906424706)
ZIP sha256 `0694727f289dadd7af138334a19824ca905cb50e6ff907450a3b4bbc976f70be`,
ZIP CRC PASS and 44/44 internal SHA256SUMS PASS. The experiment was run on
the **existing** experiment branch only, with no PR or dev/main changes.
The standard public Python/Rust verifier was built from pinned dev
`55e78c7597966617c1a193b89056ff4e99c3ddfb`, while the dedicated
experimental Rust pathsum unit test was compiled from the experiment source
(with extra `#[cfg(test)]` logging). Do not conflate those two source trees.

### Native phase-to-binary64 weight audit

Source exact rational phase coefficients and **actual native Rust f64 bit
patterns**, not decimal copies of input angles, were independently checked
with 120-digit mpmath trigonometry or algebraic exact quarter-turn weights.
Ten observed native terms:

| Source | Max observed complex absolute error | Exact quarter-cycle in source |
| --- | ---: | --- |
| S | 6.123233995736766e-17 | yes |
| S† | 1.836970198721030e-16 | yes |
| Z | 1.224646799147353e-16 | yes |
| H | 1.224646799147353e-16 | yes |
| T | 7.915761506067900e-17 | no |
| T† | 2.357323367686493e-16 | no |
| Rz(0.0002) | 5.488275696634135e-17 | no |
| Rz(pi/2) | 2.357323367686493e-16 | one quarter-cycle, one eighth-cycle |

For S, the native weight was approximately
`6.123233995736766e-17 + 1i` instead of exact `i`. For Z,
it was approximately `-1 + 1.2246467991473532e-16i` instead of
exact `-1`. This directly isolates avoidable trigonometric residue for
source coefficients exactly congruent to 0, 1/4, 1/2 or 3/4 modulo a full
cycle *without a nonzero radian remainder*. It does not establish that
changing these terms alone resolves Rust QPEexact8 `unknown`.
For eighth-cycle/T and arbitrary decimal radians, source-preserving
higher-precision weight evaluation remains a separate research path.

### Native GPMC vs *independent exact rational printed-CNF count*

One GPMC invocation per `(CNF, precision)` pair: 7 disjoint/separable
weighted-CNF families at 30 and 90 decimal digits, total **14/14 native
count observations**. The expected complex answer was calculated exactly
by multiplying independent literal weight sums from the original emitted
decimal CNF, **without running a second solver as oracle**.
This is an observed arithmetic error, *not* a general GPMC error bound.

| CNF family | Variables | Independent exact count | GPMC 30-digit absolute error | GPMC 90-digit absolute error |
| --- | ---: | ---: | ---: | ---: |
| balanced | 64 | 1 | 0 | 0 |
| balanced | 256 | 1 | 0 | 0 |
| balanced | 512 | 1 | 0 | 0 |
| two real cancellations | 64 | 1e-40 | 4.45381424e-51 | 9.79495089e-111 |
| four real cancellations | 256 | 1e-80 | 8.90762849e-91 | 1.95899018e-150 |
| four real cancellations | 512 | 1e-80 | 8.90762849e-91 | 1.95899018e-150 |
| two complex cancellations | 128 | 1e-40 | 4.45381424e-51 | 9.79495089e-111 |

All inputs were parsed through the selected native GPMC and exact original
decimal literals; no unsupported signed-complex case was silently discarded.
Even 512 variables yielded exact count 1 in the balanced family while the
existing **assumed**, variable-only conditional solver bound scales as
`2^(2*n+20-bits)`, i.e. `2^748` in absolute count units at 90 digits
for `n=512`. For matching four-cancellation families, expanding the number
of neutral/independent variables from 256 to 512 did not change the
observed count error. These data strongly support studying CNF/component
structure and actual weighted arithmetic work instead of treating
`2^(2*n)` as an empirically representative error estimate. But they do
**not** establish a valid upper bound for entangled QFT/QPE/Graphstate/QAOA
CNFs, where sum/cancel structure is different.

### Acceptance decision

- **Confirmed experimental fact:** exact Clifford quarter-cycle phases can
  be represented without native `sin(pi)`/ `cos(pi/2)` residue.
- **Confirmed experimental fact:** GPMC performed much more accurately than
  the existing broad n-only conditional model on this bounded separable cohort.
- **Not yet resolved:** a sound general GPMC weighted-count arithmetic
  enclosure, including actual component counts, cancellation and complex
  weights of original algorithm CNFs.
- **Not yet resolved:** whether refined native source weights make
  Rust QPEexact8 decisive at epsilon_D=1e-8, including strictness and
  non-Clifford source angles. No threshold or source angle was loosened.
- **Release policy:** remain experimental. Promote a narrowly validated
  corrective implementation only after additional source-pinned real-CNF
  counterexamples/negative controls pass, never by relaxing the public
  distance tolerance or adding a second production Solver run.

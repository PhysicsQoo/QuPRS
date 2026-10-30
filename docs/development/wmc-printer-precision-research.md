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


## Phase 4 — original QPEexact8 and QFT16 source-weight A/B (2026-10-30)

**Experimental branch only.** Research source commit
`49217d442c2f09ca3c996688578842bc69d69e7a`,
[Actions #40969660098](https://github.com/PhysicsQoo/QuPRS/actions/runs/40969660098):
**SUCCESS**. Artifact
[12939907212](https://github.com/PhysicsQoo/QuPRS/actions/runs/40969660098/artifacts/12939907212),
ZIP SHA256
`bfc4b985cb8f1d6aa099adc9cf10e7b68a4e6321065f700b157a1045e80c4ce1`;
ZIP CRC and 25/25 internal SHA256SUMS independently verified.

### Method and source separation

The public APIs, including actual Python QFT16 and Rust QPEexact8,
were installed from fixed **dev**
`55e78c7597966617c1a193b89056ff4e99c3ddfb`.
A `#[cfg(test)]`-only diagnostic unit test on the existing
**experiment** Rust pathsum reconstructed QPEexact8's native miter
from exactly pinned QASM source pair hashes
`8d514d06f7c9e81abda1042796cc34227624c9ed66097bee1ce5e97a87884dda` /
`227ab45a4eb033889aa57bb53e54938e74d757fea30eaa3d276b495048dc6141`.
It emitted native source rational cycle/radian coefficients attached to
individual weighted literals, without snapping approximate weights to
"nearest root". The miter had **31 CNF variables, 17 numerical weights,
six active path variables, normalization exponent twice=22**.
The experiment CNF and the public dev CNF differed in raw byte hashes
(HashMap output order / variable labels need not be identical), but the
**actual baseline GPMC printed complex count matched exactly** and
the CNF header/weight shape agreed. That is strong observational
comparability, not byte-for-byte source identity.

### QPEexact8 Rust: source-trace A/B actually solved with GPMC

There were **10 exact quarter-cycle terms**, **two eighth-cycle
nonquarter terms**, **five source-radians nonzero terms**.
Only source-proven exact quarter cycles were replaced with
algebraic exact complex values; none were selected based on closeness.

Every candidate below used the *same miter clauses* and one independent
experimental native GPMC invocation at `-prec=90`.
`D²` is reconstructed from the printed count magnitude and the
normalization factor; it is NOT a certified quantum distance.

| Study input | Printed normalized magnitude defect | Printed candidate D² |
| --- | ---: | ---: |
| Stock native Rust f64 | 1.2871134580104743e-17 | 2.5742269160209487e-17 |
| Only 10 source-exact Clifford quarters | 1.2871134580104702e-17 | 2.5742269160209404e-17 |
| All 17 weights regenerated from exact source phase by 125-digit independent trigonometry (exact quarter values special-cased) | 3.423050778880919e-31 | 6.846101557761838e-31 |

**Result:** fixing only Clifford phases does essentially nothing to
the QPE8 count defect; precision loss from eighth-cycle and/or nonzero
source-radian terms is material. All-source high-precision weight
replacement can greatly reduce the **observed** count defect on this
particular miter. This does NOT certify either source-to-weight or
solver-internal arithmetic. It also does not update the public
Rust classifier's conditional f64 input bound, which currently
forces `unknown` at epsilon_D=1e-8.

For context, the stock Rust output implied candidate
`D ≈ 5.07368e-9` while the all-source precision candidate implied
`D ≈ 8.274e-16`. These are model-free distances from the observed
counts **only**, with source/solver unknowns omitted. Do not treat
the candidate as a proof of QASM exact equivalence.

### QFT16 Python: exact-source quarter cycles do not affect result

The **actual pinned public dev QFT16** WMC-only CNF had 400
positive numerical weights. Of these, the parsed phase expressions
provided **167 proven rational quarter cycles**. A further
11 numeric weights lay within 1e-12 of a quarter-unit root but their
parsed phase expression did NOT prove that relation. These 11 were
**not** snapped or promoted to exact Clifford phases.

Real native GPMC count, before versus after modifying only
the 167 source-proven quarter weights, was **identical** to
90-decimal-digit printed precision. Both had printed
normalized magnitude defect approximately
`1.13691752980537e-30` and candidate
`D² ≈ 2.27383505961075e-30`. Public verdict remained
`unknown` with reason
`single_pass_uncertified_insufficient_printed_resolution`;
that is not a solver arithmetic counterexample. Fixing source-proven
quarter cycles therefore **does not resolve QFT16**.

### Negative control and scope

A physically different QASM pair, identity vs one-qubit
`Rz(0.01)`, returned `not_equivalent` under
`epsilon_D=1e-8` in pinned public Python WMC-only.
This is ONE bounded negative control, not a full equivalence
regression certification of any proposed model.

**Scientific promotion decision:** do not open a PR on this evidence.
Two distinct tasks remain:
1. For Rust, investigate source-accurate non-Clifford/eighth/radian
   weights and a defensible composition bound for the *actual*
   QPE8 miter; arithmetic correctness must not be inferred from
   two numerical Solver runs.
2. For QFT16, investigate the true source representation for the
   remaining 233 terms and the published Solver MPFR arithmetic
   guarantees / count-cancellation structure, rather than
   manufacturing equivalence by a permissive threshold or by snapping
   eleven near-Clifford weights.

No production algorithm changes, no added solver replay in
the public code path, no new PR/branch/worktree.

### Independent post-run source-category error attribution

Using the artifact's exact `SOURCE_WEIGHT_AUDIT` rational phase
coefficients and the actual research-miter CNF weight decimals, an
independent 115-digit oracle measured the absolute complex weight
differences by *proven source category*:

| QPE8 source phase category | Terms | Maximum individual | Sum of absolute differences |
| --- | ---: | ---: | ---: |
| Exact quarter cycles | 10 | 1.837e-16 | 1.225e-15 |
| Exact eighth cycles (nonquarter) | 2 | 2.337e-16 | 3.126e-16 |
| Nonzero source radians | 5 | 1.789e-16 | 4.809e-16 |

Notably, **the exact quarter-cycle category has the largest
sum of absolute single-weight errors**, yet replacing precisely
those ten terms produced essentially no change in the
*normalized count-magnitude defect*. This is direct evidence that
a simplistic sum of independent weight errors is not an
informative estimator of this particular trace's cancellation and
global-phase structure. It is nevertheless a possible conservative
input perturbation bound; these experiments do not invalidate
mathematically proven upper bounds. The stronger all-source
weight reconstruction changes the miter count materially, and
the separate eighth and source-radian contributions should be
investigated without assuming their effects add monotonically.


## Phase 5 — separated QPEexact8 eighth-cycle and source-radian contributions; genuine source-negative controls

Date: 2026-10-30 (Taipei). Strict research-only continuation on
`experiment/numerical-tolerance-calibration-20261027`, study commit
`106b91d31ef87d5fb3396578f5ef8f9463512bda`.

- [Source-pinned opt-in Actions #40975823758](https://github.com/PhysicsQoo/QuPRS/actions/runs/40975823758):
  **SUCCESS**.
- [Native evidence artifact 12942328264](https://github.com/PhysicsQoo/QuPRS/actions/runs/40975823758/artifacts/12942328264):
  ZIP SHA256 `b435408ccea03b3ad70d8057ab24897693418119317d4a0ff96eb2db8d1c1449`,
  ZIP CRC verified and **30/30** internal SHA256SUMS verified.
- Tested public APIs still built from pinned dev
  `55e78c7597966617c1a193b89056ff4e99c3ddfb`.
  Source-phase logging and miter-CNF reconstruction are
  `#[cfg(test)]` research-only Rust code on the existing experiment
  branch, not the public dev build. The exact original source pair
  SHA256 remains `8d514d06f7c9e81abda1042796cc34227624c9ed66097bee1ce5e97a87884dda` /
  `227ab45a4eb033889aa57bb53e54938e74d757fea30eaa3d276b495048dc6141`.
- Each candidate has the **same** 31-variable miter CNF *clauses*
  and normalization exponent twice=22. Individual CNF weight bytes
  differ deliberately, while solver settings are fixed to
  GPMC `-prec=90`. Six native counting invocations in the
  *experiment* are six different candidate trials, **not** production
  WMC replay or a second production Solver pass.

### Exact-source category A/B (printed-count diagnostics, not a certificate)

The native rational phase terms contained exactly 10 known quarter-cycle,
two eighth-cycle-but-not-quarter and five nonzero-source-radian weights.
Only the source-rational categories were used to choose replacement
weights; proximity to 1, -1, i, -i played **no role**.

| Candidate | Changed weights | Printed GPMC candidate D_proj² |
| --- | ---: | ---: |
| Baseline native f64 | 0 | 2.5742269160209487e-17 |
| Source-exact eighth cycles only | 2 | 1.2447467565562121e-17 |
| Nonzero source radians only | 5 | 1.3294801594648057e-17 |
| Both eighth cycles and radians | 7 | 7.055440585634822e-31 |
| Quarter cycles only | 10 | 2.5742269160209404e-17 |
| All seventeen from source phase | 17 | 6.846101557761838e-31 |

Both non-Clifford categories affect the observed magnitude defect,
and jointly nearly remove it; fixing only quarter-cycle terms is
insufficient. The observed magnitude-defect second-order interaction
`defect(eighth+radians) - defect(eighth) - defect(radians) + defect(base)`
was approximately `6.91647e-33`, small in this cohort but **not**
a general additivity law. Do not replace a defensible worst-case error
bound with this observed error, and do not assert that these
printed candidate distances are source-unitary or GPMC arithmetic
certificates.

### Genuine mutated QASM non-equivalence controls at D epsilon=1e-8

The original original-corpus QASM bytes for QPEexact8 and QFT16
were preserved. Separate real QASM files append the genuine gate
`rz(0.01) q[0];`, once to the original input and once to the
transpiled target. All four altered QASM files, source hashes and
native Solver observations are in artifact 12942328264.

The **original circuit vs its own mutated circuit** is independently
non-equivalent, with a known global-phase-invariant distance for any
unitary `U`: `D_proj(U, Rz(0.01) U)=|sin(0.005)|`,
approximately `0.004999979166692708` (unitary conjugation invariance).
This is far above `1e-8`, regardless of algorithm family.
In the **original vs mutated transpiled** controls, the original
cross-implementation baseline has not been independently certified,
so only observed API/solver statuses are asserted.

| Original benchmark / API | Self-source mutation | Modified transpiled target |
| --- | --- | --- |
| QPEexact8 Rust Hybrid | `not_equivalent` | `not_equivalent` |
| QPEexact8 Python WMC-only | `unknown` | `unknown` |
| QFT16 Python WMC-only | `unknown` | `unknown` |

All six public API calls completed and invoked native GPMC once.
For **all six**, the selected Solver's printed-count classification
was `not_equivalent`. Rust QPEexact8 Hybrid promoted the negative to
`not_equivalent`, whereas the four Python WMC-only cases remained
`unknown` with reason
`single_pass_uncertified_insufficient_printed_resolution`.
None returned `equivalent` or `equivalent*`: the tested known-negative
self-pairs had no false-positive classification, but Python's negative
decision coverage is poor at this threshold. **Unknown is not a pass**.

This demonstrates the current incomplete numerical model affects
both positive and negative conclusions, rather than merely blocking
positive equivalence. The printed negative alone cannot justify
reclassifying every unresolved large-CNF case without sound
solver-error and input-weight bounds.

### Research decision

Do not promote a production PR yet. Focus a next **bounded**
experiment on deriving an error *enclosure* from actual solver
weighted arithmetic and source-to-weight rounding for realistic
QPE/QFT miter CNFs, including cancellation, interval direction and
negative controls. For Rust, higher-precision representation of the
two eighth and five nonzero-radian source coefficients is more
effective than Clifford-only special-casing in this observed pair.
Maintain an unknown region when a certified bound cannot decide.
Do not alter RR-first Hybrid dispatch, public epsilon, production
single Solver invocation or introduce a global fixed guard.


## Phase 6 — QPE/QFT real-CNF d-DNNF exact arithmetic and structure-aware error enclosure

**Date:** 2026-10-30. **No production modification or PR.** Research
branch `experiment/numerical-tolerance-calibration-20261027` continued
from dev source `55e78c7597966617c1a193b89056ff4e99c3ddfb`.
The experiments are *reference-oracle research*, not a proposed routine
second GPMC solve in the public verifier.

### Primary four actual-CNF d-DNNF experiments

Research commit `5c5a8d5951b223e6c279514ca88ce58b0ec1e829`,
[Actions #40977618673](https://github.com/PhysicsQoo/QuPRS/actions/runs/40977618673)
**SUCCESS**. [Artifact 12943466270](https://github.com/PhysicsQoo/QuPRS/actions/runs/40977618673/artifacts/12943466270)
ZIP SHA256 `464cfc088d03537ad4ed90bbc5f552da6bf75ec78e021206ea95534e20619eb8`,
CRC PASS, 26/26 internal SHA256SUMS PASS.

GPMC `-ddnnf -nnfout` generated actual counting circuits from the
original source-pinned QPEexact8 Rust Hybrid and QFT16 Python WMC-only
miters and from each algorithm's physically changed source
`Rz(0.01)` self-pair. An independent Python evaluator multiplied and
added **exact rational representations** of every complex *printed
decimal CNF weight*, rather than MPFR arithmetic, and independently
compared the exact rational results with the native GPMC 90-digit
weighted counts.

| Source-pinned real CNF | d-DNNF nodes | Max absolute printed GPMC versus exact rational component discrepancy |
| --- | ---: | ---: |
| QPEexact8 baseline | 83 | 4.35e-87 |
| QPEexact8 self-source mutation | 1 | 1.19e-90 |
| QFT16 baseline | 200887 | 8.34e-75 |
| QFT16 self-source mutation | 200725 | 2.13e-75 |

These are **observed** Solver arithmetic differences on the emitted
CNF, not global a priori error bounds. For the separately evaluated
d-DNNF, no arithmetic rounding is present: integer/rational addition
and multiplication are exact.

### Independent structural checks on sealed d-DNNF

A second local analysis of the four sealed NNF artifacts confirmed
that every `O decision_variable 2 left right` node had opposite
decision-variable literals **implied by its children**, hence the
two alternatives are disjoint. Every `A` node had disjoint
variable support among its children, hence was decomposable.
Original-variable mappings were complete and occurred exactly once;
there were no unsupported deleted original variables.

In total, the four real circuits passed **133431/133431** OR
decision-disjointness checks, **266727/266727** AND
decomposability checks, with no duplicate/missing variable maps.

**Remaining gap:** this verifies deterministic/decomposable structure
of the *emitted* graph; it is **not** a separate proof that GPMC's
preprocessor and d-DNNF conversion exactly preserve the entire
original input CNF. Faithfulness must be independently established
before using the circuit as a formally certified verifier oracle.

### Exact integer model counts and source-weight perturbation theorem

The same d-DNNFs can be evaluated in the *integer counting* semiring
(OR as integer sum, AND as product) to obtain the **actual number
of satisfying assignments** of the compiled representation:

| Real CNF | CNF variables | Weighted phase literals | N_sat |
| --- | ---: | ---: | ---: |
| QPE8 baseline | 31 | 17 | 2^11 |
| QPE8 self-negative | 10 | 2 | 2^8 |
| QFT16 baseline | 486 | 400 | 2^70 |
| QFT16 self-negative | 465 | 385 | 2^64 |

Each negative literal's weight is exactly 1 and each displayed
phase-weight magnitude is bounded by `M=1+2^-40` from the actual
decimal CNF coefficients. Suppose every corresponding *ideal*
phase weight has magnitude 1 and has complex absolute error at most
`delta` relative to the displayed decimal coefficient.
The telescoping product bound, applied to at most `m` weighted
phase literals in each satisfying assignment, yields

```text
|WMC(ideal source phases) - WMC(printed CNF phases)|
  <= N_sat * m * delta * M^(m-1).
```

This inequality is **mathematically rigorous under its assumptions**.
It is not the old empirical `2^(2*CNF_vars)` Solver error allowance.
The d-DNNF evaluator uses only rational arithmetic; this bound
describes *source-weight perturbation*, not GPMC MPFR errors.

### Offline rational-threshold classification

Research commit `aaa7115ef5f5323a577f99788b6cbbb6923b4f5e`,
[offline Actions #40978779185](https://github.com/PhysicsQoo/QuPRS/actions/runs/40978779185)
**SUCCESS**, using the **existing** artifact above: it launched
**zero GPMC solver processes**.
[Artifact 12943832517](https://github.com/PhysicsQoo/QuPRS/actions/runs/40978779185/artifacts/12943832517)
ZIP SHA256 `2ff7f485245c971279687464ecaa121b583fe7fdaabd392859bbd6f9aa07ecd0`,
CRC PASS, 5/5 internal SHA256SUMS PASS.
All source CNF SHA256 values are pinned in
`.diagnostics/tolerance_calibration/structure_aware_source_bound.py`.
The magnitude-vs-distance comparison used *rational squared*
inequalities; there is no binary64 rounding of the WMC count.

| Original source-pinned pair | Per-weight delta <= 2^-49 (assumption) | Per-weight delta <= 2^-100 (assumption) |
| --- | --- | --- |
| QPEexact8 baseline | unknown | conditionally within D=1e-8 |
| QPEexact8 self-negative Rz(0.01) | conditionally not_equivalent | conditionally not_equivalent |
| QFT16 baseline | unknown | conditionally within D=1e-8 |
| QFT16 self-negative Rz(0.01) | conditionally not_equivalent | conditionally not_equivalent |

The **normalized** source-weight uncertainty radii at the less
optimistic `delta=2^-49` are approximately:
QPE8 baseline `3.02e-14`; QPE8 negative `3.55e-15`;
QFT16 baseline `3.73e-7`; QFT16 negative `4.48e-8`.
These are far below the real self-negative separation for the
two physically altered circuits, `D_proj=|sin(0.005)|≈0.0049999792`.
The source-weight upper bounds are far below the negative *normalized
trace-magnitude* defect (approximately 1.25e-5) as well.

At `delta=2^-100`, QFT16 baseline normalized input bound falls to
`1.65e-22`, much smaller than the distance-threshold magnitude
defect `5e-17`, and can produce a conditional positive verdict.
The **actual pinned Rust QPE8 f64 weights are not certified
to satisfy delta=2^-100**; that hypothetical positive result is not a
valid reason to promote the current Rust status.

### Certification boundaries and production decision

All statuses in the table are explicitly **conditional**.
Neither `delta=2^-49` nor `delta=2^-100` has been proven as a
uniform bound on Qiskit/QASM -> Path-sum -> numerical weights for all
these sources. In addition, a graph satisfying the checked local
d-DNNF properties has not been independently proven equivalent to
the complete original weighted CNF; and the QFT-negative
normalization exponent should be read back as an explicit public
result before release promotion.

This is nevertheless a stronger, structure-sensitive **mathematical
error analysis** than the n-only GPMC MPFR heuristic. It provides a
clear bounded route to `not_equivalent` on true QPE/QFT negatives
*without* arbitrarily widening the user's distance threshold.
The required remaining step is to close those **two** proof obligations,
not to treat repeated Solver agreement as a numerical certificate.

Cost: actual QFT d-DNNF compilation and exact rational evaluation
took about **34–40 seconds per real case** on the hosted runner,
versus approximately 1–2 seconds for the previous native GPMC WMC
call. The technique is therefore a research reference/oracle, **not**
a justified automatic production fallback or mandatory extra solve.

**Next before a formal PR:**
- Establish a rigorous, source-identity-aware upper bound on each
  Qiskit/Python/Rust emitted phase weight (including arbitrary
  decimal radian literals and eighth-cycle phases).
- Independently check the d-DNNF/compiler-to-original-CNF mapping
  beyond local decision/decomposition checks, with small exhaustive
  fixtures and/or SAT-backed miter certificates.
- Determine whether an efficient *single-pass* WMC implementation
  can expose enough support-count/structural information for a
  scalable bound without constructing a full 200k-node exact graph.
- Preserve RR-first Hybrid, independent Solver selection,
  `unknown` when evidence is insufficient, and **one solver
  invocation per actual WMC stage**. Never use empirical printed
  digits alone, arbitrary guards, or forced equivalence.


## Phase 7 — MPFR-directed source coefficients and a single GPMC d-DNNF run (2026-10-30)

**Scope:** Existing experiment branch only; public dev pinned at
`55e78c7597966617c1a193b89056ff4e99c3ddfb`.
Source-pinned research commit
`dd73b9bb954f65dc9a50623c8280cba105df6d95`,
[Actions #40984501155](https://github.com/PhysicsQoo/QuPRS/actions/runs/40984501155)
**SUCCESS**. Preserved [artifact 12946073052](https://github.com/PhysicsQoo/QuPRS/actions/runs/40984501155/artifacts/12946073052)
ZIP SHA256 `6ba05604e636516f55a0bad67d7b37148ef179d3d1cbb063764fd5a985283174`,
ZIP CRC verified and **39/39** internal SHA256SUMS checked.

### What was actually proven about the fixed Rust source

The experiment's `#[cfg(test)]` source-miter producer emitted the original
QPEexact8 pair and a **physically changed true self-pair**
`U` versus `Rz(0.01)U`. It recorded each exact Rust
`PhaseCoefficient` as rational cycles plus rational source radians,
then recorded the corresponding actual printed decimal CNF weight.
Source-to-miter trace and normalization for the specific sources
are still semantic obligations; no unconditional claim is made for
all QASM or all Python inputs.

The separate Linux-x86_64, 384-bit MPFR audit used directed
rounding for `pi`, exact-rational coefficients and all interval
arithmetic. It enclosed the **true** sine/cosine by evaluating a
correctly directed endpoint and expanding its range with the global
1-Lipschitz bound. Every actual printed CNF decimal weight was
compared as an exact `Fraction` against the MPFR binary endpoints,
not a high-precision but uncertified `mpmath` approximation.
A sound component L1 difference upper bound also bounds the
complex Euclidean absolute weight error.

| Exact source QPE miter | Positive numerical weights | Largest proven source-to-CNF weight L1 error | Bound status |
| --- | ---: | ---: | --- |
| Original QPEexact8 | 17 | ≤3.3000000000000000e-16 | <2^-51 |
| Physically mutated QPE8 self-negative | 2 | ≤1.7962800372021307e-17 | <2^-51 |

These **specific input-wise** interval enclosures establish
`delta <= 2^-49` for both Rust examples, replacing the prior
**unproven** 2^-49 assumption *for these examples only*. They also
demonstrate that 2^-100 cannot be assumed for the stock native
binary64 Rust phase weights.

For each of those *same* experiment-source CNFs the native GPMC was
invoked **once** at 90-decimal-digit working precision with
`-ddnnf -nnfout=...`, emitting its usual weighted count plus the
d-DNNF witness in the same process. Independent exact rational
NNF evaluation and integer model-count checking gave:

| Source-specific miter | CNF vars / source weights | N_sat | Source-only normalized WMC uncertainty | Conditional D=1e-8 classification |
| --- | --- | ---: | ---: | --- |
| QPE8 baseline | 31 / 17 | 2^11 | ≤5.610000000081637e-15 | unknown |
| QPE8 `Rz(0.01)` self-negative | 10 / 2 | 2^8 | ≤3.592560074407529e-17 | not_equivalent |

The weight uncertainty above uses the proven input-specific
`delta` and the derived telescoping bound
`N_sat * m * delta * (1+2^-40)^(m-1)`. The exact rational
d-DNNF evaluation removes MPFR arithmetic rounding in the
independent reference calculation; **this alone does not prove**
the d-DNNF is faithfully compiled from an arbitrary CNF.

### Stronger independent fixed-negative CNF semantics check

For the 10-variable negative QPE8 witness the CNF SHA256
`b965d82a7bf4900350a2cbef028ff51506b9bb0f426859c1be9432207872d2d7`
and emitted NNF SHA256
`2bcfab3dfd9dbcb0252505b24fba934cff10753004954a324d4e651cb6cd41a0`
match the earlier sealed Phase 6 negative case **byte-for-byte**.
An independent Boolean truth-table evaluator enumerated all
`2^10=1024` assignments and obtained **0 mismatches** between
the original CNF clauses and the d-DNNF variable-map/fixed/free
constraints. Both had exactly 256 satisfying assignments.
The independent, reproducible bounded verifier is
`.diagnostics/tolerance_calibration/exhaustive_small_dnnf_cnf.py`.

This closes the d-DNNF-to-CNF semantic obligation for this **one
fixed 10-variable negative instance**, not QPE baseline
or the general large QFT compilation process.

### Native single-solve GPMC structure/cost boundary

Pinned GPMC `core/Main.cc` counts once, prints the usual
weighted count, and then emits d-DNNF through `doDNNF` when
`-ddnnf -nnfout` is enabled. Source inspection and actual
stdout agree. At fixed QFT16 baseline the same native execution
reported 200121 internal counting nodes, 1587167 edges,
1.66 s native walltime, ~123 MB peak RSS and produced an ~8.07 MB
d-DNNF. A separate independent integer-only walk on the
200887-node emitted d-DNNF computed `N_sat=2^70`
in ~0.26 s. Full Python rational complex reconstruction
took ~34–40 s; this higher cost is **not** the d-DNNF
compilation cost itself.

Therefore it is **feasible** to obtain meaningful structure
within a single selected GPMC process and evaluate exact
integer model counts without an extra Solver invocation.
It is **not yet justified** as an always-on default:
`-ddnnf` affects solver-side execution state, output size,
and memory; a paired, controlled A/B is still required.

**Scientific certification boundary:** The QPE8 negative fixed
source now combines directed weight intervals, an exact rational
NNF computation and exhaustive CNF–NNF equivalence, supporting
the conditional numerical negative without relaxing epsilon.
A general `not_equivalent` promotion still needs a reliable
and preferably inexpensive way to certify *each emitted source
weight* and *each original CNF / emitted witness* in the selected
Python/Rust public path. In particular, Python QFT16's SymEngine
`evalf(113)` is not an automatically certified source-to-weight
error interval, and the d-DNNF's >200k nodes are not covered by
the small-case exhaustive check.

**Research workflow correction:** The earlier sourcebound-only
experiment name contained the substring `bound-only`, which
unintentionally selected the prior four-case d-DNNF study as
well. The gating is now narrowed to the exact research(bound):
prefix, so future source-bound studies do not repeat QFT16.
This does not affect any production code or main/dev workflow.


## Phase 8 — Python QFT16 directed phase-weight bounds, large CNF implications and matched GPMC cost

**2026-10-30 | research-only; no PR or dev/main update.**
Existing branch `experiment/numerical-tolerance-calibration-20261027`.
Pinned public dev `55e78c7597966617c1a193b89056ff4e99c3ddfb`,
pinned GPMC `a1bda3489e959d3695b6798d327c5a1fc1bed305`.

- Source-and-performance experiment commit `e222d14328d4d9619fe91734d577ba6ab263b6b2`:
  [Actions #40986641177](https://github.com/PhysicsQoo/QuPRS/actions/runs/40986641177) **SUCCESS**,
  [artifact 12947142574](https://github.com/PhysicsQoo/QuPRS/actions/runs/40986641177/artifacts/12947142574);
  ZIP SHA256 `48c9059497cbf5830e366257187ef1b1bf1f9ef5eb26d6ba692a16ec9527ea8d`,
  ZIP CRC PASS and **75/75** internal SHA256SUMS independently verified.
- Standalone original-clause implication study commit `7efcf7a80dc8444afcc6cc9a3c573f685e6c6351`:
  [Actions #40987636924](https://github.com/PhysicsQoo/QuPRS/actions/runs/40987636924) **SUCCESS**,
  [artifact 12947533493](https://github.com/PhysicsQoo/QuPRS/actions/runs/40987636924/artifacts/12947533493);
  ZIP SHA256 `1abfb222caf105f164d9b76c77952878cd1c871870121c4b37354c34e8dc58fa`,
  ZIP CRC PASS and **6/6** internal SHA256SUMS independently verified.
  This second job reused previous sealed CNF/NNF and native-phase evidence,
  **zero additional GPMC Solver calls**.

### 1. Python QFT16: actual 113-bit SymEngine-to-GPMC weights

The original two QFT16 QASM hashes still matched:
`39b6889497a4e98098b6bb2b4563ace2fb660f4cc3fe8d0763d3f69fc200d865` /
`aa85188d731454bd85b0fe2ae089ab8e6b812501730eee5f1651ac11d7b7fcbc`.
The pinned dev Python public `wmc_only` API executed **one** native GPMC
call; outcome `unknown`, printed-only `equivalent`, reason
`single_pass_uncertified_insufficient_printed_resolution`.
Its CNF SHA256 was
`20ee9e55eb1fc644d08daf130d180ded46f06f67897fa46f57b4f4ef4ef7f8f1`,
**byte-identical** to the previous independently preserved Phase 6
`qft16-baseline.cnf`. The first study script accidentally used
a 61-character incomplete expected SHA and consequently marked its
`matching_phase6_cnf` diagnostic false; the *actual* emitted SHA
had always been the correct 64-character value. This bookkeeping
error was corrected in the experiment branch and the offline recheck
compared both source CNF byte hashes exactly; it did not rerun QFT.

All **400/400** emitted Path-sum `P_to_wlogi` phase expressions,
in the actual encoded order, evaluated to explicit **rational**
numbers in symbolic representation. In particular, source
coefficients such as
`13703711448578501/36028797018963968` show that preserving
an *exact rational value already produced by Qiskit/Path-sum* is
not automatically preserving the *original ideal QASM angle*.
This distinction is essential.

A separate 384-bit MPFR **directed-rounding interval** oracle,
including interval `pi`, exact rational numerator/denominator
conversion and globally Lipschitz sine/cosine enclosure,
compared each exact displayed CNF decimal to the ideal complex
phase for that **encoded symbolic rational**. The maximum certified
component-L1 complex difference was

```text
max_j |w_CNF,j - exp(2*pi*i * rational_phase_j)|_1
    <= 9.021117345986986392e-34  < 2^-100  < 2^-49
```

This is an actual **per-weight proof for all 400 observed QFT16
Path-sum rational phases**, conditional on the source expression being
faithfully transported into the symbolic rational representation.
It is not a blanket guarantee for arbitrary SymEngine expressions,
for floating QASM inputs, or for arbitrary-angle Qiskit transpilation.
The `evalf(113)` algorithm itself has not been proven correctly
rounded for all expressions; instead the independently directed
interval checks enclose the **actual emitted decimal weights** for
these 400 sources.

The proven `<2^-100` bound can be plugged into the previously derived
structure-sensitive bound for this **same exact CNF**, yielding a
*conditional* trace-magnitude positive within `epsilon_D=1e-8`.
It cannot yet promote the public `unknown`, because
original-QASM-to-encoded-phase semantics and complete
CNF↔d-DNNF equivalence still need independent verification.

### 2. Large CNF/d-DNNF semantic checks without enumeration

An independent PySAT CaDiCaL 1.5.3 gate-Tseitin
XOR miter checked
`CNF != expand(vmap/fixed/free(dDNNF))`.
QPEexact8 baseline (31 variables) and genuine self-negative
(10 variables) both returned **UNSAT** promptly. No independently
checked DRAT/LRAT proof was collected, so this is SAT-backed evidence,
not a proof-carrying certificate.

For each of QFT16 baseline and genuine self-negative, a bounded
**70-second** full SAT-miter attempt exited **124 (timeout)**.
There is no full QFT CNF↔NNF equivalence result from those runs.
The overall Actions job remained success because these timeouts were
explicitly recorded as `NOT_VERIFIED`, not treated as a passing proof.

A separate, more effective *one-direction theorem check* was run
on the exact same four originally sealed CNF/NNF byte pairs.
For every original CNF clause `C_j`, set its literals FALSE and
compute existential satisfiability of the whole d-DNNF under that
partial assignment. This is exact under the verified
**AND decomposability** property; OR combines satisfiable branches.
Python arbitrary-size integer bitsets process **all clauses
simultaneously**, without enumerating assignments, running the
native GPMC a second time or calling SAT on every clause.

| Source-pinned real CNF | CNF clauses | All clauses entailed by NNF? | Independent time |
| --- | ---: | --- | ---: |
| QPEexact8 baseline | 61 | yes | 0.0004s |
| QPEexact8 self-negative | 19 | yes | 0.0001s |
| QFT16 baseline | 1144 | yes | 0.8364s |
| QFT16 self-negative | 1105 | yes | 0.7754s |

Across all **2329/2329** clauses, no assignment represented by the
emitted d-DNNF could violate any original CNF clause. Mapped
original variables were verified complete and unique, and AND
decomposability was independently rechecked.
Thus for these actual four cases the independently interpreted
emitted `d-DNNF => original CNF` implication has a
non-enumerative proof.

**Do not overstate:** the reverse
`original CNF => emitted d-DNNF` is NOT shown for large QFT16.
The single direction plus matching approximate GPMC count does not
prove full logical equivalence. A complete proof could use a
checkable SAT witness or another independently derived exact
CNF model-count certificate; neither is presently available for
QFT16.

### 3. Fair paired GPMC mode A/B on a single Ubuntu runner

Replayed **identical original source-pinned CNF bytes** from the
previous artifact on *one hosted ubuntu-24.04 runner* and *one native
pinned GPMC binary*. Each mode was independently launched three times
in alternating order
`default,ddnnf / ddnnf,default / default,ddnnf` with 90-decimal
working digits, for QPE8 original/negative and QFT16
original/negative, total **24 research-only Solver calls**.
For every CNF, all six native printed complex counts matched
**exactly as rational decimals** across modes and replicates.
The measurements used GNU `time` elapsed seconds and peak RSS kB.

| QFT16 source | Default median | -ddnnf median | Time ratio | Default RSS | -ddnnf RSS | RAM ratio | NNF bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 1.22s | 1.70s | 1.393x | 42168 kB | 96416 kB | 2.286x | 8066131 |
| Self-negative | 1.20s | 1.70s | 1.417x | 42064 kB | 96220 kB | 2.287x | 8014921 |

QPE8 timings were **0.00s** at this time utility's measurement
resolution. Therefore QPE timing ratios are **undefined** and should
not be interpreted as evidence of equivalent performance.
Their small peak RSS differences are not general conclusions.
All these timings are **single hosted-runner exploratory measurements**,
not stable dedicated-host performance guarantees.

**Decision:** `-ddnnf` can deliver a useful structural witness
in the **same** native GPMC invocation, but costs about
39–42% extra native walltime and 2.29x peak memory on this
QFT16 pair. This is NOT currently justified as the default
public production GPMC path. Evaluate an explicit, evidence-driven
opt-in or cheaper in-process count/structure export only after
source and semantic certificates are complete. The existing
default single-Solver contract must remain.

### Progress and outstanding proof obligations

1. **Python weight frontier advanced:** all 400 actual QFT16
   *encoded rational* phases have independently certified
   <2^-100 emitted weight errors. Verify QASM -> Qiskit ->
   encoded rational-phase source meaning separately;
   do not conflate binary64 source angles and exact source QASM.
2. **Large semantics improved:** 2329 exact original clauses
   proved entailed by their d-DNNFs in <2 seconds total,
   while both QFT full XOR SAT-miters timed out at 70s.
   Need the reverse direction for large-CNF formal equivalence.
3. **Runtime decision established:** enabling d-DNNF output
   adds significant memory/time overhead despite one Solver
   call and exact matching counts; keep public default off.
4. Existing public `unknown` statuses, RR-first Hybrid and
   fixed `epsilon_D` are unchanged. Do not replace solver
   numerical model with an empirical observed gap.
5. No new PR, dev/main change, worktree, API policy,
   fixed guard or second Solver run in production.


## Phase 9 — fixed-QFT16 semantic closure with independently checked DRUP, plus fast-path retention

**Date: 2026-10-30.** Continuation only on the existing
`experiment/numerical-tolerance-calibration-20261027` branch.
All actual public-code execution for experimental source studies
remained pinned to `dev` SHA
`55e78c7597966617c1a193b89056ff4e99c3ddfb`;
no public `dev`/`main` changes, new PR, or isolated worktree.
No change to public `RR -> Hybrid -> WMC`, one selected native
WMC invocation, solver precision or distance tolerance.

### A. Original QFT16 source-angle transport to Qiskit and to Python PathSum

First, the actual QFT16 QASM source strings were interpreted as exact
expressions `a*pi+b`, with rational `a,b`. The source file SHA256
identities remained
`39b6889497a4e98098b6bb2b4563ace2fb660f4cc3fe8d0763d3f69fc200d865`
and
`aa85188d731454bd85b0fe2ae089ab8e6b812501730eee5f1651ac11d7b7fcbc`.
The actual installed Qiskit QASM2 reader preserved gate order
and gate identity.

- Native QFT16: 408 `Rx/Ry/Rz` rotations, all textual rational
  multiples of `pi`; directed 384-bit MPFR total circuit
  operator-norm `QASM angle -> Qiskit binary64 angle` bound
  `2.7554581010756223e-15`.
- Transpiled QFT16: 279 rotations, including 260 rational-`pi`
  and 19 literal decimal-radian rotations; the corresponding bound
  is `2.5228091399995012e-15`.
- Both circuits' angle-conversion bounds add to
  `5.2782672410751235e-15` by telescoping the rotation
  unitary gate differences (each bounded by half the angle gap),
  **conditional on standard ideal Rx/Ry/Rz gate semantics**.

Source-mapping research commit
`dd7041583dcfecab60238a9b4bade4fddca629d9`,
[Actions #40988974715](https://github.com/PhysicsQoo/QuPRS/actions/runs/40988974715)
**SUCCESS**, [artifact 12947708815](https://github.com/PhysicsQoo/QuPRS/actions/runs/40988974715/artifacts/12947708815),
ZIP SHA256
`b1db6504bacabcb195271e4ad0069bb2b5f1f8f0f51074a8c9964df8e076f725`,
ZIP CRC and **17/17** SHA256SUMS verified.

A follow-up source-transport audit independently evaluated the *actual
installed* `QuPRS.utils.util.div_pi(theta)` for **every QFT16
rotation**, comparing the returned `SymEngine Rational` against the
exact corresponding binary64 `float(theta/np.pi)`. It enclosed the
direct error from the original exact QASM angle to the
`div_pi(theta)*pi` angle using 384-bit outward-rounded MPFR.

The actual `div_pi` conversion bound was **much smaller** than
the previous intermediate QASM-to-Qiskit error estimate:

| Source QFT16 circuit | Rotations checked | Direct total operator-norm bound, source QASM -> Python PathSum `div_pi` |
| --- | ---: | ---: |
| Native | 408 | 2.2841499771392332e-114 |
| Transpiled | 279 | 9.7306251010202006e-16 |
| Both | 687 | 9.7306251010202006e-16 |

The native QASM rotation ratios largely cancel their intermediate
binary64 rounding when divided by the same `np.pi`; these are
*directly enclosed actual coefficients*, not a general rule
about Qiskit rounding.
The transpiled source still contains 19 decimal-radian rotations.
No snapping to the nearest rational-`pi` value was performed.

Follow-up experiment commit
`18a46e723086865c081778707ca56f9284ced96f`,
[Actions #40990378475](https://github.com/PhysicsQoo/QuPRS/actions/runs/40990378475)
**SUCCESS**, [artifact 12949176144](https://github.com/PhysicsQoo/QuPRS/actions/runs/40990378475/artifacts/12949176144),
ZIP SHA256
`66f6dcf185fc3103daf55fb89c65cde8040cd473c1707e9d5d09d9f59e431c31`,
ZIP CRC and **7/7** SHA256SUMS independently verified.

**Limits:** These are source-angle-conversion bounds conditional
on the implemented `Rx,Ry,Rz` matching the textbook unitary gates;
they do not independently certify the full PathSum gate implementation,
reduction rules, or equivalence-preserving Qiskit transpilation.
The earlier Phase 8 MPFR study independently bounds the
**400 actual encoded rational phases -> CNF weights** by
`9.021117345986986392e-34` per complex L1 weight.

### B. The large QFT16 CNF <=> d-DNNF Boolean semantics are now checked for both fixed cases

Prior Phase 8 independently verified every original CNF clause
`dDNNF => CNF` (QFT baseline 1144/1144; QFT self-negative
1105/1105), including variable mapping and AND decomposability.
Direct large d-DNNF-XOR-SAT verification had timed out,
so the next research did **not** rerun that 200k-node SAT miter.

Instead, a two-copy original-CNF *functional extension* SAT miter
shares exactly the PathSum path variables (baseline 70;
self-negative 64) while independently duplicating the 16
output bits and all phase-weight/Tseitin variables.
The miter adds the condition that at least one derived variable differs.
Its UNSAT proves a given free-path assignment determines **at most
one** complete original-CNF assignment.
Thus the original CNF model count is at most `2^k`.
Independent exact integer evaluation of the verified deterministic,
decomposable NNF produces **exactly `2^k`** models.
Since NNF models are a subset of CNF models and saturate
the CNF upper bound, the two Boolean formulas are equal.

A first SAT check using independent CaDiCaL returned
UNSAT in under 0.02 s for each QFT16 case.
Experiment commit
`8ea36571d9281359decf445d97639e2d0f1cb2e9`,
[Actions #40989426673](https://github.com/PhysicsQoo/QuPRS/actions/runs/40989426673)
**SUCCESS**, [artifact 12947694405](https://github.com/PhysicsQoo/QuPRS/actions/runs/40989426673/artifacts/12947694405);
ZIP SHA256
`d73ac63345afdc921086d7845e507fdde5d63079978f195fa13f68afa04ee771`,
ZIP CRC and **5/5** internal SHA256SUMS verified.

To avoid trusting a black-box SAT status alone, a second
Glucose4 `with_proof=True` run emitted complete **DRUP
refutations** of the actual two-copy CNF formula, and a
separate self-contained checker independently validated **each
RUP clause addition** by assumption-based unit propagation.
Deletions are safely ignored (retained earlier clauses have already
been proven implied), and both proofs ended with the independently
checked empty clause.

| Fixed QFT16 case | Original vars | Independent NNF models | Functional miter clauses | Checked DRUP additions | Checked empty clause |
| --- | ---: | ---: | ---: | ---: | --- |
| Baseline | 486 | 2^70 | 3953 | 1297 | yes |
| `Rz(0.01)` self-negative | 465 | 2^64 | 3815 | 1225 | yes |

The original CNF / emitted NNF exact SHA256 identities and generated
functional-miter CNF / DRUP SHA256 are in the evidence artifact.
The RUP checker took about **3.07 / 2.42 seconds** respectively
in this *offline* hosted-runner study.
Both fixed statements now admit a **checked Boolean proof**:
```
CNF == emitted(d-DNNF), for precisely these source-pinned instances.
```

Checked-proof experiment commit
`86736e7665344c7847148009086f86c138323114`,
[Actions #40989900413](https://github.com/PhysicsQoo/QuPRS/actions/runs/40989900413)
**SUCCESS**, [artifact 12949160325](https://github.com/PhysicsQoo/QuPRS/actions/runs/40989900413/artifacts/12949160325);
ZIP SHA256
`251ccc3a6238761d50f084870a3cd0896a38ab51643993e258f24e23d6b297d0`,
ZIP CRC and **9/9** internal SHA256SUMS independently verified.

**Limits:** The proof validates two fixed Boolean CNF↔d-DNNF
semantics, **not** all future CNFs, the GPMC compiler generally,
arbitrary-angle QASM-to-PathSum semantics or the entire solver's
floating arithmetic. However, *for these exact pinned CNFs*, the
independent rational NNF evaluator now has a checked semantic basis
for **exact weighted counting of the displayed decimal input
weights**. This is stronger than the previous conditional
compiler-faithfulness hypothesis.

### C. No micro-precision performance regression in the production path

This is a *binding promotion criterion for research candidates*, not
a claim that a modified production runtime has already passed CI.
The production branch remains unchanged.

1. Keep `RR -> Hybrid -> WMC` and original RR tolerance/reduction
   hit rate; **RR-resolved Hybrid must never launch GPMC**.
2. At most **one native Solver invocation** per WMC stage; never
   replay GPMC to establish confidence in ordinary verification.
3. Do **not** turn on `-ddnnf` globally: the matched real QFT16
   study measured **1.39–1.42x** elapsed time and **~2.29x** peak
   RSS compared with default, for identical output counts.
4. No automatic `Fraction` re-evaluation of large d-DNNFs,
   no SAT/DRUP/MPFR proving subprocess, and no 200k-node NNF
   expansion in the ordinary public fast path. Keep these in
   separate research or release-admission diagnostics.
5. Source-angle provenance, weighted counting theorem and
   trusted precision metadata may be precomputed for pinned
   benchmark fixtures, but general public inputs cannot be
   silently assigned those benchmark-specific guarantees.
6. Scientific ambiguity can remain `unknown` only when
   the **actual** evidence interval crosses the requested
   distance boundary. Do not force an answer with a fixed
   empirical `3e-9` guard, change the user's epsilon or
   introduce `wmc_policy`.
7. Before any production promotion, demand actual
   same-environment **end-to-end Python/Rust and GPMC/Ganak
   correctness + CodSpeed v5 full benchmark-set** regressions:
   representative QPE, QFT, QAOA and Grover, not one cherry-picked
   benchmark, including native walltime and RSS. No meaningful
   performance or algorithmic regression is acceptable for
   handling numerical noise.

**Decision:** Fixed QFT16 source/Boolean evidence is substantially
closed, and the research-only exact oracle can be used as a
release correctness fixture. A *general-purpose cheap
Solver-arithmetic error enclosure* is still required before
altering the public WMC classifier. Do NOT equate the exact
CNF/NNF proof with an unconditional guarantee about GPMC
MPFR arithmetic on every future input. The right next design
is lightweight one-pass numerical evidence or bounded native
rounding guarantees, with all heavy proof tooling offline.


## Phase 10 — actual single-pass GPMC complex-operation census, no production regression

**2026-10-30 | existing research branch only.**
Research commit `d273e04f1bd27d9825346990141f4fe5a82d4e94`.
[Actions #40992318009](https://github.com/PhysicsQoo/QuPRS/actions/runs/40992318009)
**SUCCESS**, native evidence
[artifact 12950085687](https://github.com/PhysicsQoo/QuPRS/actions/runs/40992318009/artifacts/12950085687),
ZIP SHA256
`2e96e9106b194120bd818468c761bd58b38d5e1da1f1414afedfac336afaac56`.
ZIP CRC PASS; **54/54** internal SHA256SUMS independently checked.

Source-gitlink pinned to
`a1bda3489e959d3695b6798d327c5a1fc1bed305`;
unchanged public dev `55e78c7597966617c1a193b89056ff4e99c3ddfb`.

### Native arithmetic operation trace and fidelity

An ephemeral off-repository copy of GPMC was compiled once without
modifications and once with **only** research counters inserted into
`ComplexMPFR.cc` for the two complex addition and two complex
multiplication operators (`+`, `+=`, `*`, `*=`).
No d-DNNF output, high-precision second solve, auxiliary model
counter or extra arithmetic pass was enabled. Original and
instrumented binary hashes and a separately hashed patch source
are sealed in the JSON artifact. No public GPMC upstream
source/submodule was changed.

The **same source-pinned CNF** was solved at 90 decimal digits
by both binaries in alternating order, three repeats per binary,
on the same hosted Ubuntu 24.04 runner. All **24/24** native
printed complex WMC counts were identical as exact decimal text.

| Real source CNF | Complex additions | Complex multiplications | Native MPFR precision bits |
| --- | ---: | ---: | ---: |
| QPEexact8 baseline | 40 | 128 | 299 |
| QPEexact8 source-negative | 8 | 11 | 299 |
| QFT16 baseline | 134423 | 1387897 | 299 |
| QFT16 source-negative | 134327 | 1387572 | 299 |

The QFT16 baseline's `K` is **1,522,320** actual
recorded complex operations, versus the previous engineering
estimate that used a variable-only `2^(2*n)` error growth.
The binary64 input source-error and Solver MPFR arithmetic remain
separate problems.

### Same-host controlled performance

| Real CNF | Original GPMC median | Probe median | Original peak RSS | Probe peak RSS |
| --- | ---: | ---: | ---: | ---: |
| QFT16 baseline | 1.20s | 1.20s | 41992 kB | 42068 kB |
| QFT16 source-negative | 1.20s | 1.20s | 42080 kB | 42040 kB |

The QPE8 timings are <0.01s and cannot support
a meaningful timing ratio; QFT16 ratios were **1.00x** at
0.01-second timing resolution. Peak RSS was approximately
unchanged. This is **not** a production CodSpeed regression
certificate or evidence of mathematically zero overhead.
The production binary was not modified at all, which
guarantees no introduced production-path overhead for this
research-only study.

### Candidate mathematical upper bound, not yet Solver-certified

Source review identified literal decimal inputs being converted by
MPFR and `ComplexMPFR` complex operations:
two scalar rounded additions for each complex addition,
and four scalar rounded products plus two rounded component
sums/differences for each complex multiplication.
When all operations are normal and MPFR uses nearest rounding at
precision `p`, the standard per-operation relative bound
`u=2^-p` implies a conservative complex Euclidean
relative primitive error coefficient no worse than `16u`
for an addition or multiplication.

If all numerical processing of the root WMC is faithfully
accounted for by a positive-coefficient weighted
sum-of-products circuit using those operators, its cached-DAG
multiplicities and nontrivial preprocessing are correct,
and `K` is a genuine upper bound on the operation depth of
every expanded monomial, then for `m` numerical phase weights,
`N_sat` feasible models and phase modulus bound `M`:

```text
u = 2^(-p)
t = 16 * (K + m + 1) * u ; require 0 <= t < 1
S = N_sat * M^m
E_solver_count <= S * t/(1-t)
E_solver_normalized <= E_solver_count / 2^(normalization_twice/2).
```

The `t/(1-t)` form bounds
`(1+16u)^(K+m+1)-1` without gigantic rational exponentiation.
This is **a candidate engineering enclosure pending
a complete implementation-level proof**, not an existing
GPMC arithmetic certificate. Specific gaps:
complete inventory of MPFR pathways (including preprocessing,
cache reuse and exact shifts), verification of no exponent
range/underflow/overflow issues, faithful arithmetic DAG
semantics for arbitrary CNF, correct numeric input parsing,
and treatment of final decimal printer rounding. The older
`2^(2*n+20-b)` is also uncertified; do not silently replace
one assumption by another in dev.

For the four **fixed, already independently certified Boolean
CNF/d-DNNF** examples, the resulting **candidate** normalized
absolute complex Solver error bounds are:

| Real source CNF | Candidate normalized Solver error | Independently observed normalized native GPMC-vs-exact-NNF component discrepancy |
| --- | ---: | ---: |
| QPEexact8 baseline | 2.922e-87 | 2.123e-90 |
| QPEexact8 source-negative | 3.456e-88 | 4.665e-93 |
| QFT16 baseline | 1.254e-77 | 3.703e-90 |
| QFT16 source-negative | 1.567e-78 | 7.580e-90 |

Every empirical original-vs-oracle gap lies **inside** the
hypothesized bound, by roughly 1e3 through 3e12 factors.
Agreement does not prove the bound for unseen cases.

### Conditional numerical decisions with already proven weight errors

Combining the new **candidate solver** radius with the earlier
**actually MPFR-certified source-weight** radius and the
strict rational squared distance comparison at
`epsilon_D=1e-8` gives the following *research-only*
statuses for these fixed examples:

| Real source miter | Source-weight assumption/certificate | Conditional distance status |
| --- | --- | --- |
| QPEexact8 baseline | Actual 17 native weights, delta <= 3.3e-16 | `unknown` |
| QPEexact8 self-negative | Actual 2 native weights, delta <= 1.7963e-17 | `not_equivalent` |
| QFT16 baseline | All 400 encoded phases, delta <= 9.022e-34 | `within_distance` |
| QFT16 self-negative | delta <= 2^-49 still not separately certified for this exact altered phase corpus | `not_equivalent` **conditional on that delta** |

The result is **not** authorization to return `equivalent` in
the current public Python/Rust API. It is a sharply delimited
scientific route to prove the real QFT positive result at
negligible runtime cost, **after** the native Solver-arithmetic
error certificate is closed, per-source input semantics are
included, and stdout print resolution is accounted for.
The original QPE8 baseline remains `unknown` at its
observed f64 source accuracy. We must not hide that
uncertainty by changing epsilon or inventing a global guard.

### Release engineering decision

Keep existing production `RR -> Hybrid -> WMC`
dispatch and exactly one chosen GPMC/Ganak invocation.
Do **not** add `-ddnnf`, exact Fraction WMC,
native SAT/DRUP, MPFR directed interval recomputation
or a repeated high-precision GPMC solve to the ordinary
verifier hot path.

Candidate native counters are low-overhead on QFT16 in this
limited run, but they do not yet constitute complete error
provenance and are not generally proven free of overhead.
Before a PR, finish the numerical implementation proof and
compare proposed *actual public binary* behavior across
Python/Rust, both Solvers, QFT/QPE/QAOA/Grover, walltime/RSS
and the complete CodSpeed v5 suite.
Only a conclusive, performance-neutral or performance-positive
candidate should move into dev.


## Phase 11 — MPFR input/output and *a posteriori* exact WMC arithmetic evidence

**2026-10-30, research-only.** All source and tests remain on
`experiment/numerical-tolerance-calibration-20261027`;
pinned public `dev` is
`55e78c7597966617c1a193b89056ff4e99c3ddfb`.
The public verifier, its selected Solver and the one-solve
`RR -> Hybrid -> WMC` fast path were not modified.

### A. Audited original native weighted-count arithmetic sources

Inspected exactly pinned GPMC source gitlink
`a1bda3489e959d3695b6798d327c5a1fc1bed305`.

| Stage | Actual GPMC source | Count-path numerical behavior | Proof status |
| --- | --- | --- | --- |
| Decimal literals | `core/Instance.cc`, `mpfr/mpreal.h` | Input decimal strings converted to nearest MPFR at p bits; complex literal fields stored independently | Independently checked on all four fixed CNFs |
| Preprocessor | `preprocessor/Preprocessor.cc` | Equivalent-variable weights combined with `*=`; compacted/free/assigned weights merged into `gweight` using `+` and `*=` | Arithmetic through covered operators; full general semantic preservation not formally proved |
| Component decomposition | `core/Component.h`, `core/ComponentManager.cc` | Two-branch counts added; component products, branch weights and isolated weights combined by `+`, `*` | All actual complex operations counted in Phase 10 |
| Component cache | `core/ComponentCache.cc` | Stores/reuses existing complex subcount via assignment; reuse does not invoke a new arithmetic operator | Cached-DAG subcounts are reused (not independent rounding at each use); general same-precision invariants and cache semantic correctness not formally proved |
| Root | `core/Counter.cc` | `totalModels() * gweight` produces final complex WMC; unweighted `<<` shift path distinct | Actual p299 result captured as binary |
| Binary to stdout | `core/Main.cc`, `c-mpfr/ComplexMPFR.cc`, `mpfr/mpreal.h` | Output uses `mpfr_asprintf` with MPFR's default rounding and `cout.precision(90)` | Individually checked with exact rational binary/decimal differences |

**Important diagnostic distinction:** GPMC streams complex
`gweight` values **during preprocessing** before it streams
the final weighted count. A capture that assumes one
`Complex::operator<<` event is incorrect. The corrected
study selects the actual final result and retains all
intermediate stream events as separate evidence.

QFT16 uses **the cache heavily** (original ~133085 cache
hits, true negative ~133020), so the existing precision
experiments cannot be dismissed as cache-free examples.
A correct general proof must treat cache entries as
**shared DAG nodes** with one rounded value reused
multiple times, not as fresh exact values.

### B. Exact native MPFR input and printer tests

Research source commit
`baf64ddaad1217999675eed8d49b54a1e73ad41b`,
[Actions #40994462820](https://github.com/PhysicsQoo/QuPRS/actions/runs/40994462820)
**SUCCESS**,
[artifact 12950164358](https://github.com/PhysicsQoo/QuPRS/actions/runs/40994462820/artifacts/12950164358).
ZIP SHA256
`cf4d13357117e9488e496175bf24643f0a0720a3ec2a284053be07ba6a0999b7`;
ZIP CRC and all **13/13** SHA256SUMS independently checked.
An isolated scratch build instruments only the original
Complex output stream, not preprocessing, cache, count algorithm
or public binary.

Independent MPFR `mpfr_set_str` at p=299 nearest and
base-2 exact MPFR extraction checked every positive and
negative literal's printed decimal real and imaginary values.
Each component satisfied the appropriate nearest relative
binary rounding bound; the largest **complex L1** decimal
to MPFR input error was:

| Fixed CNF | Original literal weight records | Maximum absolute input L1 rounding |
| --- | ---: | ---: |
| QPEexact8 baseline | 34 | 3.90343178e-91 |
| QPEexact8 self-negative | 4 | 3.77318235e-91 |
| QFT16 baseline | 800 | 7.12783337e-91 |
| QFT16 self-negative | 770 | 6.74271748e-91 |

For **all four actual native final weighted counts**, the
rounding mode was nearest (`rnd=0`), p=299 on both complex
components; underflow, overflow, NaN, erange flags were all
zero and both components were finite. Status was captured
**before** `PrintLog10`, which may compute log10 of a negative
real component and set unrelated MPFR flags.

The exact MPFR binary count and the actual
`mpfr_asprintf("%.90Rg")`-style printed decimal count
were compared with integer `Fraction` arithmetic.
Both components of all four results fell within the
**90-significant-digit half-last-place decimal radius**.
For example, QFT16 baseline's imaginary MPFR-to-printer
difference was 2.40833e-75, inside the 5e-75 bound.
The zero- and compact-integer-format corner cases are
covered by the earlier MPFR printer contract study.
All four current examples have a checked final
stdout uncertainty, not an assumed 0.5 for a printed integer.

### C. Exact original binary WMC error for four pinned CNFs

The *independent* original CNF-to-emitted-d-DNNF Boolean
equivalence for both QFT16 cases was previously established
using checkable DRUP refutations in Phase 9. A separate
small QPE baseline/negative direct-CNF-vs-d-DNNF
Boolean XOR miter was subsequently checked via a
Glucose4 proof and an independently implemented RUP verifier:

- QPE8 baseline: CNF 31 vars / 61 clauses; NNF 83 nodes;
  Boolean XOR miter 590 clauses; **196/196 RUP additions
  accepted, empty clause checked**.
- QPE8 self-negative: CNF 10 vars / 19 clauses; NNF one
  node; XOR miter 148 clauses; **32/32 RUP additions
  accepted, empty clause checked**.

That proof used *no GPMC* and closed the prior QPE-baseline
gap (its earlier CaDiCaL UNSAT did not have a checked proof).
The fixed Boolean representations and all original-variable
weight maps are now supported independently.
Research commit `9a2bdada27737494c7a7040f51a5c757ac943b68`,
[Actions #40995487313](https://github.com/PhysicsQoo/QuPRS/actions/runs/40995487313)
**SUCCESS**, [artifact 12951440419](https://github.com/PhysicsQoo/QuPRS/actions/runs/40995487313/artifacts/12951440419),
ZIP SHA256 `6ba0e92256eba4d7e560d192853995f842901e6276b88fbfff64aaa7c2cc347a`,
CRC and **9/9 SHA256SUMS** independently checked.

For those exact byte-pinned inputs, a zero-GPMC-solve
offline audit evaluated the emitted d-DNNF with **exact
rational arithmetic** on the original CNF decimal complex
weights. It subtracted that result from the exact
base-2 MPFR value captured **before decimal printing**.
This determines the native arithmetic difference
*exactly* as a rational number for each fixed pair.

Research source commit
`b541f0302b4023d73ee33e8506efcd23b8ee77c3`,
[Actions #40995096158](https://github.com/PhysicsQoo/QuPRS/actions/runs/40995096158)
**SUCCESS**,
[artifact 12951295547](https://github.com/PhysicsQoo/QuPRS/actions/runs/40995096158/artifacts/12951295547),
ZIP SHA256 `4055b639471a6005c422b49453d478733f426b3987bf3afbcc783d4a3b9ef681`,
CRC and **6/6 SHA256SUMS** verified.

| Fixed source CNF | Exact real-component count error | Exact imag-component count error | Exact normalized complex L1 error |
| --- | ---: | ---: | ---: |
| QPEexact8 baseline | 1.93906e-87 | 3.75434e-87 | 2.779979e-90 |
| QPEexact8 self-negative | 1.31996e-88 | 1.19418e-90 | 5.202747e-91 |
| QFT16 baseline | 2.66149e-75 | 1.07475e-74 | 5.954776e-90 |
| QFT16 self-negative | 2.08519e-75 | 1.16913e-76 | 7.823458e-90 |

These are verified **exact-input, fixed-instance arithmetic
error measurements**, not a general Solver error theorem.
Unlike previous differences derived from the printed
decimal result, these values exclude printer-rounding
uncertainty altogether.

The Phase 10 engineering candidate
`S * t/(1-t)`, `t=16*2^-p*(K+m+1)`,
contains all four independently measured errors.
This is *evidence of conservative behavior on the four
source-pinned instances*, **not a proof** of the candidate
enclosure on all future circuits.

### D. Mathematical primitives and global proof boundary

With MPFR round-to-nearest, p=299, all values finite and
normal and `u=2^-p`, each real `mpfr_add` or
`mpfr_mul` satisfies the standard relative rounding
bound. Consequently, for the exact complex inputs
`a,b`, the current four-real-product/two-sum
implementation obeys conservative local norm bounds:

```text
||fl(a+b)-(a+b)||_2 <= u (||a||_2 + ||b||_2)
||fl(a*b)-(a*b)||_2 <= sqrt(2) * (2*u + u^2) ||a||_2 ||b||_2
```

The larger coefficient `16u` used in Phase 10
is deliberately conservative for these isolated primitives.
Nearest input conversion contributes a separately checked
rounding term; final decimal output has another separately
checked half-last-place term.

To lift those primitive theorems into a **general**
`N_sat M^m * ((1+16u)^(K+m+1)-1)`
global error enclosure, the following implementation-level
obligations remain:

1. **Arithmetic graph completeness:** prove the entire
   executed WMC calculation is a faithful nonnegative-
   coefficient sum-of-products DAG in the exact original
   literal weights, including weighted preprocessing.
   The `K` native counter only observes the four
   `ComplexMPFR` operators; no uncovered rounded arithmetic,
   precision-changing conversion or arithmetic-dependent
   branch may silently enter the accepted certificate.
2. **Cache precision and semantics:** prove cached values
   are copied without extra precision loss at the same p
   and the cached-DAG expansion represents each exact
   original weighted model appropriately.
3. **Exponent and rounding completeness:** establish
   normal-operation invariants for *arbitrary accepted
   inputs*, not only the four flag-clean samples,
   and handle special values and cancellation explicitly.
4. **General cost and input provenance:** establish a
   cheap, sound upper bound for `K`, `N_sat`, `m`
   and `M` available during the **single** native WMC
   call, without constructing a full d-DNNF or rerunning
   GPMC. Distinguish the exact source angle error from
   Solver input decimal parsing and count arithmetic.
5. **Solver separation:** do not apply GPMC-specific
   error claims to Ganak without an independent native
   implementation audit.

The four fixed QFT/QPE outputs are now much more
strongly certified as research oracle fixtures.
However, **a fully general inexpensive GPMC
counting-error bound is not yet proved**.
A release classifier cannot simply adopt the Phase 10
candidate. In particular, do not replace `unknown` by
`equivalent` solely because these fixed tests have
very small MPFR count errors.

### E. Production performance and release boundary

The ordinary dev/main verifier is unchanged. All
directed MPFR, fractional WMC, SAT/DRUP, NNF and
GPMC replays above were opt-in research only.
The prior source-pinned same-run baseline/probe
study found no measurable QFT16 time regression
at 0.01s timing resolution; this is not a
CodSpeed-wide production benchmark.

No blanket `-ddnnf`, extra solver call, large
Fraction computation, extra proof checking, or
new fixed `3e-9` guard is acceptable in
the public verification path. Keep RR-first,
single Solver per WMC stage and genuine `unknown`
when evidence is insufficient.

Before any dev promotion, independently prove
the remaining global DAG and metadata-bound
obligations, then benchmark the *actual proposed
Python/Rust public binaries* and Ganak/GPMC
on representative QPE/QFT/QAOA/Grover and
full CodSpeed v5. Any new correctness metadata
must be designed to avoid material regression.


## Phase 12 — GPMC weighted preprocessing/cache proof obligations and bounded structural A/B

**2026-10-30 | existing experimental branch only.**
Public `dev` and `main` unchanged. All tests used the original
GPMC gitlink `a1bda3489e959d3695b6798d327c5a1fc1bed305`
and the previously SHA256-pinned real QPEexact8/QFT16 positive and
physically changed negative CNFs. No production API/classifier edits,
no PR, no additional public WMC calls.

### Proven primitive facts versus unsupported global conclusion

Original `ComplexMPFR.cc` performs a complex addition as two real
MPFR additions, and a multiplication as four real MPFR products
plus two rounded sum/differences. Provided MPFR round-to-nearest
with no exceptional results at precision `p`, writing `u=2^-p`:

```
||fl(a + b) - (a+b)||_2 <= u*(||a||_2 + ||b||_2)

||fl(a*b) - (a*b)||_2 <= sqrt(2)*(2u+u^2)*||a||_2*||b||_2
```

The copy constructor in `mpfr/mpreal.h` constructs at the
**source's precision** then calls `mpfr_set`; assignment resizes
its destination to the source's precision before copying. Thus a
cache hit copying a normal finite, already-rounded value at the
same precision does not introduce new rounding error. The
`Complex::operator<<` operation multiplies by a power of two
and is exact unless an exceptional exponent-range event occurs.
These source-level properties strengthen *numeric* invariants
but **do not prove cache-key semantic correctness** or weighted
preprocessing equivalence.

The preprocessing source specifically contains:
- `Preprocessor::MergeAdjEquivs` multiplying literal weights
  when merging equivalent variables;
- `Preprocessor::Compact` accumulating eliminated/free/assigned
  weights with `gweight *= (w_positive + w_negative)`
  or `gweight *= w_assigned`;
- `Preprocessor::pickDefVars` testing equality of *rounded*
  positive and negative weights to decide whether a projected
  variable may be considered for elimination.

The last branch is mathematically delicate: exact source decimal
weights may round to equal binary MPFR values even when the original
decimals differ. Any general certificate must compare against the
**rounded-input WMC**, with a separate rigorous source-decimal-to-
binary perturbation bound. It may not pretend that preprocessor
decisions were made with exact original rational weights.

The `ComponentCache::requestValueOf` path returns
`pcomp->model_count()` without recomputation. An operation-depth
or `K` theorem must therefore cover a **shared arithmetic DAG**:
once-rounded cached subexpressions can be reused in several
monomials. Merely multiplying raw `K` by `u` does not prove
faithful polynomial correspondence or model multiplicity.

A general weighted-roundoff enclosure of the form
`N_sat * M^m * gamma(K)` is **conditional** on an
implementation proof that preprocessing, SAT/branching,
cache identity and root normalization represent the original
CNF's weighted-model polynomial exactly *for the quantized
weights*. Even though the four pinned cases now have independently
checked CNF <=> d-DNNF semantics and exact WMC references,
this conditional theorem cannot be silently promoted to all
GPMC inputs or Ganak.

### Critical low-cache crash boundary (not a numerical misclassification)

The first scoped [Actions #40996438726](https://github.com/PhysicsQoo/QuPRS/actions/runs/40996438726),
source SHA `ea7ec5fc317a960473cab509ab919c93fce2b026`,
was **SUCCESS as a bounded diagnostic study** but its
`-cs=1` low-cache subcases **FAILED** with GPMC's
`*** INTERRUPTED by signal 11 ***`, exit status 1.
It is incorrect to count those variants as passing numerical
comparisons. Its sealed [artifact 12951910698](https://github.com/PhysicsQoo/QuPRS/actions/runs/40996438726/artifacts/12951910698)
ZIP SHA256 `7c1ac17e5360430002d54788e3cbf618b149d92968c5e8f59c36536a8c15691c`,
CRC and **37/37 SHA256SUMS** independently verified, preserves
the failing original stdout.

Source evidence provides a strong mechanistic explanation:
`ComponentCache::init` preallocates `table_.resize(900001,NULL)`,
whose pointer storage alone is at least 7,200,008 bytes
(6.87 MiB on a 64-bit platform), exceeding a 1 MiB cap.
`createEntryFor` calls `deleteEntries()` once the
cache accounting exceeds that cap. `deleteEntries` then
performs `scores[scores.size()/2]` without testing for an
empty `scores` vector. When no deletable entries exist,
that is an out-of-bounds access and plausible root cause
for the immediately observed signal 11. **This mechanism
is source-supported but has not been independently proven
as the unique root cause via a debugger.**

This is a *cache configuration safety defect*, not evidence
that default GPMC numerical arithmetic is wrong. Do not
change production caching, its memory policy, or the pinned
GPMC submodule as an unreviewed numerical-tolerance fix.

### Fair source-pinned GPMC preprocessing/cache controls

A second [Actions #40996838428](https://github.com/PhysicsQoo/QuPRS/actions/runs/40996838428)
at source `1ad3fbce5efda7f623eaf980a672acfc01b179ad`
**SUCCESS**,
[artifact 12952125653](https://github.com/PhysicsQoo/QuPRS/actions/runs/40996838428/artifacts/12952125653),
ZIP SHA256 `7df6d71b05e863cc49aea37dd5e99796c4b2c58ba1b2e5b501bf1ce464b6298f`,
ZIP CRC and **37/37 SHA256SUMS** independently verified.

Reused the exact native, noninstrumented GPMC binary on one
hosted ubuntu-24.04 runner. Each of four original source-pinned
CNFs was solved **once per configuration**:
default; `-varlim=0` (skips *preprocessing main
loop*, but **not** initial SAT_FLE); `-cs=16` (16 MB
cache budget, **not disabled**); and both changes.
These 16 solves were **research-only**, not production
multi-solve behavior.

| QFT16 source | Default | `-varlim=0` | `-cs=16` | Both |
| --- | ---: | ---: | ---: | ---: |
| Baseline native walltime | 0.77 s | 0.93 s | 0.79 s | 0.99 s |
| Baseline peak RSS | 42.2 MB | 44.1 MB | 31.4 MB | 31.3 MB |
| Negative native walltime | 0.76 s | 0.95 s | 0.79 s | 0.98 s |
| Negative peak RSS | 42.1 MB | 44.2 MB | 31.2 MB | 31.1 MB |

The original QPE baseline, its genuine source-negative and
the QFT16 baseline showed **identical printed 90-digit complex
counts across all four configurations**.
The QFT16 negative case showed a precisely
parsed **4.0436230253302736e-90** normalized complex L1
difference when `-varlim=0`, with or without `-cs=16`;
all variants lay beneath a **research alarm threshold
1e-70**, which is **not** a proven GPMC error bound,
production guard or classification tolerance.

**Performance interpretation:** On this *single* hosted
runner, reducing preprocessing raised QFT16 native walltime
by approximately **21–25%**, whereas the 16 MB cache cap
slightly raised walltime and reduced RSS. This does not
justify changing normal preprocessing/cache settings,
does not prove correctness for arbitrary CNFs, and is
not CodSpeed v5 verification. Measurements from different
hosted runs are not interchangeable.

### Remaining theorem and production promotion criteria

1. Formally prove the original WMC polynomial correspondence
   across `SAT_FLE`, variable elimination, equivalence
   merging and cache-key reuse, using the **quantized
   input weights** as the numerical reference.
2. Prove K encompasses every rounded counting operation
   including root and weighted preprocessing, and specify
   safe rounding/exponent/overflow assumptions; the
   source-identified copy/shift operations are exact in
   their normal range.
3. Derive a cheap, sound **per-request**
   `N_sat` or relevant original-CNF model upper bound:
   `2^(all DIMACS variables)` is formally safe but so loose
   on QFT/QPE that it defeats the classifier.
   Source path-variable counts can improve this only when
   the encoder's deterministic extension property has a
   general proof, not only the fixed CNF DRUP fixtures.
4. Keep fixed source-angle/weight bounds separate from
   solver precision and stdout printing, and keep Ganak
   independent.
5. Run actual public Python/Rust and GPMC/Ganak
   correctness plus the **full CodSpeed v5** suite before
   any dev promotion. The intended stable path retains
   RR-first Hybrid and **one** Solver per WMC stage,
   with no default `-ddnnf`, SAT, DRUP, Fraction WMC
   or directed-MPFR per-request computation.

**Decision:** Phase 12 gives stronger evidence about
cache numerics and flags an independent low-cache crash,
but **does not close the general GPMC forward-error theorem**.
No production classifier change or `unknown` promotion is
authorized by these controls alone.


## Phase 13 — deterministic extension and cheaply available model-count bounds

**2026-10-30 | research-only; existing branch and pinned public dev.**
Experimental source commits:
`1f1a320d52d31b81e0064f9a8267f07849b243ab`
(offline four original CNFs, five adversarial controls) and
`9f4cf10b80f9dcf2ae47703c067714285752b3a4`
(actual pinned-dev Python QFT16 PathSum dependency audit).
Public `dev` remains
`55e78c7597966617c1a193b89056ff4e99c3ddfb`;
neither the solver, classifier nor Python/Rust public API changed.

### Formal model-count lemma and provenance guard

Suppose a particular source-generated CNF is the conjunction
of a base formula `H(X)` with exact Boolean definitions

```
z_1 <-> g_1(X)
z_2 <-> g_2(X)
...
z_m <-> g_m(X)
```

for distinct weighted phase variables `z_i`, with no
unproven forward references or missing converse implication.
Then every base `X` assignment has at most one `Z`
extension, regardless of whether `H(X)` accepts that
assignment. Consequently, **without counting models**:

```text
N_sat(CNF) <= 2^|X| = 2^(n_DIMACS - m_weighted_phase_variables).
```

For the current Python emitter `ps2wmc.py`,
`wlogi_to_clauses` creates one fresh `z_i` per
phase coefficient and `encode_equivalence(z_i, logi)`
emits both directions of the definition (including
constant `True/False` and singleton/AND/OR cases).
For the Rust `WmcManager`, `encode_phase_polynomial`
creates fresh `z_i` and explicitly emits the
`z_i <-> monomial` clauses (including constants
and one/multiple sources). The distinct Rust source
`VariableManager.path_vars` **includes the original
input variables `x_i`**; Python's `pathvar` and Rust's
`path_vars` therefore cannot simply be equated to
the same number of free Boolean degrees of freedom.

The broad bound `2^(n-m)` is safe only when the
input came from the trusted complete phase-definition
emitter, and the clause/literal invariants hold.
**An arbitrary weighted DIMACS with `m` weighted
variables does NOT necessarily have those variables
functionally determined**. Never infer a certificate
merely from the presence of weight comments or
`gpmc_cnf_budget_metadata(n,m,max_sq)` if
source provenance is missing.

### Independent checked DRUP for four real source-pinned CNFs

The same four source-pinned QPEexact8 (Rust) / QFT16
(Python) original and physical source-negative CNFs
were checked offline by two-copy original-CNF SAT
miter, **sharing every nonweighted variable** and
duplicating precisely its weighted `z_i` variables.
A Glucose4 DRUP refutation of the possibility that
the two copies differ was independently checked by
a separate RUP verifier, including the empty clause.

| Source-pinned real CNF | DIMACS `n` | Weighted `m` | Base variables `n-m` | Proved `N_sat` bound | Checked RUP additions |
| --- | ---: | ---: | ---: | --- | ---: |
| Rust QPEexact8 baseline | 31 | 17 | 14 | `2^14` | 39 |
| Rust QPEexact8 self-negative | 10 | 2 | 8 | `2^8` | 4 |
| Python QFT16 baseline | 486 | 400 | 86 | `2^86` | 1160 |
| Python QFT16 self-negative | 465 | 385 | 80 | `2^80` | 1154 |

All four source-pinned Boolean functionals were
UNSAT in the two-copy miter, and all RUP additions
and empty-clause derivations were independently
validated. These checks are fixed-instance
proof certificates, distinct from the source-level
universal lemma. Runtime for each large QFT16
proof/check was **1.42/1.84 seconds** on one
hosted runner; neither required running GPMC.

**Adversarial controls:** five small source-shaped
examples gave three accepted true-function definitions
(AND, XOR, forced phase weight), and two *rejected*
broken encodings (remove one converse AND clause;
leave a weighted variable unconstrained). The two
rejections produced SAT witnesses whose original
CNF assignments were independently checked for
same base / different weighted variable.
Therefore the test does not incorrectly bless an
arbitrary weighted literal.

[Actions #40998197952](https://github.com/PhysicsQoo/QuPRS/actions/runs/40998197952)
**SUCCESS**, immutable
[artifact 12951904243](https://github.com/PhysicsQoo/QuPRS/actions/runs/40998197952/artifacts/12951904243).
ZIP SHA256
`e68fda4f11d893ccc16e7dc1982f11c9a7b16f22e4117c55afc7e8fbe8349c21`,
CRC PASS, **21/21** internal SHA256SUMS independently
verified. Source SHA
`1f1a320d52d31b81e0064f9a8267f07849b243ab`.

### Tighter path-only bounds require another proof obligation

A `2^k` bound based on **only the Path-sum
path variables** additionally requires proving that
every output variable is a Boolean function of the
path variables and perhaps other output functions
on a directed acyclic dependency graph. For
ordinary `PathSum.QuantumCircuit` representation,
input `x_i` symbols may appear directly in outputs,
and the initial inputs must be included in the
free basis unless separately constrained.
Thus a `pathvar` field is not automatically
a universal tight counting bound.

The actual pinned `dev` Python QFT16 API
was run **once** (WMC-only, unchanged public
`unknown` result) to inspect `final_pathsum`
and reproduce the original exact CNF SHA256
`20ee9e55eb1fc644d08daf130d180ded46f06f67897fa46f57b4f4ef4ef7f8f1`.
It contained exactly **70 path variables,
16 output variables and 400 phase weights**.
All 16 output Boolean expressions had *zero*
cross-output dependencies and referenced only
the declared path-variable set. The entire
phase expression used no undeclared symbols.
A deterministic topological output evaluation
therefore certifies at most one output/aux
assignment per path variable assignment:

```text
N_sat(QFT16 baseline) <= 2^70, from the actual PathSum source.
```

This reproduces the tighter Phase 9 fixed QFT16
two-copy SAT+DRUP upper bound by an independent
source-level dependency argument. It does not
make the tight bound valid for every PathSum:
the source proof relies on full emitted iff
definitions and the dependency guard.
Seven synthetic guard controls passed the expected
accept/reject classification, including rejection
of self-dependency, mutual cycles, undeclared
output or phase symbols and output/path overlap.

[Actions #40998482414](https://github.com/PhysicsQoo/QuPRS/actions/runs/40998482414)
**SUCCESS**,
[artifact 12951964651](https://github.com/PhysicsQoo/QuPRS/actions/runs/40998482414/artifacts/12951964651);
ZIP SHA256
`a95fd476fbb325af4dd0dd0a7400a376400a405a10f80b17eec2eb6b62c6a8b5`,
CRC PASS and **5/5** internal SHA256SUMS
independently verified.

The QFT16 source-negative `2^64` tight
bound remains covered by the independent
Phase 9 checked DRUP certificate. No claim
is made that the source-level Python check
was also run on that modified-source case.

### Practical low-cost implementation recommendation

1. Derive a trusted **definitional-phase-literals**
   provenance flag at the existing PathSum encoder
   boundary. When true, `n` and `m` are already
   counted; `N_sat_upper=2^(n-m)` requires no
   SAT, d-DNNF, extra GPMC call, or numerical solve.
2. Permit an optional **tighter** `2^k`
   certificate only if all output/input degrees
   of freedom are accounted for and the
   Boolean-expression dependency graph is
   independently established acyclic.
   Guard against name collision, undeclared
   symbol, self-dependency and incomplete
   helper-variable definitions; otherwise
   **fall back to the conservative trusted-encoder
   `2^(n-m)` bound**.
3. Arbitrary weighted CNF inputs, untrusted
   source exporters and unknown Rust/Python
   side effects must not be assigned the
   trusted-source certificate. Rust source
   `var_map` and initial `x_i` semantics
   must be checked independently from Python.
4. Before any public API promotion, certify
   that the GPMC native arithmetic DAG including
   weighted preprocessing and cache reuse
   faithfully evaluates the emitted quantized
   CNF weight polynomial, and incorporate source
   phase error plus MPFR solver and decimal
   printer rounding independently.
5. A real production candidate must preserve
   RR-first Hybrid and **one WMC Solver call**
   and pass end-to-end Python/Rust + both
   Solvers + **full CodSpeed v5** performance.
   These proof tools stay **offline**; source
   bookkeeping in the hot path should piggyback
   existing symbol/weight collection and must
   be benchmarked before enabling.

**Decision:** Phase 13 closes a substantial
*structural* part of the counting upper-bound
problem for the current trusted encoders and
provides a genuine QFT16 path-only source
certificate. It does **not** finish the
general GPMC native forward-error theorem or
authorize the public verifier to replace an
unresolved `unknown`.

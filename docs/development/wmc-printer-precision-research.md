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

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

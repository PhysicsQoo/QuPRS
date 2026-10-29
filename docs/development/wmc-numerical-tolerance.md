# Weighted-model-counting numerical tolerances

QuPRS distinguishes the **symbolic reduction** tolerance from two WMC
floating-point classification thresholds. These are numerical decision
policies; they do not change PathSum reductions, CNF encoding, Ganak or GPMC.

## User API

~~~python
from QuPRS import check_equivalence

result = check_equivalence(
    original, optimized,
    method="wmc_only", backend="rust", tool_name="ganak",
    wmc_magnitude_tolerance=1e-8,
    wmc_phase_tolerance=1e-8,
)
print(result.equivalent, result.wmc_magnitude_tolerance)
~~~

Both fields are optional, evaluated per call and separately recorded in
the returned result. When omitted, the public API reads defaults from
config.WMC_MAGNITUDE_TOLERANCE and config.WMC_PHASE_TOLERANCE. Explicit values must be finite numbers
strictly between 0 and 1. Invalid values fail before native execution.
config.set_tolerance() governs Python symbolic reduction only; changing
it is **not** a way to tune the WMC numeric classifier. Changing the
process-global RR coefficient tolerance invalidates tolerance-dependent
symbolic caches; it must be a finite positive number (not a bool).
It is not a per-call or thread-local setting.

## Source-phase preservation versus RR matching

For the Python backend, gate construction preserves nonzero input phase
coefficients even when individual coefficients are smaller than
`config.TOLERANCE`. The Elim/HH/omega matching rules retain their
existing local coefficient tolerance. This separation prevents
an accumulation of tiny rotations from being silently erased
before RR/Hybrid or WMC-only examines the resulting circuit.

For example, `Rz(3e-6)` repeated 200 times is the same rotation as
`Rz(0.0006)`, with projective Hilbert--Schmidt distance from
identity `abs(sin(0.0006/2)) ≈ 3e-4` and ideal normalized
trace-magnitude defect `1 - abs(cos(0.0006/2)) ≈ 4.5e-8`.
With an RR coefficient tolerance of `1e-6`, the old gate-local
snapping policy could erase all 200 small rotations even though the
combined rotation exceeds a WMC magnitude tolerance of `1e-8`.
The phase-preserving construction keeps both representations visible
to WMC and lets RR report `unknown` when reduction is incomplete.

This is a correctness fix for premature phase deletion, **not** a
mathematical proof that arbitrary repeated approximate RR reductions
have an error bound, or that Ganak/GPMC can certify QCEC's
`1e-8` projective circuit-distance tolerance. In controlled
identity tests, Ganak's rounded complex count has exhibited normalized
magnitude errors around `9.3e-10` (60 H gates) and `2.0e-9`
(80 H gates). The current WMC public default `1e-8` remains unchanged;
these depth-specific observations are not universal error estimates.

All **Python, PyO3 and Rust crate API** defaults are magnitude 1e-8 and
phase 1e-8. These are numerical heuristics, not exact certificates. The
historical Rust direct-call values were 1e-6 each; native callers requiring
them must explicitly select those thresholds. The Rust crate additionally
exposes a typed `VerificationOptions` interface alongside the existing
function signatures.
Both backend paths must agree on selected settings and outcomes.

The magnitude classifier compares the normalized weighted trace with unit
magnitude; the phase tolerance distinguishes equality from equality
**up to global phase** once the magnitude condition passes. These are not
independent theorems about exact equivalence. Smaller thresholds can
increase false negatives when weighted counts are imprecise. Larger ones
can increase false positives.

## Reference cases and competing tools

For identity vs RZ(0.001),

~~~text
|Tr(RZ(0.001))|/2 = cos(0.0005)
                       ≈ 0.9999998750000026
1 - |Tr|/2              ≈ 1.249999974e-7
~~~

Consequently a magnitude threshold of 1e-6 considers this close enough
in the historical heuristic, whereas 1e-8 distinguishes it. This is
*not* proof that 1e-8 is sound for all circuits or solver output modes.

MQT QCEC reports separate numerical DD tolerance (2e-13 in its
configuration reference), approximate process distance threshold
(default 1e-8), and trace thresholds. Their meanings are different.
Quokka-Sharp documents an FPE: 1e-12 tool configuration field plus an
equivalence API epsilon=0 setting. None of these values should be
copied to QuPRS without comparing the normalized trace metric, backend
arithmetic and actual solver precision.

References:
- https://mqt.readthedocs.io/projects/qcec/en/v3.4.0/api/mqt/qcec/pyqcec/index.html
- https://mqt.readthedocs.io/projects/qcec/en/latest/approximate_equivalence_checking.html
- https://github.com/System-Verification-Lab/Quokka-Sharp

## Numerical status versus proof provenance

~~~python
result = check_equivalence(
    original, optimized, method="wmc_only",
    wmc_magnitude_tolerance=1e-8,
)
# result.equivalent is the current numerical classification;
# result.wmc_numerical_verdict explicitly records the solver observation.
~~~

There is no public `wmc_policy` switch. A floating WMC positive or
negative is not automatically a source-exact proof. The optional
`approximate_distance_tolerance=epsilon` selects the projective
Hilbert--Schmidt distance, with stable magnitude-defect boundary
`epsilon**2 / (1 + sqrt(1 - epsilon**2))`. A fixed 3e-9 empirical
magnitude-defect guard returns `unknown` for uncertain boundary results;
it is **not a certified solver error enclosure**. A projective `1e-8`
distance is below ordinary float64 normalized-magnitude resolution.
The `decision_basis` field marks numerical versus symbolic evidence.
In distance mode, the separately configurable legacy
`config.WMC_MAGNITUDE_TOLERANCE` is ignored; both backends use the
same projective epsilon. The canonical `wmc_magnitude_tolerance=1e-8`
may be explicitly supplied, but a different magnitude threshold is
incompatible with a projective distance request. WMC-only and Hybrid
numerical outcomes are still heuristic, not source-exact proofs.
For controlled comparisons record the tolerance, solver, backend,
raw count and source commit. Verified interval certificates remain
separate research artifacts.

Acceptance requires:
1. Same result across Python/Rust and GPMC/Ganak for true identity and
   I vs RZ(0.001) at both legacy and candidate thresholds.
2. The source-scope regression suite and cross-platform native gates pass.
3. The candidate 1e-8 does not convert bona fide equivalent benchmark
   instances to spurious negative verdicts; otherwise retain 1e-6 by
   default and permit explicit per-call strict policy.
4. No change to the TACAS Reduction-first Hybrid or solver selection.

## v0.14.0 development: precision-aware WMC transport

This section describes the **experimental source implementation** on the
numerical-tolerance development branch. It does not announce a released API,
and it does not change the current public distance-classification semantics.

### Current public verification contract

~~~python
from QuPRS import check_equivalence

result = check_equivalence(
    original, optimized,
    backend="rust",                # or "python"
    method="wmc_only",             # or "hybrid"
    tool_name="ganak",             # or "gpmc"
    approximate_distance_tolerance=2e-4,
    wmc_phase_tolerance=1e-8,
)
print(result.equivalent, result.decision_basis, result.wmc_numerical_verdict)
~~~

**approximate_distance_tolerance** is an optional, finite projective
Hilbert--Schmidt distance threshold strictly in (0, 1). It is **not** the
same quantity as **wmc_magnitude_tolerance**: the latter is the legacy
normalized magnitude-defect budget and must be left at its canonical 1e-8
value if explicitly supplied alongside the projective threshold.
The symbolic reduction tolerance is independently managed by
**config.set_tolerance()**. No **wmc_policy** argument exists.

The possible overall labels remain **equivalent**, **equivalent***,
**not_equivalent**, **unknown**, plus separate timeout/resource outcomes.
**wmc_numerical_verdict** records an external-counter observation, not an
exact proof. Inconclusive numerical evidence stays **unknown**; a Solver
crash, malformed output or timeout is never rebranded as inequivalence.

### Internal precision-aware transport under integration

Python's **QuPRS.utils.precision_count.PrintedCount** stores the real and
imaginary solver count as exact rational conversions of the decimal text,
with separate **printed-format half-last-unit** values. The opt-in internal
**run_wmc(..., preserve_count=True)** returns that record; ordinary
**run_wmc()** retains its existing two-float return shape. Rust's
**pathsum::precision_count::PrintedCount** uses **BigRational**;
**WmcManager::solve_with_deadline_printed** reuses the same Solver subprocess
supervisor and preserves the text before **Complex<f64>** conversion. Legacy
Rust **solve_with_deadline** remains unchanged.

Given the integer normalization exponent k = 2n + number of additional
path variables, both precision-aware implementations compare

\[
  |\operatorname{Count}|^2
  \quad\text{to}\quad
  2^k(1-\varepsilon^2)
\]

with exact rational arithmetic, widening real and imaginary printed
values separately by their formatting half-units. This avoids *additional*
binary64 cancellation in the final normalized magnitude comparison.
An output such as **1.00000000e+00** with insufficient printed precision is
**unknown** at a sufficiently narrow distance threshold, while an output
whose **entire** printed interval lies above the physically normalized
unit magnitude is also **unknown**.

### What the existing empirical guard cannot resolve

The current approximate classifier retains an empirical normalized-magnitude
guard of 3e-9. It is **not** an internal Solver arithmetic bound. Near exact
equivalence the projective-distance threshold has magnitude deficit

\[
\delta_{\mathrm{threshold}} =
\frac{\varepsilon^2}{1+\sqrt{1-\varepsilon^2}}.
\]

At epsilon = 1e-8, this is about 5e-17, so the fixed guard is about
**60 million times larger** than the threshold; at epsilon = 2e-8
it is about **15 million times larger**. A normalized exact-identity
WMC result in this mode can consequently remain **unknown**, even
though the circuits are equal. The guard is comparable to the distance
criterion only around epsilon ~= 7.75e-5. This is a *numerical resolution
floor of the current heuristic*, not a lower bound on the actual circuit
distance or an estimate of all Solver error.

This result motivates separate high-precision weight and Solver-arithmetic
evidence instead of reducing the empirical guard without justification.

**Critical limitation:** these intervals cover only rounding of the
solver's *printed* count, not error in the solver's internal arithmetic,
input weight creation, phase reductions or QASM conversion. They cannot
certify that a solver computed the correct mathematical trace. No native
Ganak distribution has yet been replaced by the research printer variant;
its v2.8.0 mode-6 output remains limited to nine significant digits.
Do not treat an internal printed-only numerical verdict as a new
source-exact equivalence proof.

### Remaining error sources and release documentation gate

| Stage | Current implementation | Required release evidence |
| --- | --- | --- |
| QASM/source angle | Rust QASM2 retains supported pi/decimal-radian literals; Qiskit numeric circuit objects may already be binary64 | Separate input provenance, literal-vs-object tests |
| Python phase to weight | SymEngine evalf(113) emits phase weights | Precision sweep, comparison to independent high-precision oracle |
| Rust phase to weight | Exact PhaseCoeff is converted to binary64 before sin/cos | High-precision conversion and native near-threshold regression |
| Python reduction | Elim, HH, omega may use local tolerance to match/drop terms | Bound or track approximate reductions and their accumulated effect |
| Rust reduction | Exact rational special-coefficient matching | Confirm no hidden lossy branch or untracked approximation |
| GPMC/Ganak computation | Floating/MPFR arithmetic, no global count error certificate | Identify actual arithmetic precision and defensible limits for each Solver |
| Solver output | Precision-aware text parser; Ganak native printer still fixed to %.8Re | Reproducible source-pinned binary build, full output precision, hashes |
| Normalization and distance | Rational printed-count path, not yet connected to public distance verdict | Python/Rust public API parity, boundary and unknown regression |
| End-to-end decision | Existing numerical heuristic and 3e-9 empirical guard | Provenance, conservative unknown, original-paper representative cases |

Before shipping v0.14.0, update **the README, Python public API
docstrings, Rust crate/PyO3 API documentation, and this policy page**
together with one complete example per backend. Document parameter
defaults, allowed range, return statuses, numerical/proof provenance,
legacy-call compatibility, known Solver limitations, and how timeout,
**unknown**, and Solver exceptions differ. The release gate must verify
these docs against the tested implementation, not just a proposed API.

## Candidate-selection evidence

The initial 1e-10 public default candidate failed the native historical
policy gate: explicitly historical RZ(0.0026) controls naturally changed
classification, and a genuine identity versus 60 H gates was falsely
reported as inequivalent by a finite-precision Ganak 2.8.0 mode-6 count.
That proves 1e-10 was too strict for the supported default environment.
The currently integrated public default is 1e-8, while historical boundary
fixtures now explicitly request 1e-6 to continue testing the historical
policy. The large-normalization identity control still uses the new default
and must remain correct; do not adjust that oracle or silently skip the case.

Source: https://github.com/PhysicsQoo/QuPRS/actions/runs/40149062476

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
The per-call `rr_tolerance` governs Python symbolic reduction only;
it is **not** a WMC numerical classifier threshold. Changing the
per-call RR coefficient tolerance participates in symbolic cache keys; it must be a finite positive number (not a bool).
It is not a per-call or thread-local setting.

## Source-phase preservation versus RR matching

For the Python backend, gate construction preserves nonzero input phase
coefficients even when individual coefficients are smaller than
`rr_tolerance`. The Elim/HH/omega matching rules retain their
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
`approximate_distance_tolerance=epsilon` selects projective
Hilbert--Schmidt distance. Python and native Rust (also reached via PyO3)
compare the exact-rational squared-magnitude interval of the printed
complex solver count to `2**k * (1 - epsilon**2)`. Printing resolution
and separately declared count-component uncertainty are included; the
fixed historical `3e-9` heuristic is not used in this public distance
path. A projective `1e-8` distance is below ordinary float64
normalized-magnitude resolution.

GPMC distance mode requests 90 *decimal* precision digits in one solver
invocation. Python applies a conditional source-weight and MPFR operation
allowance; native Rust conservatively accounts for its currently binary64
weight creation. Ganak retains its native mode-6 printer precision and
returns `unknown` when that output cannot distinguish the threshold.
None of these numerical allowances certifies the full source-angle,
reduction-rule, or solver arithmetic error. Solver selection never changes.
No automatic 60/90 replay is performed on the release-facing path;
replays remain restricted to separately scoped research workflows.
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

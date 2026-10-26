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
it is **not** a way to tune the WMC numeric classifier.

The current **public Python API** defaults are magnitude 1e-8 and
phase 1e-8. These are numerical heuristics, not exact certificates. The historical values were 1e-6 each. Direct callers of the
legacy Rust-core function retain its historical defaults; the Python API
passes its validated current per-call settings to the Rust FFI explicitly.
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
    wmc_policy="conservative",
    wmc_magnitude_tolerance=1e-8,
)
# Uncertified solver floating-point observations remain "unknown";
# result.wmc_numerical_verdict retains the threshold-based diagnostic.
~~~

Use wmc_policy="conservative" when an uncertified numeric WMC result
must not be exposed as a strict mathematical verdict. For controlled
legacy comparisons, specify the tolerance and record it with the solver,
backend, raw count, and source commit. Strict interval bounds from the
bounded diagonal-family reference are a separate research artifact.

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

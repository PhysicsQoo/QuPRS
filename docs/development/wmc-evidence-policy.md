# Weighted model counting: numerical evidence versus proof

QuPRS supports the `reduction_rules`, `hybrid`, and `wmc_only`
verification methods. When a run invokes Ganak or GPMC, the solver returns
a finite-precision weighted count rather than a universal exact-equivalence
certificate. The API does **not** expose a `wmc_policy` selector.

## What the current classifier means

The normalized trace magnitude is

\[
m=\frac{|\mathrm{Tr}(U^\dagger V)|}{2^n}.
\]

The current WMC decision threshold is based on `|m - 1|` with a
default `wmc_magnitude_tolerance=1e-8`, not a distance certificate.
The independent phase threshold `wmc_phase_tolerance=1e-8`
separates `equivalent` from `equivalent*` once the magnitude gate passes.
These thresholds have the same defaults in the Python public API,
PyO3/Rust FFI, and direct Rust crate entry points.

For instance, identity versus `Rz(0.0002)` is not strictly equivalent
even up to global phase, but its *ideal* trace-magnitude defect is
about `5e-9`, within the current numerical acceptance band. The
historical `1e-6` threshold would additionally include
`Rz(0.001)` (ideal defect about `1.25e-7`).
These facts describe numeric thresholds, **not** mathematical equality.

## Public Python API

```python
from QuPRS import check_equivalence

result = check_equivalence(
    original, optimized,
    backend="rust", method="wmc_only", tool_name="ganak",
    wmc_magnitude_tolerance=1e-8,
    wmc_phase_tolerance=1e-8,
)

print(result.equivalent)             # Numerical classification
print(result.wmc_numerical_verdict)  # Original solver-derived observation
```

`wmc_numerical_verdict` is populated when WMC supplies a definite numeric
classification, including the Hybrid fallback path; it is `None` when
reduction alone settles the comparison or no solver observation exists.

There is no `wmc_policy="conservative"` option in the updated API.
Previous callers explicitly setting `wmc_policy` must remove that
argument; it raises `TypeError` instead of being ignored. Historical
v0.13.4 behavior remains documented in the changelog.

## Current scope and limitations

In this initial API integration, WMC output remains a numerical
classification. No general solver rounding-error enclosure is claimed.
The projective Hilbert--Schmidt metric,

\[
D(U,V)=\sqrt{1-|\mathrm{Tr}(U^\dagger V)|^2/4^n},
\]

and its explicit user-defined distance boundary will be integrated
alongside automatic near-boundary `unknown` handling in a subsequent
verified implementation stage before the v0.14.0 release.

Python local RR coefficient tolerance is configured using process-global
`config.set_tolerance()`; the Rust native symbolic reduction engine has
different exact-angle semantics and does not silently emulate that knob.
An RR fast-path which proves exact equivalence or equality up to global
phase does not need WMC. A nonzero source-exact residual, however, cannot
alone establish that an operator lies *outside* an explicitly requested
approximate-distance boundary.

Solver parse failures, timeouts, memory exhaustion, and missing binaries
must be reported separately from physical non-equivalence; neither solver
may silently fall back to the other. QASM source literals and already
floating-quantized Qiskit inputs must remain distinguishable when
interpreting numerical evidence.

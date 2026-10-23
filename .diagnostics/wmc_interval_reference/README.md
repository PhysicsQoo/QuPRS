# Small Weighted-CNF Interval Reference

This is an **independent, deliberately bounded research reference**, not a
replacement WMC solver, production verifier, or automatic certificate for
QuPRS's Path-sum-to-CNF encoder.

## What it proves

For at most 12 Boolean variables, it enumerates every assignment satisfying
an explicit CNF and encloses each signed complex literal weight using exact
rational endpoint arithmetic. Addition, subtraction, multiplication and
absolute-value-squared are implemented as outward rational intervals, avoiding
floating-point narrowing. A normalized complex magnitude is enclosed using
integer square roots with outward decimal-rational bounds.

For an **exact rational radian** angle θ in [-1,1], the weights
`exp(+iθ)` and `exp(-iθ)` use consecutive alternating Taylor partial
sums for sine and cosine. Decreasing term magnitudes and the alternating-series
remainder theorem prove that the exact values lie within those intervals.
The input is `Fraction`, **not** a Python float. Unsupported angles or floats
are rejected instead of silently approximated.

The one-variable, no-clause trace reference assigns
`w(+)=exp(+iδ/2)`, `w(-)=exp(-iδ/2)`. Its count is
`2 cos(δ/2)`, so its normalized magnitude matches the analytic
`I` versus `RZ(δ)` trace. In particular `δ=1/1000` radians yields a
rigorously bounded magnitude **strictly less than 1**. Exact identity, pure
phase, zero, signed/complex cancellation and a two-variable XOR CNF provide
independent controls.

## What it does not prove

A manually constructed CNF is **not** the same as the CNF emitted by the QuPRS
encoder. This implementation does **not** read a QuPRS-generated DIMACS file,
parse its full complex-weight dialect, or establish its encoding equivalence to
an input QASM. It does **not** bound actual GPMC/Ganak internal arithmetic,
solver output formatting or numeric normalization. The angle in an ordinary
binary floating-point QASM pipeline is not automatically an exact rational
radian. Thus a reference bound **must not** be retroactively attached to a
native Solver result as a certificate. It also does not solve near-one
certification for general circuits.

No QuPRS source, acceptance thresholds, reducer, solver selection or default
CI testing is changed. The existing near-identity scientific RED remains a
separate unresolved observation.

## Reproduce

With Python 3.11+ and no external dependencies:

```sh
python -m unittest discover -s .diagnostics/wmc_interval_reference -p 'test_*.py' -v
python .diagnostics/wmc_interval_reference/run_reference.py \
  --output interval-wmc-reference-results
(cd interval-wmc-reference-results && sha256sum -c reference-results.sha256)
```

The standalone opt-in workflow saves source provenance, test output, JSON,
SHA256 checksums and JUnit. The entire reference test should be **GREEN**;
it must never turn the separate actual native WMC strict-equivalence RED green
by `xfail`/`skip`, reducing the tolerance or relabeling a false positive.

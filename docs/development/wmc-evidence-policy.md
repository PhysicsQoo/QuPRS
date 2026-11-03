# Weighted model counting: numerical evidence versus proof

QuPRS implements `reduction_rules`, `hybrid` and `wmc_only`.
The default WMC numerical metric for all public Python/PyO3/Rust
entry points in v0.14.0 is **projective Hilbert-Schmidt distance**

\[
D(U,V)=\sqrt{1-|\operatorname{Tr}(U^\dagger V)|^2/4^n}
\]

with `approximate_distance_tolerance=1e-8`. Users may select
a different finite distance tolerance in (0, 1) on each verification.
`None` means the documented default, not legacy magnitude mode.

The historical `wmc_magnitude_tolerance` and `wmc_policy`
public parameters are **removed**: callers supplying them receive
`TypeError`. The global-phase label tolerance
`phase_tolerance` / `wmc_phase_tolerance` is independent;
`rr_tolerance` governs per-call Python reduction and native Rust's
conservative aggregate diagonal-residual RR acceptance.

## Python and Rust example

```python
from QuPRS import check_equivalence

result = check_equivalence(
    original, optimized,
    backend="rust", method="hybrid", tool_name="gpmc",
    approximate_distance_tolerance=1e-8,
)
print(result.equivalent)
print(result.wmc_numerical_verdict)
print(result.wmc_solver_invoked)
```

`equivalent` and `equivalent*` are numerical WMC classifications
when an external solver ran. `wmc_numerical_verdict=None`
indicates no external WMC observation. A reduced or analytic
empty-CNF result can be obtained without invoking the solver; use
`wmc_solver_invoked`, not walltime, to distinguish that case.

## What printed-count precision establishes

Both solvers return numerical weighted complex counts, not universal
certificates of the actual trace. The numerical classifier compares
the central printed complex count's squared magnitude with the
projective threshold. Printed rounding intervals are retained as
separate, uncertified precision diagnostics, not a second acceptance
criterion.
For an observed magnitude deficit `t`,

\[
t(\epsilon)=\frac{\epsilon^2}{1+\sqrt{1-\epsilon^2}}.
\]

At `epsilon=1e-8`, `t\approx5e-17`.
GPMC may be run with 90 decimal output digits; Ganak mode 6 has its
own precision. The GPMC source-phase weights use MPFR input precision
on the supported native path, but **neither** the solver output nor
MPFR input precision proves an upper bound for all internal solver
steps. For this reason, a finite-count WMC verdict is a **numerical
observation**, not a source-exact certificate. The printed interval
can be `unknown` independently of a determinate operational result.

`unknown` remains appropriate when reduction is inconclusive or the
verification stage genuinely cannot classify; printed resolution
alone does not veto the central-count distance classifier. QuPRS
does not retry GPMC at another precision or silently switch Solvers. The default has no process-global mutable
WMC policy; reduction always occurs before WMC in Hybrid mode.

## Scientific acceptance and limits

A source-angle exact identity, a numerical projective-distance
threshold and an external Solver observation are three distinct
claims. QuPRS retains gate-source semantics and explicitly reports
numerical uncertainty rather than asserting that floating WMC
arithmetic is a source-exact proof.

For physics-oriented regression tests, retain Qiskit full-unitary
oracles where tractable and analytical one-qubit controls such as

\[
D(I,R_z(\theta))=|\sin(\theta/2)|.
\]

A reported result inconsistent with such an oracle is a **scientific
failure** and must not be treated as harmless because a broader
regression suite passed. CodSpeed Simulation detects in-process CPU
regressions, whereas real external Solver latency needs WallTime.

See [WMC numerical tolerance](wmc-numerical-tolerance.md) and
[Equivalence semantics](equivalence-semantics.md).

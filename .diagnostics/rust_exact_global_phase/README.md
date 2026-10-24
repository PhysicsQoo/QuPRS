# Exact Rust Reduction global-phase verdict — RED→GREEN contract

This source-pinned research work isolates a **Reduction-only** status
classification problem in the post-paper Rust implementation. It is
distinct from the Python-only TACAS Artifact, WMC solver numeric acceptance
bands, Qiskit transpiler approximation, and explicit
QuantumCircuit.global_phase transport (the latter has an independent
fail-closed guard).

## Independent mathematical oracle

For exact `theta = pi / d` with integer `d > 0`,

```
RZ(theta) = exp(-i theta/2) P(theta)
```

as complete 2×2 unitaries. For `d=1000` and `d=10_000_000`,
`exp(-i pi/(2d))` is **not** one. Consequently the two circuits are
equivalent up to global phase, **not exactly equivalent**. A source
`Angle` holding the exact rational `1/d` multiple of π must not be
declared zero because `sin(theta)` is below a floating tolerance.

The original Rust Reduction status code uses `cos/sin` and
`1e-6` to distinguish exact `equivalent` from `equivalent*`
even after the PathSum is reduced to a pure scalar. This can erase a
genuine scalar at denominators above approximately one million.
Additionally, PathSum `PhaseCoeff` represents cycles of `2*pi`,
not cycles of `pi`, so the old diagnostic
`phase_val * pi` is dimensionally incorrect.

## Acceptance

1. Preserve an independently failing **RED** test on the unchanged
   code using the real Rust verifier with exactly rational
   `Angle(1/10_000_000)` input, plus compiled public
   `QASM2 -> Rust` tests using `rz(pi/d)` vs `p(pi/d)`.
2. Change only the final **pure Reduction phase verdict**: when
   PathSum proves identity up to a scalar phase, report exact equality
   only if `PhaseCoeff::is_zero()` modulo a full `2*pi` cycle;
   any nonzero rational/symbolic scalar must be reported as
   global-phase-only equivalence. Do not alter PhasePolynomial,
   Reduction scheduling, WMC fallback, angle parser, Solver or
   numerical tolerances.
3. Verify the exact identity controls, native Python FFI semantics,
   no WMC call on resolved examples, and cross-version Qiskit 1.4.6
   and 2.6.1 runs.
4. The result remains limited by parser-to-Angle fidelity and
   PathSum mathematical soundness; this correct classification
   **relative to exact represented PhaseCoeff** is not a blanket
   theorem about arbitrary decimal source angles.

The branch is a **stacked Draft** on the validated source parser and
P/U1 normalization work. It is not ready for merging until native and
existing platform/benchmark CI are accepted. Public GitHub only carries
technical reproduction and mathematics; no internal planning metadata.

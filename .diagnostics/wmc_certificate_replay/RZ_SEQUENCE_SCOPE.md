# Exact rational one-qubit RZ sequence source theorem

Research-only stage 1: a standalone Python-stdlib source semantic checker
without Qiskit, QuPRS, GPMC, Ganak or previous interval libraries.

Accepted grammar: canonical 1-qubit OpenQASM 2.0 fixed header and 0–4
literal signed-decimal RZ gates, each |angle| <= 1/2 radian, bounded
cumulative angles; no expressions, comments, other gates or noncanonical
input. Decimal strings are exact rationals by design.

For two accepted source programs U and V let Delta be the rational
difference between their summed angles. Their ideal source relative
unitary is RZ(Delta); up-to-global-phase equivalence is true exactly when
Delta=2*pi*k for an integer k. Since Delta is rational and pi is
irrational, that is possible only for k=0 and Delta=0. This uses the
known mathematical irrationality of pi (not reproved in software).

For nonzero |Delta| <= 1, x=|Delta|/2 in (0,1/2],
the alternating Taylor inequalities give:

    0 < 1 - x^2/2 <= cos(x) <= 1 - x^2/2 + x^4/24 < 1.

All endpoints use exact Fraction values; no floating tolerance or pi
approximation. For Delta=0, multiplying the ideal RZ source matrices
cancels exactly. This proof is solely about the explicitly stipulated
source semantics, not equivalence of compiled circuits.

Fixed six-case matrix:
- identity vs RZ(+0.0002): NON_EQUIVALENT
- identity vs RZ(-0.0002): NON_EQUIVALENT
- identity vs RZ(+0.0002)^2: NON_EQUIVALENT
- identity vs RZ(+0.0002)RZ(-0.0002): EQUIVALENT (source only)
- RZ(+0.0002) vs itself: EQUIVALENT (source only)
- identity vs RZ(+0.0002)RZ(-0.000199999): NON_EQUIVALENT
  (residual = 1/1000000000 radians).

The emitted JSON explicitly sets emitted_cnf_semantics_verified=false
and strict_equivalence_of_compiled_circuits_certified=false for every
case. Source equality or non-equality MUST NOT be promoted to a native
solver or compiler certificate without real CNF/phase mapping evidence.

The already-validated #113 Python diagonal-family source auditor accepts
1-4 RZ/U1/diagonal gates and includes cancellation controls, whereas
the independent #114 Rust source auditor only supports one positive RZ.
Do not simply apply its single-gate positive-angle proof to negatives,
multiple gates or cancellation cases. Extend each real encoder separately
with source-pinned evidence and fail-closed unsupported outcomes.

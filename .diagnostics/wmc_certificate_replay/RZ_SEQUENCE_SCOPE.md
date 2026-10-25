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

## Archived Rust source-angle representation drift (2026-10-25)

This is distinct from floating-point GPMC/Ganak arithmetic. In actual Rust
near-cancellation CNFs, the original source contains RZ(0.0002) followed
by RZ(-0.000199999), giving an **exact source residual of 1e-9 radians**.
Both original solver artifacts preserve Rust PhasePolynomial coefficients
1/12258111022 (constant) and 6129055510/6129055511 (input bit), in pi-units.

Rust rational.rs currently parses decimal source values with f64, divides
by f64 pi, then uses continued fractions with epsilon 1e-10 and a max
denominator of 1e9. Reproducing the conversion on the two distinct gates
yields 27/424115 and -23/361285 pi-units. Their sum is precisely
2/6129055511 pi-units; applying the existing RZ miter factor and sign
gives exactly the constant/bit phase fractions archived in the emitted CNF.

Thus the represented relative-angle is **2*pi/6129055511 radians**, not
the exact source residual 1/1e9 radians. An independent rigorous Fraction
Machin/pi bracketing computation proves the represented angle is strictly
2%-3% larger; its numerical relative error is about **2.5147397654%**.
This percentage is ONLY relative to this cancellation residual and must
not be generalized to individual Rust gate accuracy.

This is a **source->represented-angle discrepancy**. It neither shows
incorrect native solver arithmetic nor invalidates the conditional
enclosure of the **already represented** rational Rust phase weights.
The analytic exact source inequivalence and compiled-source conformance
remain different propositions. A source-semantic correction should be
considered as a separate RED->GREEN change using exact decimal ingress
or an explicitly specified representation-error contract, without
changing reduction-first Hybrid or weakening WMC tolerance.

Provenance: Rust native Actions run 40176131364, artifact 12592955204,
ZIP digest SHA256 27cae4f9e7ef2f74019fd244e1804909a0d0c3917e2602bef45c929ae2e74c23.
See test_rust_decimal_cancellation_drift.py for four independently
checked targeted controls. The observational f64 parser mirror is
separate from the exact rational angle/relative-drift inequality.

# Quantum-circuit equivalence: mathematical contract and implementation status

This document distinguishes the **intended mathematical specification** from the
**observed behavior of the current implementation**. It is not a claim that all
current QuPRS verdicts are sound. In particular, see the reproductions linked
below before relying on a positive WMC verdict or a negative Rust reduction
verdict involving decimal-radian angles.

## Domain and comparison boundary

A supported `n`-qubit circuit denotes a unitary
`U_C: (C^2)^{⊗n} → (C^2)^{⊗n}` under a fixed qubit/register ordering.
The circuits must have the same dimension and compatible mappings of logical
qubits to matrix axes. A register rename is not an implicit permutation.
A different ancilla, garbage, measurement or open-system semantics requires an
**explicit separate contract**; no implicit partial-trace equivalence is implied.

For fixed unitary matrices `U,V ∈ U(d)`, `d=2^n`:

* **Exact equality:** `U = V`.
* **Global-phase equality:** `∃φ∈R: U=e^{iφ}V`. A phase may be nonzero.
* **Exact-versus-global-phase result:** `equivalent` denotes the first,
  `equivalent*` (displayed by the Rust FFI as
  `Equivalent (Up to Global Phase)`) denotes global-phase equivalence.
  The latter is **not** a claim of exact equality.
* **Inequality:** `∀φ∈R: U ≠ e^{iφ}V` (when global phase is permitted).

Global phase is the verification target; two distinct relative phases or
a nontrivial action on a basis state are **not** global phase.

### Matrix-oracle identities

Write `M=U†V` and `t=Tr(M)`. For unitary `M`, exact global-phase
equivalence is characterized by `|t|=d`. This follows by equality in the
triangle inequality for the `d` unit-modulus eigenvalues of `M`.
Exact equality is characterized by `t=d` (not just `|t|=d`).

The optimal global-phase adjusted, dimension-normalized Frobenius distance is

`D_gp(U,V) = min_φ ||U-e^{iφ}V||_F / √d
            = √(2-2|Tr(U†V)|/d).`

These are **mathematical identities**, not permission to test an approximate
floating value for equality. A dense numerical oracle with finite tolerance
is a *diagnostic reference*, not by itself an exact certificate.

For `I` versus `RZ(δ)` on one qubit:
`|Tr(RZ(δ))|/2=|cos(δ/2)|`. For `δ=0.001` radians,
the defect `1-|cos(δ/2)|≈1.249999974×10⁻⁷` is nonzero.
Thus `I` and `RZ(0.001)` are **not** globally-phase equivalent,
even though the magnitude is inside the current `10⁻⁶` WMC band.
In contrast, `RZ(2π)=-I` is globally-phase equivalent to `I`
but not exactly equal.

## Parameterized circuits

For a specified parameter domain `D`, pointwise global-phase equivalence is

`∀θ∈D, ∃φ(θ)∈R: U(θ)=e^{iφ(θ)}V(θ).`

The order of quantifiers is material: a different definition requiring one
parameter-independent `φ` must be stated separately. Exact equality uses
`∀θ∈D, U(θ)=V(θ)`. The domain must specify real/complex parameters,
constraints, binding rules, and whether distinct symbols are independent.

Sampling finitely many parameter assignments is **not** proof of a universal
claim. A counterexample at one valid assignment disproves the universal claim.
No automatic inference of this universal contract from ordinary QASM decimal
constants is intended.

## Intended result/status semantics

| Public Python status | Mathematical meaning / required evidence |
| --- | --- |
| `equivalent` | Exact equality established, not merely a near-one floating trace |
| `equivalent*` | Global-phase equality established, with nonzero phase |
| `not_equivalent` | Proven inequivalence within the declared equivalence model |
| `unknown` | Evidence is insufficient; neither equivalence nor inequivalence proved |
| `Timeout` | Request/solver budget exhausted; not a negative mathematical result |
| `MemoryOut` | Memory/resource exhaustion; not a negative mathematical result |
| exception | Unsupported/invalid input, solver failure, malformed output, or internal error; not a negative mathematical result |

The Rust FFI uses display variants such as `Equivalent`, `Not Equivalent`
and `Equivalent (Up to Global Phase)`; the Python facade translates them.
An `Unknown` returned from reduction must not silently become `Equivalent`
on the strength of a rounded WMC result. Solver errors must not switch
between Ganak and GPMC without explicit user selection.

**Implementation status for the v0.13.4 candidate (2026-10-27):**

1. **Historical pre-fix findings (2026-10-22):** the source-angle RED and
   default WMC negative-control results in the archived
   [native tests](https://github.com/PhysicsQoo/QuPRS/pull/74) and
   [solver audit](https://github.com/PhysicsQoo/QuPRS/pull/77) describe
   earlier commits. They must not be presented as a fresh native RED result
   from current `dev`.
2. **Current Rust source representation:** supported QASM2 decimal-radian
   literals are retained in an exact rational-radian component, separate from
   symbolic pi coefficients, through the Rust PathSum phase operations.
   Conversion at the external weighted-complex-solver boundary remains finite
   precision; exact source representation is **not** a general WMC certificate.
3. **Remaining known limitation:** floating WMC thresholds can classify
   strictly inequivalent near-identity rotations as numerically equivalent.
   There is no selectable `wmc_policy`; the solver observation remains
   available through `wmc_numerical_verdict`. Distance-aware classification
   and automatic numerical uncertainty handling require further verification.
   Strict and approximate Qiskit-transpilation relations (including
   Graphstate16) remain separate.
4. **Release gate:** source-pinned QPE, Graphstate16, CP/U2/SX and global-phase
   oracle controls, both backends and both independent solvers, must be checked
   again at the actual RC SHA. Those prior-run findings are not substitutes.

## Minimal independent reference checks

`python -m pytest -q test/test_semantics_reference_contract.py`

The small one-qubit reference suite exercises exact identity, global phase,
near-identity inequality, nontrivial inequality, exact decimal-radian
composition, symbolic π provenance and parameter-domain counterexamples.
It is not a substitute for the pinned native RED gate or actual solver
audit. A production claim additionally requires backend- and
method-specific parity on exact source SHAs, including both true-positive
and true-negative controls.

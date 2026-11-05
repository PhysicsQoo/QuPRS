# Quantum-circuit equivalence and numerical semantics

This document defines the supported unitary comparison boundary, result labels,
and numerical limits. A finite-precision WMC classification is not a mathematical
proof of exact equivalence, and unsupported input or solver failure must not be
reported as a definitive equivalence result.

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

The v0.14.0 default `approximate_distance_tolerance=1e-8` uses the
**projective Hilbert--Schmidt distance** rather than the phase-adjusted
normalized Frobenius distance above. Writing `m=|Tr(U†V)|/d`:

`D_proj(U,V)=√(1-m²)`, whereas `D_gp(U,V)=√(2-2m)`.

In particular `D_proj²=D_gp²-D_gp⁴/4`; at `m=√3/2`,
`D_proj=0.5` but `D_gp≈0.517638`. The stable projective
threshold uses `1-m ≤ epsilon²/(1+√(1-epsilon²))`, with a
printed-count output precision interval, not a fixed numerical guard. These metric tolerances
must not be conflated with one another or with other tools' settings.

These are **mathematical identities**, not permission to test an approximate
floating value for equality. A dense numerical oracle with finite tolerance
is a *diagnostic reference*, not by itself an exact certificate.

For `I` versus `RZ(δ)` on one qubit:
`|Tr(RZ(δ))|/2=|cos(δ/2)|`. For `δ=0.001` radians,
the defect `1-|cos(δ/2)|≈1.249999974×10⁻⁷` is nonzero.
Thus `I` and `RZ(0.001)` are **not** globally-phase equivalent,
even though a retired magnitude-based heuristic with a `10⁻⁶` band would have accepted it. The v0.14.0 default distance criterion does not.
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

## Result/status semantics and evidence provenance

A result string is a **classification**, not by itself a formal proof.
The same string can arise from exact symbolic reasoning, tolerance-dependent
Python reductions, or finite-precision WMC.

| Status | Current interpretation |
| --- | --- |
| `equivalent` | Symbolic identity or numerical near-identity under the selected thresholds; WMC acceptance is not proof of exact equality. |
| `equivalent*` | Symbolic up-to-global-phase result or numerically accepted trace with phase above the phase threshold. |
| `not_equivalent` | Structural mismatch, strict symbolic counterexample, or numerical WMC rejection; numerical negatives are not universal source-exact proofs. |
| `unknown` | Incomplete symbolic reduction or another genuinely inconclusive verification outcome; printed output rounding uncertainty is separately reported. |
| `Timeout`, `MemoryOut` | Resource limit, not physical non-equivalence. |
| exception | Invalid input, missing solver or failed parsing, not non-equivalence. |

A result classified without WMC has `wmc_time=None` and
`tool_time=None`. A populated `wmc_time` indicates that the
WMC stage was reached; use `wmc_solver_invoked` (available for both
backends) to establish whether an external solver actually ran.
This distinction is necessary for Rust's empty-CNF analytic shortcut.
For finite WMC counts, `wmc_printed_verdict` can be `unknown`
while the operational `wmc_numerical_verdict` is determinate.
Timing alone does not provide a mathematical proof, and a reduction
verdict can depend on RR tolerance. Rust FFI display strings are
normalized by the Python facade. Solver failures do not silently
select a different solver.

## Source representation and numerical limitations

Supported native Rust QASM2 decimal-radian literals retain their rational
source representation separately from symbolic multiples of pi through the
PathSum phase operations. Qiskit-object inputs can already contain rounded
floating-point parameters; the native parser cannot reconstruct original
source literals from those values.

External weighted-complex solvers use finite-precision arithmetic and report
numerical counts rather than certified bounds on the exact trace. Near the
selected distance threshold, a numerically accepted result can differ from
strict source-exact equivalence. Use an independent physical or matrix oracle
when the distinction matters. See [WMC evidence policy](wmc-evidence-policy.md).

## Minimal independent reference checks

`python -m pytest -q test/test_semantics_reference_contract.py`

The small one-qubit reference suite exercises exact identity, global phase,
near-identity inequality, nontrivial inequality, exact decimal-radian
composition, symbolic π provenance and parameter-domain counterexamples.
It is not a complete proof for arbitrary circuit families. Backend- and
method-specific checks should include both equivalent and inequivalent
controls under the documented source and numerical semantics.

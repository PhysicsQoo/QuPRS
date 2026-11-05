# Source-angle representation and limitations

**Current representation contract (v0.14.0):** the supported Rust QASM2 angle/phase
representation has been integrated into `rational.rs`, `qasm.rs` and the
PathSum/WMC path. Exact decimal-radian input provenance is preserved through
symbolic phase operations. The solver complex-weight boundary and some
Qiskit-object input paths still use finite precision; this is not a
certificate of arbitrary-circuit strict equivalence.

## Angle representation

For an accepted QASM angle `θ` represent
`θ = aπ + b` radians, where `a,b ∈ Q` are **independent,
arbitrary-precision** rational coefficients. Store symbolic π multiples
as `(a,0)`; store *literal decimal radian constants* as `(0,b)`
using an exact base-10 decimal-to-rational parse. Do not silently treat
`3.141592653589793` as symbolic `π`. Distinguish literal source
semantics from incoming already-rounded binary64 Qiskit parameters;
the latter require an explicit, documented conversion policy.

For expression addition/subtraction, operate componentwise. Scalar
integer/rational multiplication preserves exactness. For cancellation,
`(aπ+b)-(aπ+b)=0` exactly. Because π is transcendental,
`aπ+b=0` iff `a=b=0` over rational `a,b`.
Likewise `aπ+b ≡ 0 (mod 2π)` iff `b=0` and
`a∈2Z`. **Never** independently reduce the decimal-radian
coefficient `b` modulo 2π by floating approximation.

Path-sum phase exponents use factors `exp(2π i P)`; angle and phase
objects require a **typed, proof-preserving conversion**.
A rational multiple of π can become a rational phase coefficient;
a rational decimal-radian constant requires its own exact provenance
or a bounded transcendental evaluator, not a rational substitute for
`b/π`. Global-phase identity detection must distinguish an
input-independent phase from qubit-dependent relative phases.

## Input and conversion limits

The native parser accepts only supported static QASM angle arithmetic;
unsupported expressions and gates fail closed. Literal decimal radians
remain distinct from symbolic pi terms. Inputs already rounded by Qiskit
cannot regain source-literal precision through parsing.

The external WMC complex-weight conversion and solver counting remain
finite-precision operations. This representation improves source-angle
fidelity but does not certify arbitrary weighted-model-counting results.
For verification near a numerical decision boundary, use independent
matrix or physical-reference checks. See the
[WMC evidence policy](wmc-evidence-policy.md).

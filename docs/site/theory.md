# Theory

## Path-sum representation

A Path-sum expresses a quantum circuit using Boolean path variables and phase polynomials. QuPRS applies algebraic reduction rules, including elimination, Hadamard–Hadamard, and omega-style simplifications.

When reductions do not determine the result, the hybrid method can encode the remaining expression as a weighted model counting (WMC) problem.

## Numerical equivalence

For unitary operators (U) and (V) on (n) qubits, a projective distance used by QuPRS is

$$
D_{\mathrm{proj}}(U,V)
= \sqrt{1 - \frac{|\operatorname{Tr}(U^\dagger V)|^2}{4^n}}.
$$

This distance is insensitive to a global phase. Source-exact gate equivalence, numerical acceptance, and solver precision are distinct concepts; results must be interpreted using the requested verification method and its tolerance contract.

See the [public numerical semantics](https://github.com/PhysicsQoo/QuPRS/blob/dev/docs/development/per-call-tolerance.md) for the API's per-verification thresholds.

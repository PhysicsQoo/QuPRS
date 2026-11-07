# Theory

QuPRS verifies supported unitary quantum-circuit comparisons using Boolean Path-sum representations, algebraic reduction rules, and optional complex weighted model counting.

## Mathematical foundations

- [Path-sum and reduction rules](path-sum.md) explains Boolean path variables, phase-polynomial expressions, the roles of Elim/HH/omega, and exact-versus-tolerance-aware reduction.
- [Weighted model counting](weighted-model-counting.md) explains the complex counting formulation, independent solver selection, and limits of numerical evidence.
- [Verification methods and result meanings](verification.md) relates the mathematical stages to the user-facing API.

For two unitary operators `U` and `V` on `n` qubits, the projective metric used by the default WMC classifier is

$$
D_{\mathrm{proj}}(U,V)
=\sqrt{1-\frac{|\operatorname{Tr}(U^\dagger V)|^2}{4^n}}.
$$

An equality claim may be structural or approximate, depending on the selected method and tolerances. This distance is global-phase invariant, but a positive finite-precision solver verdict is not, by itself, a proof of source-exact equivalence.

The complete publicly documented [equivalence semantics](https://github.com/PhysicsQoo/QuPRS/blob/dev/docs/development/equivalence-semantics.md) distinguish exact equality, global-phase equivalence, and finite numerical acceptance. See [executable examples](examples.md) for small controls.

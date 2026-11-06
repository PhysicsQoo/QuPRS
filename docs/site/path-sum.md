# Path-sum representation and reduction

## Representation

A Path-sum represents the action of a quantum circuit on a computational-basis state as a finite sum of amplitudes indexed by Boolean path variables:

$$
U|x\rangle = \alpha\!\!\sum_{y\in\{0,1\}^{m}}
 e^{2\pi i P(x,y)}\,|f(x,y)\rangle.
$$

Here, \(x\) is the input bit string, \(y\) is the path-variable string, \(P\) is a real-valued phase polynomial measured in **cycles** (one cycle is \(2\pi\) radians), \(f\) gives the output bit string, and \(\alpha\) accounts for normalization. The exact representation and allowed coefficient domains depend on the constructed PathSum; not every circuit is a sum with unit coefficients.

For a comparison, QuPRS builds an expression reflecting the input and output circuit composition. The reduction engine rewrites the Path-sum while attempting to preserve the represented operation.

## Reduction rules

QuPRS implements the **Elim**, **HH**, and **omega** families of simplifications:

| Rule family | Purpose | Essential applicability condition |
| --- | --- | --- |
| Elim | Remove a redundant path variable | Its phase/output dependence must meet the rule's cancellation conditions |
| HH | Eliminate or constrain variables through Hadamard-related phase structure | The required phase-polynomial and Boolean dependencies must match |
| Omega | Simplify a constrained root-of-unity phase sum | Coefficients and variable occurrence must match the supported root-of-unity identity |

These descriptions are the rule *roles*, not substitutes for their algebraic side conditions. An arbitrary phase polynomial or path variable cannot be eliminated just because it resembles a pattern. See the public [Rust reduction implementation](https://github.com/PhysicsQoo/QuPRS/tree/dev/rust/pathsum/src) and [Python PathSum implementation](https://github.com/PhysicsQoo/QuPRS/tree/dev/src/QuPRS/pathsum) for the exact supported cases.

## Exact source expressions versus approximate reduction

The per-call `rr_tolerance` controls numerical coefficient matching and approximate reduction in the supported implementations. The default is `1e-10`. Choosing `rr_tolerance=0` is useful when checking whether the reduction relies on numerical acceptance rather than a tolerance-matched coefficient.

The original input angles must not be silently replaced by rounded source literals. Python's Qiskit-object path may already contain binary floating-point angles, while supported native Rust QASM literals can preserve their textual decimal provenance. Therefore equal-looking numerical results do not necessarily certify identical original sources.

## Reduction-only and hybrid

- `method="reduction_rules"` returns a classification when reduction establishes one; otherwise it can report `unknown`.
- `method="hybrid"` passes the **final configured reduction residual** to WMC only when reduction remains inconclusive. It does not revert to the original unreduced circuit behind the user's back.
- `method="wmc_only"` bypasses reduction-rule matching but still performs the representation/normalization required to form the WMC problem.

An accepted reduction can depend on `rr_tolerance`. When a source-exact or independently certified claim matters, compare with an appropriate mathematical oracle or use controlled exact-source checks.

See [worked examples](examples.md), [weighted model counting](weighted-model-counting.md), and [equivalence and numerical semantics](https://github.com/PhysicsQoo/QuPRS/blob/dev/docs/development/equivalence-semantics.md).

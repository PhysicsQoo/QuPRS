# Path-sum representation and reduction

## Representation

A Path-sum represents the action of a quantum circuit on a computational-basis state as a finite sum of amplitudes indexed by Boolean path variables:

$$
U|x\rangle = \alpha\!\!\sum_{y\in\{0,1\}^{m}}
 e^{2\pi i P(x,y)}\,|f(x,y)\rangle.
$$

Here, \(x\) is the input bit string, \(y\) is the path-variable string, \(P\) is a real-valued phase polynomial measured in **cycles** (one cycle is \(2\pi\) radians), \(f\) gives the output bit string, and \(\alpha\) accounts for normalization. The exact representation and allowed coefficient domains depend on the constructed PathSum; not every circuit is a sum with unit coefficients.

For a comparison, QuPRS builds an expression reflecting the input and output circuit composition. The reduction engine rewrites the Path-sum while attempting to preserve the represented operation.

## Exact algebraic identities underlying the rules

These identities hold for **Boolean** variables. They are algebraic checks on the rule families, not a claim that any approximate coefficient match is exact.

**Elim.** If an internal path variable \(y\) occurs in neither the phase \(P\) nor the output \(f\), then the two contributions are identical:

$$
\sum_{y\in\{0,1\}} e^{2\pi iP}\,|f\rangle
=2e^{2\pi iP}\,|f\rangle.
$$

Removing \(y\) must also preserve the total amplitude, including the path-count normalization. QuPRS finds a reducible variable only after checking that it is absent from the output and the phase.

**HH.** Let the complete path-variable tuple be \(y=(y_0,y_1,z)\), with residual tuple \(y'=(y_1,z)\) excluding \(y_0\). The integer-valued polynomial \(Q(x,z)\) is independent of \(y_0,y_1\). The **source phase**, before applying the reduction, is

$$
P(x,y)=\frac12 y_0\bigl(y_1+Q(x,z)\bigr)+R(x,y').
$$

Here the original \(Q\) is **not reduced modulo 2**. The residual phase \(R(x,y')\) and output ket \(|f(x,y')\rangle\) are independent of the eliminated variable \(y_0\).

Summing \(y_0\) enforces the Boolean constraint \(y_1=\overline Q\), where **only at substitution** do we define \(\overline Q=Q(x,z)\bmod 2\). If \(y_0\) and \(y_1\) are both summed variables, HH acts on the complete amplitude and output ket:

$$
\begin{aligned}
&\sum_{y_0,y_1\in\{0,1\}}
 e^{2\pi iP(x,y)}\,|f(x,y')\rangle\\
&\qquad=2\,e^{2\pi iR_{\overline Q}(x,z)}
 |f_{\overline Q}(x,z)\rangle.
\end{aligned}
$$

Here \(R_{\overline Q}(x,z)=R(x,(\overline Q,z))\) and \(f_{\overline Q}(x,z)=f(x,(\overline Q,z))\). Thus the **original phase keeps \(Q\)**, while the replacement \(y_1\leftarrow\overline Q\) is performed in **both the residual phase and the output ket**. The factor \(2\) must be combined with the Path-sum normalization.

When \(y_1\) is not a summed variable, summing over \(y_0\) instead gives \(2\delta_{y_1,\overline Q}\) times the residual amplitude and ket. Implementation matching additionally requires the supported half-cycle coefficient pattern and a target variable absent from its own replacement polynomial.

**Omega.** Let \(y_0\) be a summed Boolean variable, with residual phase \(R\), integer-valued \(Q\), and output ket \(|f\rangle\) all independent of \(y_0\). As in HH, the **source** keeps the unreduced \(Q\), while the reduced phase uses \(\overline Q=Q\bmod 2\). The quarter-cycle identities preserve the output ket:

$$
\begin{aligned}
&\sum_{y_0=0}^{1}
 e^{2\pi i[R+y_0(\frac14+\frac12Q)]}
 |f\rangle\\
&\qquad=\sqrt{2}\,
 e^{2\pi i[R+\frac18-\frac14\overline Q]}
 |f\rangle,
\end{aligned}
$$

$$
\begin{aligned}
&\sum_{y_0=0}^{1}
 e^{2\pi i[R+y_0(\frac34+\frac12Q)]}
 |f\rangle\\
&\qquad=\sqrt{2}\,
 e^{2\pi i[R-\frac18+\frac14\overline Q]}
 |f\rangle.
\end{aligned}
$$

The output ket \(|f\rangle\) is unchanged because it does not depend on \(y_0\). The \(\sqrt{2}\) factor is accounted for by the Path-sum normalization when the path-variable count changes. These identities require the specified quarter-cycle singleton and half-cycle cross terms; they cannot be applied to arbitrary coefficients or a \(y_0\)-dependent output.

For implementation-level applicability, see [Python matching and substitutions](https://github.com/PhysicsQoo/QuPRS/blob/dev/src/QuPRS/pathsum/pattern_match.py) and [native Rust reduction matching](https://github.com/PhysicsQoo/QuPRS/blob/dev/rust/pathsum/src/reduction.rs). The algebraic identities appear in the [TACAS 2026 QuPRS paper](https://link.springer.com/chapter/10.1007/978-3-032-22749-2_21) and earlier [path-sum verification calculus](https://www.mathstat.dal.ca/~mamy/Papers/pathsum.pdf). 

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

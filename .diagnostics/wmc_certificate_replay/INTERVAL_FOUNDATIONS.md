# Rational interval proof foundations — bounded research audit

Scope: the single-qubit source-CNF RZ(0.0002) strict *negative* certificate only. These exact-arithmetic unit tests are necessary regression properties, NOT a second independent formalization of the full proof engine.

1. Pi: Machin formula pi=16 atan(1/5)-4 atan(1/239). From tangent addition, tan(2a)=5/12 and tan(4a)=120/119 for a=atan(1/5); b=atan(1/239) gives tan(4a-b)=1. The analytic range 0<4a-b<pi/2 fixes 4a-b=pi/4. Since arctan(1/n) has decreasing alternating terms, consecutive rational partial sums are outward bounds for n>=2. Interval subtraction preserves containment.

2. Taylor: for |x|<=1, decreasing alternating cosine and sine partial sums enclose the true values. For rational |x|<=7, the general polynomial uses the uniform Lagrange remainder bound |x|^(2*t-1)/(2*t-1)! for cosine and |x|^(2*t)/(2*t)! for sine, since all derivatives have absolute value <=1. For interval angles derived from pi, the midpoint plus/minus its radius is valid by the real sine/cosine derivative <=1.

3. Complex interval: each real and imaginary product is enclosed using all interval endpoint products, subtraction and addition. Dependency can widen the enclosure but cannot soundly narrow it. Weight-count intervals sum ALL satisfying assignments; their phase-literal truth tables and unique Boolean witnesses must separately be checked against actual CNF.

4. sqrt and outward decimals: integer square root of floor(n*10^(2d)) yields the exact lower integer root. Its ceiling is either that integer or the next; therefore an exact value 1 cannot be rounded below 1. A strictly smaller exact bound within the rounding grid remains INCONCLUSIVE if its rounded upper endpoint is 1.

5. Source semantics: the research model defines literal decimal rz(0.0002) as exact 1/5000 radians. The ideal eigenphases are ±1/10000. For 0<x<=1, cos(x)<=1-x^2/2+x^4/24<1, so exact source non-equivalence is analytic. This is a PRECONDITION, not a proof that arbitrary QASM floating parsers preserve exact decimal semantics. Source-to-weighted-CNF phase matching is separately bounded for the pinned research case.

Unverified: general QASM compiler correctness, all Rust/Python phase translations, GPMC/Ganak internal floating-point error, and strict positive equivalence from any finite numerical tolerance. No production policy changes. A fully independent formal proof in Coq/Lean/Isabelle is not supplied by these tests.

"""Reproduce near-cancelled Rust Angle rational approximation.

The exact Rust phase fractions are pinned to source-run 40176131364,
Artifact #12592955204. The float continued-fraction routine is an
observational reproduction of the source parser, while pi enclosures and
relative-error inequalities are rigorous independent Fraction arithmetic.
This is NOT a native-solver-arithmetic or full compiler proof.
"""
from fractions import Fraction as F
from math import floor, pi
import unittest

SOURCE_A = F("0.0002")
SOURCE_B = F("-0.000199999")
SOURCE_DELTA = SOURCE_A + SOURCE_B
# Raw nearly_cancelled PhasePolynomial TSV (both solvers).
RUST_CONST = F(1,12258111022)
RUST_BIT = F(6129055510,6129055511)


def mirror_rust_continued_fraction(value):
    """Mirror rational.rs f64 CF policy; NOT a bit-exact Rust interpreter."""
    epsilon=1e-10
    max_denom=1_000_000_000
    if abs(value)<epsilon:
        return F(0)
    x=value
    n0,n1,d0,d1=0,1,1,0
    for _ in range(100):
        a=floor(x)
        n2,d2=a*n1+n0,a*d1+d0
        if d2>max_denom:
            break
        n0,n1,d0,d1=n1,n2,d1,d2
        if abs(value-n1/d1)<epsilon:
            break
        fractional=x-a
        if fractional<epsilon:
            break
        x=1/fractional
    else:
        raise ValueError("Unbounded continued fraction approximation")
    return F(n1,d1)


def exact_arctangent_interval(denominator,terms=36):
    """Adjacent alternating Taylor sums enclose arctan(1/denominator)."""
    x=F(1,denominator)
    s=sum(((-1)**k*x**(2*k+1)/F(2*k+1))
          for k in range(terms))
    following=s+(-1)**terms*x**(2*terms+1)/F(2*terms+1)
    return min(s,following),max(s,following)


def machins_pi_interval():
    a0,a1=exact_arctangent_interval(5)
    b0,b1=exact_arctangent_interval(239)
    return 16*a0-4*b1,16*a1-4*b0


def represented_vs_source():
    if SOURCE_DELTA!=F(1,10**9):
        raise ValueError("Unexpected exact QASM source delta")
    phase_distance=1-RUST_BIT
    if phase_distance != RUST_CONST*2:
        raise ValueError("Constant/bit phase disagreement")
    low,high=machins_pi_interval()
    # Rz's represented angle = 2*pi*(1-bit-coefficient).
    represent_lo=2*low*phase_distance
    represent_hi=2*high*phase_distance
    return {
        "source_delta":SOURCE_DELTA,
        "represented_pi_units":2*phase_distance,
        "represented_radians_lower":represent_lo,
        "represented_radians_upper":represent_hi,
        "relative_drift_lower":represent_lo/SOURCE_DELTA-1,
        "relative_drift_upper":represent_hi/SOURCE_DELTA-1,
    }


class RustExactSourceDriftControls(unittest.TestCase):
    def test_mirror_each_individual_float_approximation(self):
        a=mirror_rust_continued_fraction(float(SOURCE_A)/pi)
        b=-mirror_rust_continued_fraction(float(-SOURCE_B)/pi)
        self.assertEqual(a,F(27,424115))
        self.assertEqual(b,-F(23,361285))
        self.assertEqual(a+b,F(2,6129055511))
        self.assertEqual(RUST_CONST,(a+b)/4)
        self.assertEqual(RUST_BIT,(-F(1,2)*(a+b))%1)

    def test_pi_interval_is_exact_and_tight(self):
        low,high=machins_pi_interval()
        self.assertLess(F(314159,100000),low)
        self.assertLess(low,high)
        self.assertLess(high,F(314160,100000))
        self.assertLess(high-low,F(1,10**30))

    def test_source_and_represented_angles_provably_differ(self):
        x=represented_vs_source()
        self.assertEqual(x["source_delta"],F(1,10**9))
        self.assertTrue(F(2,100)<x["relative_drift_lower"]
                        <x["relative_drift_upper"]<F(3,100))
        self.assertGreater(x["represented_radians_lower"],SOURCE_DELTA)

    def test_near_identity_result_is_not_positive_proof(self):
        x=represented_vs_source()
        # Source trace gap ≈delta^2/8, so float-based tolerance is
        # insufficient for asserting exact equivalence at 1e-9.
        self.assertEqual(SOURCE_DELTA**2/F(8),F(1,8*10**18))
        self.assertGreater(x["represented_radians_lower"],SOURCE_DELTA)


if __name__=="__main__":
    unittest.main()

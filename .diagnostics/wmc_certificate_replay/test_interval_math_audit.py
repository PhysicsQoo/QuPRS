"""Necessary mathematical invariants; not a second formal proof system."""
from fractions import Fraction as F
from itertools import product
from math import factorial
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"wmc_interval_reference"))
from interval_wmc import (
    Interval, ComplexInterval, WeightedCNF, _sqrt_fraction_bounds,
    _alternating_series_nonnegative, normalized_magnitude,
    unit_phase_rational_radians)
from phase_coeff_reference import (
    arctan_reciprocal_interval, ideal_rational_pi_phase, pi_interval,
    outward_decimal_interval, taylor_trig_at_rational)

def encloses(interval, val):
    return interval.lower <= val <= interval.upper

class IntervalMathFoundations(unittest.TestCase):
    def test_machin_identity_rational_tangent(self):
        # a=atan(1/5), tan(2a)=5/12, tan(4a)=120/119,
        # b=atan(1/239): tan(4a-b)=1, 0<4a-b<pi/2 => pi/4.
        a=F(1,5)
        tan_2a=2*a/(1-a*a)
        tan_4a=2*tan_2a/(1-tan_2a*tan_2a)
        self.assertEqual(tan_2a,F(5,12))
        self.assertEqual(tan_4a,F(120,119))
        self.assertEqual((tan_4a-F(1,239))/(1+tan_4a*F(1,239)),1)
        pi=pi_interval()
        self.assertLess(F(333,106),pi.lower)
        self.assertLess(pi.upper,F(355,113))
        self.assertLess(pi.upper-pi.lower,F(1,10**100))

    def test_arctangent_consecutive_alternating_sums(self):
        for denom,terms in product((2,5,239,1000),(1,2,5,25)):
            with self.subTest(denom=denom,terms=terms):
                interval=arctan_reciprocal_interval(denom,terms=terms)
                next_term=F(1,denom)**(2*terms+1)/(2*terms+1)
                self.assertEqual(interval.upper-interval.lower,next_term)
                self.assertGreaterEqual(interval.lower,0)
                self.assertLessEqual(interval.upper,F(1,denom))

    def test_sine_cosine_alternating_width_and_symmetry(self):
        for x,cosine,terms in product((F(0),F(1,10000),F(1,5),F(1)),
                                     (True,False),(1,2,6,9)):
            with self.subTest(x=x,cosine=cosine,terms=terms):
                val=_alternating_series_nonnegative(x,cosine=cosine,terms=terms)
                k=0 if cosine else 1
                self.assertEqual(val.upper-val.lower,
                                 x**(2*terms+k)/factorial(2*terms+k))
        for x,cosine in product((F(0),F(1,10000),F(5,2),F(7)),
                                (True,False)):
            pos=taylor_trig_at_rational(x,cosine=cosine)
            neg=taylor_trig_at_rational(-x,cosine=cosine)
            self.assertEqual(neg,pos if cosine else -pos)
            if x==0:
                self.assertEqual(pos,Interval.exact(1 if cosine else 0))

    def test_complex_rectangles_enclose_corner_products(self):
        a=ComplexInterval(Interval(F(-3,2),F(2)),
                          Interval(F(-2),F(1,3)))
        b=ComplexInterval(Interval(F(-1,3),F(7,4)),
                          Interval(F(-4,5),F(3)))
        result=a*b
        for x,y,u,v in product((a.real.lower,a.real.upper),
                                (a.imag.lower,a.imag.upper),
                                (b.real.lower,b.real.upper),
                                (b.imag.lower,b.imag.upper)):
            self.assertTrue(encloses(result.real,x*u-y*v))
            self.assertTrue(encloses(result.imag,x*v+y*u))

    def test_outward_negative_decimal_and_rational_sqrt(self):
        for low,high in ((F(-3,7),F(2,11)),(F(-11,3),F(-1,19)),
                         (F(0),F(0)),(F(1,10**60),F(1,3))):
            rounded=outward_decimal_interval(Interval(low,high),digits=20)
            self.assertLessEqual(rounded.lower,low)
            self.assertGreaterEqual(rounded.upper,high)
        for v in (F(0),F(1),F(2),F(4,9),
                  F(1,10**80),F(1)-F(1,10**90),F(1)+F(1,10**90)):
            lo,hi=_sqrt_fraction_bounds(v)
            self.assertLessEqual(lo*lo,v)
            self.assertGreaterEqual(hi*hi,v)
        self.assertEqual(_sqrt_fraction_bounds(F(1)-F(1,10**90))[1],F(1))
        self.assertEqual(normalized_magnitude(ComplexInterval.exact(1),1),
                         Interval.exact(1))

    def test_ideal_pi_phase_quadrants(self):
        expected={(1,4):(F(0),F(1)),(1,2):(F(-1),F(0)),
                  (3,4):(F(0),F(-1))}
        for (numer,denom),(re,im) in expected.items():
            z=ideal_rational_pi_phase(numer,denom)
            self.assertTrue(encloses(z.real,re))
            self.assertTrue(encloses(z.imag,im))

    def test_small_rz_strict_negative_and_precision_fail_closed(self):
        for x in (F(-1),F(-1,10000),F(0),F(1,10000),F(1)):
            self.assertTrue(encloses(unit_phase_rational_radians(x).abs_squared(),1))
        half=F(1,10000)
        trace=unit_phase_rational_radians(half)+unit_phase_rational_radians(-half)
        magnitude=normalized_magnitude(trace,2)
        self.assertLess(magnitude.upper,1)
        self.assertGreater(magnitude.lower,F(99999999,100000000))
        tiny=F(1,10**60)
        tiny_trace=unit_phase_rational_radians(tiny)+unit_phase_rational_radians(-tiny)
        self.assertGreaterEqual(normalized_magnitude(tiny_trace,2).upper,1)

if __name__=="__main__":
    unittest.main()

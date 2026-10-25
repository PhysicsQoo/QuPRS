"""High denominator phases get a narrow research-only rigorous enclosure."""
import math
from fractions import Fraction as F
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from wrapped_rust_phase_reference import local_wrapped_phase
from interval_wmc import Interval, ComplexInterval


class HighDenominatorPhaseBoundary(unittest.TestCase):
    def test_actual_rust_tiny_angle_fractions_bounded(self):
        for numerator,denominator in (
            (1,12258111022),
            (6129055510,6129055511),
        ):
            with self.subTest(denominator=denominator):
                phase=local_wrapped_phase(numerator,denominator)
                self.assertTrue(phase.real.lower <= 1 <= phase.real.upper)
                self.assertTrue(phase.abs_squared().lower <= 1
                                <= phase.abs_squared().upper)
                self.assertLess(phase.imag.upper-phase.imag.lower,F(1,10**20))

    def test_wrap_sign_and_nonzero_coefficient(self):
        x=local_wrapped_phase(1,12258111022)
        y=local_wrapped_phase(12258111021,12258111022)
        self.assertGreater(x.imag.lower,0)
        self.assertLess(y.imag.upper,0)
        self.assertGreater(x.real.lower,0)

    def test_reject_oversized_or_large_unchecked_phases(self):
        for a,b in ((1,10**13+1),(1,10**9),(1,10**12+1),
                    (10**11+1,3*10**11+3),(0,10**11+1)):
            with self.subTest(numerator=a,denominator=b),self.assertRaises(ValueError):
                local_wrapped_phase(a,b)


if __name__=="__main__":
    unittest.main()

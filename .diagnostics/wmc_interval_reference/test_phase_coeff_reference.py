"""Independent rational-pi coefficient-to-complex-weight enclosures."""
from fractions import Fraction as F
import unittest

from interval_wmc import ComplexInterval, Interval, normalized_magnitude
from phase_coeff_reference import (
    arctan_reciprocal_interval, ideal_rational_pi_phase, pi_interval,
    taylor_trig_at_rational, union_printed_and_ideal,
    max_printed_ideal_component_gap, outward_decimal_interval,
)


class PhaseCoefficientReferenceTests(unittest.TestCase):
    def test_machin_pi_interval_contains_strict_rational_bounds(self):
        p = pi_interval()
        self.assertLess(p.lower, F(355, 113))  # 355/113 is above pi.
        self.assertGreater(p.upper, F(333, 106))  # 333/106 is below pi.
        self.assertGreater(p.lower, F(333, 106))
        self.assertLess(p.upper, F(355, 113))
        self.assertLess(p.upper - p.lower, F(1, 10**100))

    def test_outward_rational_decimal_rounding(self):
        rounded = outward_decimal_interval(
            Interval(F(-1, 3), F(1, 3)), digits=20
        )
        self.assertLessEqual(rounded.lower, F(-1, 3))
        self.assertGreaterEqual(rounded.upper, F(1, 3))
        self.assertGreater(rounded.upper - rounded.lower, F(0))
        self.assertEqual(outward_decimal_interval(Interval.exact(1)),
                         Interval.exact(1))

    def test_phase_zero(self):
        z = ideal_rational_pi_phase(0, 1)
        self.assertEqual(z, ComplexInterval.exact(1))
        self.assertEqual(normalized_magnitude(z, 1), Interval.exact(1))

    def test_quadrants_and_negative_cosine(self):
        q = [
            ((1, 4), F(0), F(1)),
            ((1, 2), F(-1), F(0)),
            ((3, 4), F(0), F(-1)),
        ]
        for (numer, denom), re, im in q:
            with self.subTest(phase=(numer, denom)):
                z = ideal_rational_pi_phase(numer, denom)
                self.assertLessEqual(z.real.lower, re)
                self.assertGreaterEqual(z.real.upper, re)
                self.assertLessEqual(z.imag.lower, im)
                self.assertGreaterEqual(z.imag.upper, im)
                self.assertLess(z.real.upper - z.real.lower, F(1, 10**45))
                self.assertLess(z.imag.upper - z.imag.lower, F(1, 10**45))

    def test_representation_enclosure_hulls(self):
        printed = ComplexInterval.exact(F(1001, 1000), F(1, 2))
        ideal = ComplexInterval(Interval(F(999, 1000), 1),
                                Interval(F(499, 1000), F(501, 1000)))
        envelope = union_printed_and_ideal(printed, ideal)
        self.assertEqual(envelope.real.lower, F(999, 1000))
        self.assertEqual(envelope.real.upper, F(1001, 1000))
        self.assertGreaterEqual(max_printed_ideal_component_gap(printed, ideal),
                                F(1, 1000))

    def test_remainder_even_for_angles_greater_than_one(self):
        p = pi_interval()
        # cos(pi)=-1, sin(pi)=0 even though |pi|>1.
        center = (p.lower + p.upper) / 2
        radius = (p.upper - p.lower) / 2
        c = taylor_trig_at_rational(center, cosine=True)
        s = taylor_trig_at_rational(center, cosine=False)
        self.assertLessEqual(c.lower - radius, -1)
        self.assertGreaterEqual(c.upper + radius, -1)
        self.assertLessEqual(s.lower - radius, 0)
        self.assertGreaterEqual(s.upper + radius, 0)

    def test_reject_unsafe_phase_parameters(self):
        for a, b in ((-1, 2), (2, 2), (1, 0), (1, 10_000_000_001)):
            with self.subTest(a=a, b=b), self.assertRaises(ValueError):
                ideal_rational_pi_phase(a, b)
        with self.assertRaises(ValueError):
            arctan_reciprocal_interval(1)
        with self.assertRaises(ValueError):
            taylor_trig_at_rational(F(8), cosine=True)


if __name__ == "__main__":
    unittest.main()

"""Independent parser tests; stdlib-only, no QuPRS installation required."""
from fractions import Fraction
import unittest

from d4_transport import parse_d4_printed


class D4TransportTests(unittest.TestCase):
    def test_complex_fraction_and_printed_granularity(self):
        count = parse_d4_printed(
            "c s exact arb float -2.500e-40+1.2500e-30i\n"
        )
        self.assertEqual(count.real, Fraction(-25, 10**41))
        self.assertEqual(count.imag, Fraction(125, 10**32))
        self.assertEqual(count.real_half_unit, Fraction(5, 10**44))
        self.assertEqual(count.imag_half_unit, Fraction(5, 10**35))
        self.assertFalse(count.arithmetic_certified)

    def test_integer_real_and_zero_dialects(self):
        self.assertEqual(parse_d4_printed("c s exact arb int 8\n").real, 8)
        self.assertEqual(parse_d4_printed("c s exact arb float 0.125\n").real, Fraction(1, 8))
        self.assertEqual(parse_d4_printed("c s exact arb float 0+0i\n").imag, 0)

    def test_conflicting_or_nonfinite_fail_closed(self):
        for source in (
            "c s exact arb float nan+0i\n",
            "c s exact arb float 1e9999+0i\n",
            "c s exact arb float 1+-3ei\n",
            "c s exact arb int 1.5\n",
            "c s exact arb float 1+0i\nc s exact arb float 2+0i\n",
            "c s exact arb cpx 1+0i\n",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                parse_d4_printed(source)

    def test_duplicate_equal_counts_keeps_conservative_unit(self):
        count = parse_d4_printed(
            "c s exact arb float 1.0000+0i\n"
            "c s exact arb float 1.0+0i\n"
        )
        self.assertEqual(count.real, 1)
        self.assertEqual(count.real_half_unit, Fraction(5, 100))


if __name__ == "__main__":
    unittest.main()

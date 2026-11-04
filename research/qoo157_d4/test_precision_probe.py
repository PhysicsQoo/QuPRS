"""Exact Fraction oracle contract for near-cancellation d4 precision probes."""
from fractions import Fraction
import unittest

from poc_d4 import oracle_count, parse_cnf
from precision_probe import SWEEP, IMAG_SWEEP, cases, one_plus_inverse_power


class PrecisionProbeOracleTests(unittest.TestCase):
    def test_exact_nonzero_residuals_survive_oracle(self):
        fixtures = cases()
        self.assertEqual(len(fixtures), len(SWEEP) + len(IMAG_SWEEP) + 1)
        for k in SWEEP:
            with self.subTest(k=k, component="real"):
                source = fixtures[f"real_residual_1e-{k}"]
                self.assertEqual(parse_cnf(source)[0], 1)
                self.assertEqual(oracle_count(source), (Fraction(1, 10**k), 0))
        for k in IMAG_SWEEP:
            with self.subTest(k=k, component="imaginary"):
                source = fixtures[f"imag_residual_1e-{k}"]
                self.assertEqual(oracle_count(source), (0, Fraction(1, 10**k)))
        self.assertEqual(
            oracle_count(fixtures["large_cancellation_keep_one"]), (1, 0)
        )

    def test_exact_decimal_generator_does_not_use_binary_floats(self):
        self.assertEqual(one_plus_inverse_power(1), "1.1")
        self.assertEqual(one_plus_inverse_power(20), "1." + "0" * 19 + "1")
        with self.assertRaises(ValueError):
            one_plus_inverse_power(0)
        with self.assertRaises(ValueError):
            one_plus_inverse_power(101)


if __name__ == "__main__":
    unittest.main()

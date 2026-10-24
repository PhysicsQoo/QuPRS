"""Dependency-free proof and negative controls for tiny interval model counts."""
from fractions import Fraction as F
import unittest

from interval_wmc import (
    MAX_VARIABLES, Interval, ComplexInterval, WeightedCNF,
    normalized_magnitude, unit_phase_rational_radians,
)


def exact(re=0, im=0):
    return ComplexInterval.exact(re, im)


def trace_problem(delta):
    half = delta / 2
    return WeightedCNF((), ((unit_phase_rational_radians(half),
                             unit_phase_rational_radians(-half)),))


class IntervalCountingTests(unittest.TestCase):
    def test_exact_physical_controls(self):
        for weight, phase in ((exact(1), 'identity'),
                              (exact(-1), 'minus_identity'),
                              (exact(0, 1), 'imag_phase')):
            with self.subTest(phase=phase):
                result = WeightedCNF((), ((weight, weight),)).count()
                magnitude = normalized_magnitude(result, 2)
                self.assertEqual(magnitude, Interval.exact(1))

    def test_taylor_zero_has_no_fabricated_uncertainty(self):
        self.assertEqual(unit_phase_rational_radians(F(0)), exact(1))

    def test_small_rz_has_rigorous_upper_less_than_one(self):
        # Analytic certificate: |Tr(RZ(delta))|/2=cos(delta/2)<1
        # for these nonzero exact rational radian angles.
        for delta in (F(1, 10**3), F(1, 10**6), F(1, 100)):
            with self.subTest(delta=str(delta)):
                count = trace_problem(delta).count()
                norm = normalized_magnitude(count, 2)
                self.assertGreater(norm.lower, 0)
                self.assertLess(norm.upper, 1, (delta, norm))
                self.assertLess(count.abs_squared().upper, F(4))
                self.assertLess(norm.upper - norm.lower, F(1, 10**20))

    def test_signed_complex_weight_cancellation(self):
        weights = ((exact(F(1, 2), F(1, 3)),
                    exact(-F(1, 2), -F(1, 3))),)
        result = WeightedCNF((), weights).count()
        self.assertEqual(result, exact())
        self.assertEqual(normalized_magnitude(result, 2), Interval.exact(0))

    def test_xor_two_variable_weighted_reference(self):
        # Only assignments (x1=true,x2=false) and the reverse satisfy XOR.
        # Count = 1*4+2*3=10, independent of QuPRS and native solvers.
        cnf = WeightedCNF(((1, 2), (-1, -2)),
                          ((exact(1), exact(2)), (exact(3), exact(4))))
        self.assertEqual(cnf.count(), exact(10))

    def test_constraints_and_empty_clauses(self):
        weights = ((exact(1), exact(2)),)
        self.assertEqual(WeightedCNF(((1,),), weights).count(), exact(1))
        self.assertEqual(WeightedCNF(((1, -1),), weights).count(), exact(3))
        self.assertEqual(WeightedCNF(((1,), (-1,)), weights).count(), exact())
        self.assertEqual(WeightedCNF(((),), weights).count(), exact())

    def test_outward_interval_complex_multiplication(self):
        z = ComplexInterval(Interval(F(-1), F(2)), Interval(F(1), F(3)))
        product = z * z
        for real, imag in ((-1, 1), (-1, 3), (2, 1), (2, 3)):
            expected = complex(real, imag) ** 2
            self.assertLessEqual(product.real.lower, expected.real)
            self.assertGreaterEqual(product.real.upper, expected.real)
            self.assertLessEqual(product.imag.lower, expected.imag)
            self.assertGreaterEqual(product.imag.upper, expected.imag)

    def test_reject_float_inputs_and_unsupported_angles(self):
        with self.assertRaises(TypeError):
            Interval.exact(0.1)
        with self.assertRaises(TypeError):
            unit_phase_rational_radians(0.001)
        with self.assertRaises(ValueError):
            unit_phase_rational_radians(F(2))

    def test_invalid_constraints_and_bounds_fail_closed(self):
        with self.assertRaises(ValueError):
            Interval(F(1), F(0))
        with self.assertRaises(ValueError):
            WeightedCNF(((2,),), ((exact(), exact()),))
        with self.assertRaises(ValueError):
            WeightedCNF(((0,),), ((exact(), exact()),))
        with self.assertRaises(ValueError):
            WeightedCNF((), tuple((exact(), exact()) for _ in range(MAX_VARIABLES + 1)))
        with self.assertRaises(ValueError):
            normalized_magnitude(exact(1), 0)


if __name__ == '__main__':
    unittest.main()

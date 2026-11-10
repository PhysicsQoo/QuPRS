"""Independent exact oracle for tiny existentially projected complex WMC.

This tests the mathematical reference, not a solver's proprietary CNF dialect,
printed precision, numerical certificate, or production equivalence verdict.
"""

from fractions import Fraction
from itertools import product
import unittest


ComplexQ = tuple[Fraction, Fraction]
ONE: ComplexQ = (Fraction(1), Fraction(0))
ZERO: ComplexQ = (Fraction(0), Fraction(0))


def _add(a: ComplexQ, b: ComplexQ) -> ComplexQ:
    return a[0] + b[0], a[1] + b[1]


def _multiply(a: ComplexQ, b: ComplexQ) -> ComplexQ:
    return a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]


def exact_projected_count(
    variables: int,
    clauses: tuple[tuple[int, ...], ...],
    projected: tuple[int, ...],
    signed_weights: dict[int, ComplexQ],
    factor: ComplexQ = ONE,
) -> tuple[bool, ComplexQ]:
    """Sum distinct projected satisfying assignments, with exact rational weights.

    Hidden variables establish existential satisfiability; multiple witnesses
    for the same projected assignment contribute only once. Weights are
    restricted to projected variables so hidden-variable weight semantics
    cannot be accidentally conflated with ordinary weighted model counting.
    The global factor is applied exactly once after the model sum.
    """
    if type(variables) is not int or variables < 0:
        raise ValueError("Invalid CNF variable count")
    if len(projected) != len(set(projected)) or any(
        type(v) is not int or not 1 <= v <= variables for v in projected
    ):
        raise ValueError("Invalid projection")
    if any(
        type(lit) is not int or not 1 <= abs(lit) <= variables
        for clause in clauses for lit in clause
    ):
        raise ValueError("Invalid clause literal")
    if any(type(lit) is not int or abs(lit) not in projected or lit == 0
           for lit in signed_weights):
        raise ValueError("Weights must belong to projected variables")

    hidden = tuple(v for v in range(1, variables + 1) if v not in projected)
    total = ZERO
    has_model = False
    for bits in product((False, True), repeat=len(projected)):
        visible = dict(zip(projected, bits))
        has_extension = False
        for hidden_bits in product((False, True), repeat=len(hidden)):
            assignment = visible | dict(zip(hidden, hidden_bits))
            if all(
                any(assignment[abs(lit)] == (lit > 0) for lit in clause)
                for clause in clauses
            ):
                has_extension = True
                break
        if not has_extension:
            continue
        has_model = True
        weight = ONE
        for variable in projected:
            lit = variable if visible[variable] else -variable
            weight = _multiply(weight, signed_weights.get(lit, ONE))
        total = _add(total, weight)
    return has_model, _multiply(total, factor)


class ProjectedComplexWmcOracleTests(unittest.TestCase):
    def test_existential_witness_is_counted_once(self):
        valid, count = exact_projected_count(
            2, ((1, 2),), (1,),
            {1: (Fraction(0), Fraction(1)), -1: ONE},
        )
        self.assertTrue(valid)
        self.assertEqual(count, (Fraction(1), Fraction(1)))

    def test_signed_complex_weights_and_nonunit_global_factor(self):
        valid, count = exact_projected_count(
            3, ((1, 3), (-3, 2)), (1, 2),
            {
                1: (Fraction(0), Fraction(1)),
                -1: ONE,
                2: (Fraction(3, 2), Fraction(1, 4)),
                -2: (Fraction(-1, 2), Fraction(1, 4)),
            },
            factor=(Fraction(2), Fraction(1, 3)),
        )
        self.assertTrue(valid)
        self.assertEqual(count, (Fraction(19, 12), Fraction(17, 6)))

    def test_zero_weighted_count_does_not_imply_unsatisfiable(self):
        valid, count = exact_projected_count(
            1, (), (1,), {1: ONE, -1: (Fraction(-1), Fraction(0))}
        )
        self.assertTrue(valid)
        self.assertEqual(count, ZERO)
        unsat, empty_count = exact_projected_count(
            1, ((),), (1,), {1: ONE}
        )
        self.assertFalse(unsat)
        self.assertEqual(empty_count, ZERO)

    def test_empty_projection_counts_an_existential_witness_once(self):
        valid, count = exact_projected_count(
            2, ((1, 2),), (), {}, factor=(Fraction(3, 2), Fraction(-1, 4))
        )
        self.assertTrue(valid)
        self.assertEqual(count, (Fraction(3, 2), Fraction(-1, 4)))

    def test_hidden_weight_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "projected variables"):
            exact_projected_count(2, (), (1,), {2: ONE})


if __name__ == "__main__":
    unittest.main()

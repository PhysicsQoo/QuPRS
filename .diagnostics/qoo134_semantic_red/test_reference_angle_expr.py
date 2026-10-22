"""GREEN reference-model tests for exact angle-domain expressions ONLY.

A model for proposed future architecture, not installed into QuPRS native.
The decimal-radian and rational-π dimensions must stay distinct until
an explicitly sound numerical/exact verification boundary.
"""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
import pytest


@dataclass(frozen=True)
class AngleExpr:
    # Exact algebraic expression in the basis (pi, radians).
    pi_weight: Fraction = Fraction(0)
    rad_weight: Fraction = Fraction(0)

    @classmethod
    def decimal_radians(cls, literal):
        return cls(rad_weight=Fraction(Decimal(literal)))

    @classmethod
    def pi_fraction(cls, numerator, denominator):
        return cls(pi_weight=Fraction(numerator, denominator))

    def __add__(self, other):
        return AngleExpr(self.pi_weight + other.pi_weight,
                         self.rad_weight + other.rad_weight)

    def __neg__(self):
        return AngleExpr(-self.pi_weight, -self.rad_weight)

    def __sub__(self, other):
        return self + (-other)


@pytest.mark.parametrize("left,right,sum_literal", [
    ("-2.5802058126763807", "-2.5802058126763807",
     "-5.1604116253527614"),
    ("1.6198837120072371", "-2.5802058126763807",
     "-0.9603221006691436"),
    ("1.3499030933393643", "0.125", "1.4749030933393643"),
])
def test_exact_decimal_radians_are_additive(left, right, sum_literal):
    total = (AngleExpr.decimal_radians(left)
             + AngleExpr.decimal_radians(right))
    assert total == AngleExpr.decimal_radians(sum_literal)
    # Comparison is symbolic equality, not a configurable loose epsilon.
    assert (total - AngleExpr.decimal_radians(sum_literal)) == AngleExpr()


def test_exact_pi_fraction_addition_preserves_symbolic_identity():
    a = AngleExpr.pi_fraction(1, 8)
    assert a + a == AngleExpr.pi_fraction(1, 4)
    assert AngleExpr.pi_fraction(1, 4) != AngleExpr.decimal_radians("0.7853981633974483")


@pytest.mark.parametrize("a,b", [
    ("0.125", "0.126"), ("0.0", "0.001"),
    ("0.0", "0.2"), ("0.0", "3.0"),
])
def test_true_inequivalent_rotations_never_collapse_to_equal_expression(a,b):
    assert AngleExpr.decimal_radians(a) != AngleExpr.decimal_radians(b)
    assert (AngleExpr.decimal_radians(a)
            - AngleExpr.decimal_radians(b)).rad_weight != 0


def test_big_rational_required_over_i64_budget():
    # Honest bound: decimal literals with 17+ digits already give denominators
    # well beyond the old 1e9 CF cap. Repeated circuit algebra may exceed i64.
    x = AngleExpr.decimal_radians("-2.5802058126763807")
    assert x.rad_weight.denominator > 1_000_000_000
    assert (x+x-x-x) == AngleExpr()

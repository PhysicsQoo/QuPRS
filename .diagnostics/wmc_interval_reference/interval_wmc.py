"""Tiny, exact-rational interval WMC reference for research diagnostics.

This is intentionally independent of the QuPRS Path-sum/solver implementation.
It does not certify a QuPRS-generated CNF or any native solver's arithmetic.
"""
from dataclasses import dataclass
from fractions import Fraction
from math import factorial, isqrt

MAX_VARIABLES = 12


def _rational(value):
    if isinstance(value, bool):
        raise TypeError('Boolean is not a rational bound')
    if isinstance(value, (int, Fraction)):
        return Fraction(value)
    raise TypeError('Use int or Fraction; floating-point inputs are not certified')


@dataclass(frozen=True)
class Interval:
    lower: Fraction
    upper: Fraction

    def __post_init__(self):
        lo, hi = _rational(self.lower), _rational(self.upper)
        if lo > hi:
            raise ValueError('Interval lower bound exceeds upper bound')
        object.__setattr__(self, 'lower', lo)
        object.__setattr__(self, 'upper', hi)

    @classmethod
    def exact(cls, value):
        v = _rational(value)
        return cls(v, v)

    def __add__(self, other):
        return Interval(self.lower + other.lower, self.upper + other.upper)

    def __neg__(self):
        return Interval(-self.upper, -self.lower)

    def __sub__(self, other):
        return self + (-other)

    def __mul__(self, other):
        p = (self.lower * other.lower, self.lower * other.upper,
             self.upper * other.lower, self.upper * other.upper)
        return Interval(min(p), max(p))

    def square(self):
        hi = max(self.lower * self.lower, self.upper * self.upper)
        lo = (Fraction(0) if self.lower <= 0 <= self.upper
              else min(self.lower * self.lower, self.upper * self.upper))
        return Interval(lo, hi)

    def divided_by_positive_integer(self, divisor):
        if isinstance(divisor, bool) or not isinstance(divisor, int) or divisor <= 0:
            raise ValueError('Normalization must be a positive integer')
        return Interval(self.lower / divisor, self.upper / divisor)


@dataclass(frozen=True)
class ComplexInterval:
    real: Interval
    imag: Interval

    @classmethod
    def exact(cls, real=0, imag=0):
        return cls(Interval.exact(real), Interval.exact(imag))

    def __add__(self, other):
        return ComplexInterval(self.real + other.real, self.imag + other.imag)

    def __mul__(self, other):
        return ComplexInterval(
            self.real * other.real - self.imag * other.imag,
            self.real * other.imag + self.imag * other.real,
        )

    def abs_squared(self):
        return self.real.square() + self.imag.square()


def _alternating_series_nonnegative(x, *, cosine, terms=6):
    """Rigorous enclosure from consecutive alternating Taylor partial sums.

    For 0 <= x <= 1 the magnitudes of successive terms decrease. The
    actual sin/cos lies between partial sums S_{terms-1} and S_terms.
    Exact rational evaluation guarantees outward bounds without mpmath.
    """
    x = _rational(x)
    if not 0 <= x <= 1 or not 1 <= terms <= 30:
        raise ValueError('Certified Taylor enclosure requires 0 <= x <= 1')
    power = 0 if cosine else 1
    total = sum(((-1) ** k) * x ** (power + 2 * k) /
                factorial(power + 2 * k) for k in range(terms))
    next_sum = total + ((-1) ** terms) * x ** (power + 2 * terms) / factorial(power + 2 * terms)
    return Interval(min(total, next_sum), max(total, next_sum))


def unit_phase_rational_radians(angle):
    """Enclose exp(i*angle) for *exact rational radian* angle, |angle|<=1.

    A decimal written in QASM need not denote these exact radians through
    the entire existing encoding pipeline; this function claims no such fact.
    """
    angle = _rational(angle)
    cosine = _alternating_series_nonnegative(abs(angle), cosine=True)
    sine = _alternating_series_nonnegative(abs(angle), cosine=False)
    return ComplexInterval(cosine, sine if angle >= 0 else -sine)


@dataclass(frozen=True)
class WeightedCNF:
    """Conjunctive clauses and per-variable (positive, negative) weights.

    All n variables are assigned even if the CNF does not mention them.
    Clause literals are nonzero integers in +/-[1,n]. No solver called.
    """
    clauses: tuple
    weights: tuple

    def __post_init__(self):
        n = len(self.weights)
        if not 1 <= n <= MAX_VARIABLES:
            raise ValueError(f'Reference supports 1..{MAX_VARIABLES} variables')
        if any(not isinstance(w, tuple) or len(w) != 2 or
               any(not isinstance(z, ComplexInterval) for z in w)
               for w in self.weights):
            raise TypeError('Each variable requires two ComplexInterval weights')
        for clause in self.clauses:
            if not isinstance(clause, tuple):
                raise TypeError('Clauses must be tuples')
            for literal in clause:
                if (isinstance(literal, bool) or not isinstance(literal, int)
                        or literal == 0 or abs(literal) > n):
                    raise ValueError(f'Invalid literal {literal!r} for n={n}')

    def count(self):
        """Exact-rational interval sum over ALL satisfying assignments."""
        result = ComplexInterval.exact()
        for bits in range(1 << len(self.weights)):
            def is_true(literal):
                truth = bool(bits & (1 << (abs(literal) - 1)))
                return truth if literal > 0 else not truth
            if not all(any(is_true(lit) for lit in clause) for clause in self.clauses):
                continue
            weight = ComplexInterval.exact(1)
            for index, (positive, negative) in enumerate(self.weights):
                weight = weight * (positive if bits & (1 << index) else negative)
            result = result + weight
        return result


def _sqrt_fraction_bounds(number, decimal_digits=35):
    """Outward integer-square-root bounds, never a floating sqrt."""
    number = _rational(number)
    if number < 0 or not 1 <= decimal_digits <= 100:
        raise ValueError('sqrt requires nonnegative rational and digits 1..100')
    scale = 10 ** decimal_digits
    floor = isqrt((number.numerator * scale * scale) // number.denominator)
    exact = (floor * floor * number.denominator == number.numerator * scale * scale)
    return Fraction(floor, scale), Fraction(floor if exact else floor + 1, scale)


def normalized_magnitude(count, normalization):
    """Outward interval for |count|/positive normalization, not a verdict."""
    if not isinstance(count, ComplexInterval):
        raise TypeError('count must be a ComplexInterval')
    if isinstance(normalization, bool) or not isinstance(normalization, int) or normalization <= 0:
        raise ValueError('Normalization must be a positive integer')
    squared = count.abs_squared().divided_by_positive_integer(normalization ** 2)
    lo, _ = _sqrt_fraction_bounds(squared.lower)
    _, hi = _sqrt_fraction_bounds(squared.upper)
    return Interval(lo, hi)


def serialize_interval(interval):
    return {'lower': str(interval.lower), 'upper': str(interval.upper)}


def serialize_complex(value):
    return {'real': serialize_interval(value.real), 'imag': serialize_interval(value.imag)}

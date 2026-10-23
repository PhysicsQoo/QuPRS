"""Exact rational bounds for exp(2*pi*i*w), w a rational phase coefficient.

The bounds are rigorous for the coefficient *actually stored in a Rust
PhasePolynomial*, not for its original floating QASM angle. No assumptions
about libm correct rounding or solver floating arithmetic are required.
"""
from fractions import Fraction
from math import factorial

from interval_wmc import ComplexInterval, Interval

_PHASE_LIMIT = 10_000_000_000


def arctan_reciprocal_interval(denom, terms=90):
    """Enclose arctan(1/denom) by adjacent alternating partial sums."""
    if not isinstance(denom, int) or denom < 2 or not 1 <= terms <= 120:
        raise ValueError("Unsupported Machin arctangent parameters")
    q = Fraction(1, denom)
    partial = sum(
        (-1) ** k * q ** (2 * k + 1) / (2 * k + 1)
        for k in range(terms)
    )
    next_value = partial + (-1) ** terms * q ** (2 * terms + 1) / (2 * terms + 1)
    return Interval(min(partial, next_value), max(partial, next_value))


def pi_interval():
    # Machin's identity: pi = 16 atan(1/5) - 4 atan(1/239).
    return (arctan_reciprocal_interval(5) * Interval.exact(16)
            - arctan_reciprocal_interval(239) * Interval.exact(4))


def taylor_trig_at_rational(x, *, cosine, terms=48):
    """Lagrange-remainder enclosure valid for any bounded rational x.

    The omitted derivative is <= 1 in absolute value, so no monotonic-term
    assumption is made for |x| > 1.
    """
    if not isinstance(x, Fraction) or not 1 <= terms <= 70 or abs(x) > 7:
        raise ValueError("Unsupported Taylor reference input")
    start = 0 if cosine else 1
    center = sum((-1) ** k * x ** (2 * k + start) /
                 factorial(2 * k + start) for k in range(terms))
    # For cosine S_{2*terms-2}: next Taylor degree is 2*terms-1.
    # For sine S_{2*terms-1}: next Taylor degree is 2*terms.
    missing = 2 * terms - 1 if cosine else 2 * terms
    error = abs(x) ** missing / factorial(missing)
    return Interval(center - error, center + error)


def outward_decimal_interval(interval, digits=50):
    """Rational outward rounding; contains the original huge exact interval.

    This is a certificate-preserving representation bound, NOT a float
    conversion, and keeps serialized numerators/denominators small.
    """
    if not isinstance(interval, Interval) or not 20 <= digits <= 80:
        raise ValueError("Unsupported rigorous decimal enclosure")
    scale = 10 ** digits
    low = interval.lower.numerator * scale // interval.lower.denominator
    high_num = interval.upper.numerator * scale
    high = -(-high_num // interval.upper.denominator)
    return Interval(Fraction(low, scale), Fraction(high, scale))


def ideal_rational_pi_phase(numerator, denominator):
    """Enclose exp(2*pi*i*numerator/denominator) with rational endpoints."""
    if (type(numerator) is not int or type(denominator) is not int
            or not 0 <= numerator < denominator <= _PHASE_LIMIT):
        raise ValueError("Requires reduced, nonnegative phase fraction in [0,1)")
    fraction = Fraction(numerator, denominator)
    pi = pi_interval()
    theta = pi * Interval.exact(2 * fraction)
    center = (theta.lower + theta.upper) / 2
    radius = (theta.upper - theta.lower) / 2
    # The derivatives of sin and cos are bounded by 1 on the real axis:
    # |trig(theta) - trig(center)| <= radius.
    rc = taylor_trig_at_rational(center, cosine=True)
    rs = taylor_trig_at_rational(center, cosine=False)
    return ComplexInterval(
        outward_decimal_interval(Interval(rc.lower - radius, rc.upper + radius)),
        outward_decimal_interval(Interval(rs.lower - radius, rs.upper + radius)),
    )


def union_printed_and_ideal(printed, ideal):
    """An enclosure containing both the exact printed decimal and ideal w.

    This is deliberately broader than either individual reference and is
    *not* an enclosure for every possible originating QASM source angle.
    """
    if not isinstance(printed, ComplexInterval) or not isinstance(ideal, ComplexInterval):
        raise TypeError("Expected complex intervals")
    return ComplexInterval(
        Interval(min(printed.real.lower, ideal.real.lower),
                 max(printed.real.upper, ideal.real.upper)),
        Interval(min(printed.imag.lower, ideal.imag.lower),
                 max(printed.imag.upper, ideal.imag.upper)),
    )


def max_printed_ideal_component_gap(printed, ideal):
    """Conservative upper bound on componentwise printed-vs-ideal mismatch."""
    def max_gap(a, b):
        return max(abs(a.lower - b.upper), abs(a.upper - b.lower))
    return max(max_gap(printed.real, ideal.real),
               max_gap(printed.imag, ideal.imag))

"""Conditional GPMC numerical distance budget for bounded MPFR inputs.

This is a deliberately conservative *engineering model*, not a formal
certificate of GPMC's C++ algorithm, its source-angle parser, or its solver.
Never use printed digits alone as an arithmetic error bound. Only support
small CNFs with bounded weights and explicit GPMC precision provenance.
"""
from dataclasses import dataclass
from fractions import Fraction
from decimal import Decimal
import math

from .precision_count import PrintedCount, PrintedDistanceEvidence, classify_printed_distance

MAX_BUDGET_VARS = 18
SOURCE_WEIGHT_BITS = 100  # Margin below Python's 113-bit weight construction.
MIN_GPMC_DECIMAL_DIGITS = 60


@dataclass(frozen=True)
class GpmcDistanceBudget:
    status: str
    reason: str
    printed_status: str
    normalized_count_uncertainty: str | None
    solver_arithmetic_certified: bool = False
    source_weight_certified: bool = False
    model: str = "bounded_mpfr_precision_model_v1"


def _complex_abs_bound(x, y):
    # Upper bound on L2 magnitude using the L1 norm, exact rational.
    return abs(x) + abs(y)


def classify_gpmc_budgeted_count(
    count: PrintedCount, *, expected_twice_log2: int,
    distance_tolerance: float, precision_digits: int,
    cnf_vars: int, number_of_weights: int, maximum_weight_magnitude_squared: Fraction,
    independent_count: PrintedCount | None = None,
    phase_tolerance: float = 1e-8,
):
    """Calculate a conditional numerical verdict with explicit assumptions.

    The conservative componentwise count-error model is
      E=2^(2*n+20) * (2^-100 + 2^(-floor(digits*log2(10)))).
    It covers a deliberately large operation allowance and a source
    weight accuracy *assumption*, not an externally certified error.
    Two independent precision runs must agree inside the modeled
    componentwise enclosure. This is a numerical verdict, not proof.
    """
    printed=classify_printed_distance(
        count, expected_twice_log2, distance_tolerance,
    )
    if (
        not isinstance(cnf_vars, int)
        or not isinstance(number_of_weights, int)
        or cnf_vars < 0 or cnf_vars > MAX_BUDGET_VARS
        or number_of_weights < 0 or number_of_weights > cnf_vars
        or maximum_weight_magnitude_squared > (Fraction(1) + Fraction(1, 2**60))**2
        or maximum_weight_magnitude_squared < 0
        or precision_digits < MIN_GPMC_DECIMAL_DIGITS
        or independent_count is None
    ):
        return GpmcDistanceBudget(
            "unknown", "unsupported_or_uncrosschecked_precision_budget",
            printed.status, None,
        )
    # Avoid floats in every normalized trace comparison; use exact integer
    # power-of-two exponents and interval arithmetic for output.
    bits=int(precision_digits * 3.321928094887362) - 1
    component_error=2**(2*cnf_vars+20) * (
        Fraction(1,2**SOURCE_WEIGHT_BITS) + Fraction(1,2**bits)
    )
    # Reject precision disagreement BEFORE using either run to decide.
    if (
        abs(count.real - independent_count.real) >
            2*component_error + count.real_print_half_unit + independent_count.real_print_half_unit
        or abs(count.imag - independent_count.imag) >
            2*component_error + count.imag_print_half_unit + independent_count.imag_print_half_unit
    ):
        return GpmcDistanceBudget(
            "unknown", "precision_replay_disagreement",
            printed.status, str(component_error),
        )
    # Two runs must produce the same side of the normalized magnitude
    # distance threshold after including model and printed-rounding error.
    norm_sq=Fraction(2)**expected_twice_log2
    epsilon=Fraction(Decimal(str(distance_tolerance)))
    target=norm_sq*(1-epsilon*epsilon)
    def interval(c):
        re=abs(c.real); im=abs(c.imag)
        e_re=component_error + c.real_print_half_unit
        e_im=component_error + c.imag_print_half_unit
        lower=(max(Fraction(0),re-e_re)**2 +
               max(Fraction(0),im-e_im)**2)
        upper=(re+e_re)**2+(im+e_im)**2
        return lower,upper
    lo,hi=interval(count)
    lo2,hi2=interval(independent_count)
    if lo > norm_sq or lo2 > norm_sq:
        status,reason="unknown","modeled_nonphysical_overshoot"
    elif hi < target and hi2 < target:
        status,reason="not_equivalent","modelled_count_below_distance_threshold"
    elif lo >= target and lo2 >= target:
        # A positive classification remains numerical, not an exact proof;
        # retain the public global-phase distinction.
        phase = math.atan2(float(count.imag), float(count.real))
        status = ("equivalent" if abs(phase) < phase_tolerance else "equivalent*")
        reason = "modelled_count_inside_distance_threshold"
    else:
        status,reason="unknown","modeled_uncertainty_intersects_threshold"
    return GpmcDistanceBudget(
        status,reason,printed.status,str(component_error),
    )

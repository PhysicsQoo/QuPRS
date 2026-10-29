"""Single-invocation conditional GPMC count uncertainty model.

A numerical engineering budget, never a certificate for GPMC arithmetic,
input-source semantics, or reduction rules. Do not silently rerun the solver.
"""
from dataclasses import dataclass
from fractions import Fraction
import math

from .precision_count import (
    PrintedCount, classify_printed_distance, classify_observed_distance,
)

MAX_MODEL_VARS = 512
SOURCE_WEIGHT_BITS = 100
MIN_PRECISION_DIGITS = 60


@dataclass(frozen=True)
class GpmcSingleCountEvidence:
    status: str
    reason: str
    printed_status: str
    component_error: str | None
    source_weight_certified: bool = False
    solver_arithmetic_certified: bool = False
    model: str = "single_pass_conditional_v1"


def classify_gpmc_single_count(
    count: PrintedCount, *, expected_twice_log2: int,
    distance_tolerance: float, phase_tolerance: float,
    cnf_vars: int, number_of_weights: int,
    maximum_weight_magnitude_squared: Fraction,
    precision_digits: int,
) -> GpmcSingleCountEvidence:
    """Classify one printed solver count with explicitly conditional errors.

    Assume source weight accuracy of at least 100 bits and GPMC MPFR
    operations at the requested decimal-digit precision. Both are
    engineering assumptions; no universal count-arithmetic enclosure
    is claimed. Ineligible workloads are unknown, not a false verdict.
    """
    printed = classify_printed_distance(
        count, expected_twice_log2, distance_tolerance,
    )
    eligible = (
        type(cnf_vars) is int and 0 <= cnf_vars <= MAX_MODEL_VARS
        and type(number_of_weights) is int
        and 0 <= number_of_weights <= cnf_vars
        and type(precision_digits) is int
        and MIN_PRECISION_DIGITS <= precision_digits <= 200
        and isinstance(maximum_weight_magnitude_squared, Fraction)
        and 0 <= maximum_weight_magnitude_squared
        <= (Fraction(1) + Fraction(1, 2**60))**2
    )
    if not eligible:
        return GpmcSingleCountEvidence(
            "unknown", "unsupported_single_pass_precision_model",
            printed.status, None,
        )
    # Source conversion allowance, expressed in absolute count units.
    normal_scale = Fraction(2) ** ((expected_twice_log2 + 1) // 2)
    source_component = (
        normal_scale * Fraction(number_of_weights + 1, 2**SOURCE_WEIGHT_BITS)
    )
    # Explicit conditional MPFR operation allowance; not a theorem about
    # GPMC's complete summation algorithm.
    operation_bits = int(precision_digits * math.log2(10)) - 2
    solver_component = Fraction(2) ** (2 * cnf_vars + 20 - operation_bits)
    component_error = source_component + solver_component
    status, evidence = classify_observed_distance(
        count, expected_twice_log2, distance_tolerance, phase_tolerance,
        component_error=component_error,
    )
    return GpmcSingleCountEvidence(
        status,
        "single_pass_uncertified_" + evidence.reason,
        printed.status,
        str(component_error),
    )

"""Precision-aware WMC text transport for opt-in projective-distance checks.

All bounds in this module are *formatting* bounds, conditional on correctly
rounded solver stdout. They say nothing about source angles, weight evaluation,
the numerical counter, or reduction-rule error. A determinate result is a
numerical observation, not a formal equivalence certificate.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import math
import re

PREFIXES = (
    "c s exact double prec-sci", "c s exact arb cpx",
    "c s exact half float", "c s exact single float",
    "c s exact double float", "c s exact quadruple float",
    "c s exact octuple float", "c s exact arb frac",
)
_MAX_DIGITS = 8192
_MAX_EXPONENT = 2048


@dataclass(frozen=True)
class PrintedCount:
    real: Fraction
    imag: Fraction
    real_print_half_unit: Fraction
    imag_print_half_unit: Fraction
    format_name: str


@dataclass(frozen=True)
class PrintedDistanceEvidence:
    status: str
    reason: str
    printed_only: bool = True
    certified_solver_bound: bool = False


def _number_and_unit(text: str) -> tuple[Fraction, Fraction]:
    if len(text) > _MAX_DIGITS:
        raise ValueError("Solver count token exceeds precision transport limit")
    if "/" in text:
        pieces = text.split("/")
        if len(pieces) != 2:
            raise ValueError("Malformed rational solver count")
        numerator, denominator = (int(x) for x in pieces)
        if denominator == 0:
            raise ValueError("Zero denominator in solver count")
        return Fraction(numerator, denominator), Fraction(0)
    match = re.fullmatch(
        r"([+-]?)(\d+(?:\.\d*)?|\.\d+)(?:[eE]([+-]?\d+))?",
        text,
    )
    if match is None:
        raise ValueError("Non-finite or invalid solver count")
    exponent = int(match.group(3) or "0")
    if abs(exponent) > _MAX_EXPONENT:
        raise ValueError("Solver count exponent outside bounded transport range")
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("Malformed decimal solver count") from exc
    if not number.is_finite():
        raise ValueError("Non-finite solver count")
    # MPFR's scientific printer gives a true zero a zero mantissa; its
    # effective output half-unit is zero for that representational zero.
    if number.is_zero():
        return Fraction(0), Fraction(0)
    fractional_digits = len(match.group(2).split(".", 1)[1]) if "." in match.group(2) else 0
    half_unit_exp = exponent - fractional_digits - 1
    unit = Fraction(5) * (
        Fraction(10) ** half_unit_exp
    )
    return Fraction(number), unit


def parse_printed_count_line(line: str) -> PrintedCount | None:
    prefix = next(
        (name for name in PREFIXES
         if line == name or (line.startswith(name) and line[len(name):len(name) + 1].isspace())),
        None,
    )
    if prefix is None:
        return None
    value = re.sub(r"\s+", "", line[len(prefix):]).replace("+-", "-")
    if not value:
        raise ValueError("Empty weighted-count value")
    if not value.endswith("i"):
        re_count, re_unit = _number_and_unit(value)
        return PrintedCount(re_count, Fraction(0), re_unit, Fraction(0), prefix)
    value = value[:-1]
    splits = [
        i for i in range(1, len(value))
        if value[i] in "+-" and value[i - 1] not in "eE"
    ]
    re_string, im_string = (
        (value[:splits[-1]], value[splits[-1]:]) if splits else ("0", value)
    )
    if im_string in ("+", "-"):
        im_string += "1"
    if im_string == "":
        raise ValueError("Empty imaginary weighted-count")
    re_count, re_unit = _number_and_unit(re_string)
    im_count, im_unit = _number_and_unit(im_string)
    return PrintedCount(re_count, im_count, re_unit, im_unit, prefix)


def parse_printed_solver_output(stdout: str) -> PrintedCount:
    found = None
    for line in stdout.splitlines():
        candidate = parse_printed_count_line(line)
        if candidate is not None:
            if found is not None and (found.real, found.imag) != (candidate.real, candidate.imag):
                raise ValueError("Solver output has conflicting decimal counts")
            if found is None:
                found = candidate
    if found is None:
        raise ValueError("Solver output lacks a recognized weighted count")
    return found


def classify_printed_distance(
    count: PrintedCount, expected_twice_log2: int, distance_tolerance: float
) -> PrintedDistanceEvidence:
    """Compare |count|^2 against 2^k (1 - eps^2) without a f64 cast.

    A status here only supports a printed-value numerical heuristic; unknown
    includes known print-resolution ambiguity and nonphysical overshoot.
    Caller must separately account for unbounded solver arithmetic/source
    weight error and must not advertise this as an equivalence proof.
    """
    if not isinstance(expected_twice_log2, int) or isinstance(expected_twice_log2, bool):
        raise ValueError("Normalization exponent must be an integer")
    if abs(expected_twice_log2) > _MAX_EXPONENT:
        raise ValueError("Normalization exponent exceeds precision limit")
    if isinstance(distance_tolerance, bool) or not isinstance(distance_tolerance, (int, float)):
        raise ValueError("Distance tolerance must be finite in (0, 1)")
    epsilon = float(distance_tolerance)
    if not math.isfinite(epsilon) or not 0 < epsilon < 1:
        raise ValueError("Distance tolerance must be finite in (0, 1)")
    eps = Fraction(Decimal(str(epsilon)))
    norm_squared = Fraction(2) ** expected_twice_log2
    threshold = norm_squared * (1 - eps * eps)

    r, i = abs(count.real), abs(count.imag)
    lo_re = max(Fraction(0), r - count.real_print_half_unit)
    lo_im = max(Fraction(0), i - count.imag_print_half_unit)
    hi_re = r + count.real_print_half_unit
    hi_im = i + count.imag_print_half_unit
    magnitude_sq_lower = lo_re * lo_re + lo_im * lo_im
    magnitude_sq_upper = hi_re * hi_re + hi_im * hi_im
    if magnitude_sq_lower > norm_squared:
        return PrintedDistanceEvidence("unknown", "nonphysical_magnitude_overshoot")
    if magnitude_sq_upper < threshold:
        return PrintedDistanceEvidence("not_equivalent", "printed_distance_exceeds_threshold")
    if magnitude_sq_lower >= threshold:
        return PrintedDistanceEvidence("equivalent", "printed_distance_within_threshold")
    return PrintedDistanceEvidence("unknown", "insufficient_printed_resolution")

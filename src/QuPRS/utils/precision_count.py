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


def _number_and_unit(
    text: str, *, reported_significant_digits: int | None = None,
) -> tuple[Fraction, Fraction]:
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
    # GPMC's MPFR %Rg printer uses the reported *significant-digit*
    # precision but suppresses trailing zeros (including after integers).
    # Its "c o precision N" header supplies N; the visible last digit
    # alone is not a correct rounding unit for trimmed %Rg values.
    half_unit_exp = (
        number.adjusted() - reported_significant_digits
        if reported_significant_digits is not None
        else exponent - fractional_digits - 1
    )
    unit = Fraction(5) * (Fraction(10) ** half_unit_exp)
    return Fraction(number), unit


def parse_printed_count_line(
    line: str, *, reported_significant_digits: int | None = None,
) -> PrintedCount | None:
    prefix = next(
        (name for name in PREFIXES
         if line == name or (line.startswith(name) and line[len(name):len(name) + 1].isspace())),
        None,
    )
    if prefix is None:
        return None
    # Only GPMC's high-precision MPFR output advertises %Rg precision.
    # Other solver dialects retain literal visible-last-digit intervals.
    significant_digits = (
        reported_significant_digits
        if prefix == "c s exact double prec-sci" else None
    )
    value = re.sub(r"\s+", "", line[len(prefix):]).replace("+-", "-")
    if not value:
        raise ValueError("Empty weighted-count value")
    if not value.endswith("i"):
        re_count, re_unit = _number_and_unit(value, reported_significant_digits=significant_digits)
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
    re_count, re_unit = _number_and_unit(re_string, reported_significant_digits=significant_digits)
    im_count, im_unit = _number_and_unit(im_string, reported_significant_digits=significant_digits)
    return PrintedCount(re_count, im_count, re_unit, im_unit, prefix)


def parse_printed_solver_output(stdout: str) -> PrintedCount:
    # GPMC announces the MPFR %Rg significant-digit count independently
    # of the formatted result, so collect it before parsing the count.
    precision = None
    for line in stdout.splitlines():
        if line.startswith("c o precision "):
            match = re.fullmatch(r"c o precision (\d+)", line.strip())
            if match is None or not 16 <= int(match.group(1)) <= 200:
                raise ValueError("Invalid GPMC MPFR print precision")
            digits = int(match.group(1))
            if precision is not None and precision != digits:
                raise ValueError("Conflicting GPMC MPFR print precision")
            precision = digits
    found = None
    for line in stdout.splitlines():
        candidate = parse_printed_count_line(
            line, reported_significant_digits=precision
        )
        if candidate is not None:
            if found is not None and (found.real, found.imag) != (candidate.real, candidate.imag):
                raise ValueError("Solver output has conflicting decimal counts")
            if found is None:
                found = candidate
    if found is None:
        raise ValueError("Solver output lacks a recognized weighted count")
    return found



def exactly_count_unweighted_tautology(
    dimacs_text: str, expected_twice_log2: int,
) -> bool:
    """Prove a trivial WMC count without trusting decimal solver output.

    Only accept a well-formed, *unweighted* CNF whose every clause is a
    Boolean tautology (including the clause-free CNF). It therefore has
    exactly 2**variables satisfying assignments. Match that exact integer
    power against the required trace normalization. This is not a generic
    SAT/tautology checker and deliberately rejects anything nontrivial.
    """
    if not isinstance(expected_twice_log2, int) or isinstance(expected_twice_log2, bool):
        return False
    header = None
    clauses = 0
    for raw in dimacs_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("c"):
            if line.startswith("c p weight "):
                return False
            continue
        if line.startswith("p "):
            parts = line.split()
            if header is not None or len(parts) != 4 or parts[:2] != ["p", "cnf"]:
                return False
            try:
                variables, expected_clauses = map(int, parts[2:])
            except ValueError:
                return False
            if variables < 0 or expected_clauses < 0:
                return False
            header = (variables, expected_clauses)
            continue
        if header is None:
            return False
        try:
            literals = [int(value) for value in line.split()]
        except ValueError:
            return False
        if not literals or literals[-1] != 0 or 0 in literals[:-1]:
            return False
        if any(abs(lit) > header[0] for lit in literals[:-1]):
            return False
        literal_set = set(literals[:-1])
        if not any(-lit in literal_set for lit in literal_set):
            return False
        clauses += 1

    return (
        header is not None
        and clauses == header[1]
        and expected_twice_log2 == 2 * header[0]
    )


def classify_printed_distance(
    count: PrintedCount, expected_twice_log2: int, distance_tolerance: float,
    *, component_error: Fraction = Fraction(0),
) -> PrintedDistanceEvidence:
    """Compare |count|^2 against 2^k (1 - eps^2) without a f64 cast.

    A status here only supports a printed-value numerical heuristic; unknown
    includes print-resolution ambiguity and counts outside the distance band.
    Caller must separately account for unbounded solver arithmetic/source
    weight error and must not advertise this as an equivalence proof.

    component_error is a caller-supplied absolute count-unit error bound for
    EACH real/imaginary component, in addition to stdout rounding. Its validity
    is the caller's responsibility; this routine never certifies it.
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
    if not isinstance(component_error, Fraction) or component_error < 0:
        raise ValueError("Component error must be a nonnegative Fraction")
    norm_squared = Fraction(2) ** expected_twice_log2
    threshold = norm_squared * (1 - eps * eps)

    r, i = abs(count.real), abs(count.imag)
    lo_re = max(Fraction(0), r - count.real_print_half_unit - component_error)
    lo_im = max(Fraction(0), i - count.imag_print_half_unit - component_error)
    hi_re = r + count.real_print_half_unit + component_error
    hi_im = i + count.imag_print_half_unit + component_error
    magnitude_sq_lower = lo_re * lo_re + lo_im * lo_im
    magnitude_sq_upper = hi_re * hi_re + hi_im * hi_im
    upper_limit = norm_squared * (1 + eps * eps)
    if magnitude_sq_upper < threshold:
        return PrintedDistanceEvidence("not_equivalent", "printed_distance_exceeds_threshold")
    if magnitude_sq_lower >= threshold and magnitude_sq_upper <= upper_limit:
        return PrintedDistanceEvidence("equivalent", "printed_distance_within_threshold")
    if magnitude_sq_lower > upper_limit:
        return PrintedDistanceEvidence("unknown", "distance_interval_outside_tolerance")
    return PrintedDistanceEvidence("unknown", "insufficient_printed_resolution")



def ganak_print_resolution_distance(
    count: PrintedCount, expected_twice_log2: int, distance_tolerance: float,
) -> float | None:
    """Return an observed-output resolution warning threshold, if necessary.

    The normalized *squared-magnitude* span from the actual printed
    real/imaginary rounding intervals is
        (max(|C|^2) - min(|C|^2)) / 2**expected_twice_log2.
    Its square root expresses that span on the projective-distance
    scale. Warn only when it exceeds the REQUESTED epsilon**2. This
    measures output representation, NOT Ganak's internal arithmetic
    accuracy or a formal error bound on the WMC computation.
    """
    if count.format_name == "c s exact double prec-sci":
        return None  # GPMC is not Ganak.
    if expected_twice_log2 < -_MAX_EXPONENT or expected_twice_log2 > _MAX_EXPONENT:
        return None
    eps = Fraction(Decimal(str(distance_tolerance)))
    if not 0 < eps < 1:
        return None
    r, i = abs(count.real), abs(count.imag)
    r_low = max(Fraction(0), r - count.real_print_half_unit)
    i_low = max(Fraction(0), i - count.imag_print_half_unit)
    r_high = r + count.real_print_half_unit
    i_high = i + count.imag_print_half_unit
    width = ((r_high*r_high + i_high*i_high)
             - (r_low*r_low + i_low*i_low))
    normalized_width = width / (Fraction(2) ** expected_twice_log2)
    if normalized_width <= eps*eps:
        return None
    # This float is for the user-visible warning only; the decision to
    # warn was made with exact rational comparison.
    try:
        return math.sqrt(float(normalized_width))
    except OverflowError:
        return float("inf")


def classify_observed_distance(
    count: PrintedCount, normalization_twice_log2: int,
    distance_tolerance: float, phase_tolerance: float,
    *, component_error: Fraction = Fraction(0),
    ganak_point_estimate: bool = False,
) -> tuple[str, PrintedDistanceEvidence]:
    """Numerical label for a high-precision printed complex count.

    The interval comparison is exact rational; the caller must separately
    justify any source/solver arithmetic assumptions behind component_error.
    Phase classification divides by an exact rational L1 scale before float
    conversion, preventing overflow for large counts.
    """
    evidence = classify_printed_distance(
        count, normalization_twice_log2, distance_tolerance,
        component_error=component_error,
    )
    if evidence.status == "unknown" and ganak_point_estimate and (
        evidence.reason == "insufficient_printed_resolution"
    ):
        # The strict output-format interval cannot decide at this epsilon.
        # As an explicitly uncertified Ganak observation, use the printed
        # complex count's center point; retain the 'unknown' raw evidence
        # for diagnostics and emit the caller's resolution warning.
        norm_squared = Fraction(2) ** normalization_twice_log2
        eps = Fraction(Decimal(str(distance_tolerance)))
        magnitude_sq = count.real**2 + count.imag**2
        if magnitude_sq < norm_squared * (1 - eps**2):
            return "not_equivalent", evidence
    elif evidence.status != "equivalent":
        return evidence.status, evidence
    scale = abs(count.real) + abs(count.imag)
    if scale == 0:
        return "unknown", PrintedDistanceEvidence("unknown", "zero_phase_reference")
    phase = math.atan2(float(count.imag / scale), float(count.real / scale))
    if not math.isfinite(phase):
        return "unknown", PrintedDistanceEvidence("unknown", "unresolved_phase")
    return ("equivalent" if abs(phase) < phase_tolerance else "equivalent*"), evidence


def approximate_printed_log2(count: PrintedCount) -> float:
    """Diagnostic log2(|count|) without f64 conversion of the raw count.

    Normalized magnitude comparisons must still use rational intervals;
    this float is for reporting only, including beyond binary64 count range.
    """
    re, im = abs(count.real), abs(count.imag)
    scale = max(re, im)
    if scale == 0:
        return float("-inf")
    return (
        math.log2(scale.numerator) - math.log2(scale.denominator)
        + math.log2(math.hypot(float(re / scale), float(im / scale)))
    )

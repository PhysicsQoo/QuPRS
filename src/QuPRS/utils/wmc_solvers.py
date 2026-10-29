"""Independent solver command and result-format adapters."""
from decimal import Decimal, localcontext
import math
import re

SOLVER_ARGUMENTS = {
    "gpmc": ("-mode=1",),
    # Both solvers count floating weights; mode 6 emits rounded complex values.
    "ganak": ("--mode=6",),
}
RESULT_PREFIXES = (
    "c s exact double prec-sci",
    "c s exact arb cpx",
    "c s exact half float",
    "c s exact single float",
    "c s exact double float",
    "c s exact quadruple float",
    "c s exact octuple float",
    "c s exact arb frac",
)


def parse_real(component):
    """Convert a decimal or arbitrarily large fraction without integer limits."""
    with localcontext() as context:
        context.prec = 40
        pieces = component.split("/")
        if len(pieces) == 1:
            value = Decimal(pieces[0])
        elif len(pieces) == 2:
            value = Decimal(pieces[0]) / Decimal(pieces[1])
        else:
            raise ValueError(f"Invalid count component: {component}")
        result = float(value)
    if not math.isfinite(result):
        raise ValueError("Weighted count is outside the finite floating-point range")
    return result


def parse_count_line(line):
    """Return a complex count, or None for a non-result line."""
    prefix = next((p for p in RESULT_PREFIXES
                   if line == p or (line.startswith(p) and line[len(p):len(p) + 1].isspace())), None)
    if prefix is None:
        return None
    value = re.sub(r"\s+", "", line[len(prefix):]).replace("+-", "-")
    if not value.endswith("i"):
        return complex(parse_real(value), 0)
    value = value[:-1]
    splits = [i for i in range(1, len(value))
              if value[i] in "+-" and value[i - 1] not in "eE"]
    if splits:
        index = splits[-1]
        real, imaginary = value[:index], value[index:]
    else:
        real, imaginary = "0", value
    if imaginary in ("", "+", "-"):
        imaginary += "1"
    return complex(parse_real(real), parse_real(imaginary))


def classify_weighted_count(real, imag, expected_log2, *, magnitude_tolerance, phase_tolerance):
    """Classify a WMC result without rounding or squaring its components.

    The magnitude policy matches Rust's normalized-amplitude threshold.
    This operates on solver output, *not* on the reducer's symbolic tolerance.
    Global phases outside the zero-phase tolerance remain equivalent*.
    """
    if not all(math.isfinite(v) for v in (real, imag, expected_log2)):
        raise ValueError("Non-finite weighted count or normalization")
    if magnitude_tolerance <= 0 or phase_tolerance <= 0:
        raise ValueError("Weighted-count tolerances must be positive")

    scale = max(abs(real), abs(imag))
    if scale == 0.0:
        return "not_equivalent", float("-inf")

    # log(hypot) without overflowing real**2 + imag**2 or a large norm.
    log_count = math.log2(scale) + math.log2(
        math.hypot(real / scale, imag / scale)
    )
    log_difference = log_count - expected_log2

    # expm1 is accurate near zero; the upper guard avoids overflow when the
    # expected count is far smaller than the observed finite count.
    if log_difference > 2 or abs(math.expm1(log_difference * math.log(2))) >= magnitude_tolerance:
        return "not_equivalent", log_count

    phase = math.atan2(imag, real)  # [-pi, pi], including phases just below 2*pi
    if abs(phase) < phase_tolerance:
        return "equivalent", log_count
    return "equivalent*", log_count


# Engineering guard for approximate projective-distance classifications.
# This is a reproducible, empirical uncertainty band, NOT a certified
# solver error enclosure. Tight tolerances below this floor are inconclusive.
APPROXIMATE_MAGNITUDE_GUARD = 3e-9


def classify_approximate_weighted_count(
    real, imag, expected_log2, *, distance_tolerance, phase_tolerance
):
    """Classify finite-precision WMC evidence against a projective distance.

    D(U,V) = sqrt(1 - |Tr(U^dagger V)|**2 / 4**n).
    The magnitude deficit is compared against the stable threshold
    eps**2 / (1 + sqrt(1 - eps**2)). Near-threshold and unphysical
    magnitude overshoots are inconclusive rather than fabricated proofs.
    """
    # Share the logarithmic normalization with the legacy WMC classifier.
    _legacy, log_count = classify_weighted_count(
        real, imag, expected_log2,
        magnitude_tolerance=1e-8, phase_tolerance=phase_tolerance,
    )
    if log_count == float("-inf"):
        return "not_equivalent", log_count
    epsilon = float(distance_tolerance)
    sq = epsilon * epsilon
    threshold = sq / (1.0 + math.sqrt(1.0 - sq))
    delta = (log_count - expected_log2) * math.log(2.0)
    if delta > 1:
        return "unknown", log_count
    # Use expm1 for cancellation stability near m = 1.
    defect = -math.expm1(delta)
    guard = APPROXIMATE_MAGNITUDE_GUARD
    if defect < -guard:
        return "unknown", log_count
    if abs(defect - threshold) <= guard:
        return "unknown", log_count
    if defect > threshold + guard:
        return "not_equivalent", log_count
    # Only far-inside evidence is accepted. This remains a numerical verdict,
    # never a formal error certificate for the external weighted counter.
    phase = math.atan2(imag, real)
    return (
        "equivalent" if abs(phase) < phase_tolerance else "equivalent*",
        log_count,
    )

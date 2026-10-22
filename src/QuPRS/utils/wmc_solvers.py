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
    "c s exact quadruple float",
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
    """Return *uncertified* WMC diagnostics without manufacturing a proof.

    The current Ganak/GPMC outputs and CNF phase weights carry no verified,
    end-to-end error enclosure. Neither an output equal to the expected
    count nor a count different from it proves a strict unitary relation.
    In particular, a near-unity trace magnitude cannot establish an exact
    equality even modulo global phase.

    This fail-closed gate preserves the normalized logarithmic count for
    diagnostics. Until a separately validated certificate producer/verifier
    exists, all finite numerical counts have status ``unknown``. Symbolic
    reduction decisions are made upstream and remain unaffected.
    """
    if not all(math.isfinite(v) for v in (real, imag, expected_log2)):
        raise ValueError("Non-finite weighted count or normalization")
    if magnitude_tolerance <= 0 or phase_tolerance <= 0:
        raise ValueError("Weighted-count tolerances must be positive")

    scale = max(abs(real), abs(imag))
    if scale == 0.0:
        # A rounded zero is not a certified exact zero of the true trace.
        return "unknown", float("-inf")

    # Preserve the overflow-safe log(count) diagnostic.
    log_count = math.log2(scale) + math.log2(
        math.hypot(real / scale, imag / scale)
    )
    # An arbitrary fixed tolerance is not a certificate of either verdict;
    # even a bitwise f64 match to the expected value is inconclusive.
    return "unknown", log_count

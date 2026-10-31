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



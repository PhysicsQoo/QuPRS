"""Independent exact QASM2 diagonal RZ/P reference, not a general verifier.

For a*pi+b with rational a,b, equality modulo 2*pi is decided using
the irrationality of pi. No floating or WMC result enters the proof.
"""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
import hashlib
import re

ZERO = (Fraction(0), Fraction(0))
NUM = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?")
GATE = re.compile(r"(rz|p)\(([^()]*)\)\s+q\[(\d+)\];")
QREG = re.compile(r"qreg\s+q\[(\d+)\];")


@dataclass(frozen=True)
class Certificate:
    verdict: str
    witness_qubit: int | None
    left_sha256: str
    right_sha256: str
    scope: str = "exact-qasm2-diagonal-rz-p-v1"


def add(a, b):
    return a[0] + b[0], a[1] + b[1]


def sub(a, b):
    return a[0] - b[0], a[1] - b[1]


def zero_mod_2pi(a):
    # (r*pi+s) mod 2*pi == 0 iff rational s==0, integer r even.
    return a[1] == 0 and a[0].denominator == 1 and a[0].numerator % 2 == 0


def source_angle(raw):
    text = raw.strip().lower().replace(" ", "")
    if not text or len(text) > 1024:
        raise ValueError("Missing or oversized angle")
    negative = text.startswith("-")
    if text[0] in "+-":
        text = text[1:]
    parts = text.split("/")
    if len(parts) not in (1, 2):
        raise ValueError("Unsupported source expression")

    def product(expr):
        factor, pi_count = Fraction(1), 0
        for token in expr.split("*"):
            if token == "pi":
                pi_count += 1
            else:
                if not NUM.fullmatch(token):
                    raise ValueError("Unsupported angle token")
                # Bound exponent size before rational materialization.
                # A zero literal such as 0e-1000 remains exact zero.
                mantissa, marker, exponent = token.partition("e")
                if marker and not -512 <= int(exponent) <= 512:
                    if Decimal(mantissa) != 0:
                        raise ValueError("Nonzero decimal exponent exceeds bound")
                factor *= Fraction(Decimal(token))
        if pi_count > 1:
            raise ValueError("Nonlinear pi expression")
        return factor, bool(pi_count)

    a, is_pi = product(parts[0])
    d, denominator_pi = product(parts[1]) if len(parts) == 2 else (Fraction(1), False)
    if not d or denominator_pi:
        raise ValueError("Unsupported or zero denominator")
    value = (-a if negative else a) / d
    return (value, Fraction(0)) if is_pi else (Fraction(0), value)


def parse_diagonal_qasm(source):
    header, n, scal, angles = False, None, ZERO, []
    for raw in source.splitlines():
        line = raw.split("//", 1)[0].strip()
        if not line:
            continue
        if line == "OPENQASM 2.0;":
            if header:
                raise ValueError("Duplicate QASM header")
            header = True
        elif line == 'include "qelib1.inc";':
            continue
        elif (match := QREG.fullmatch(line)):
            if n is not None or not header:
                raise ValueError("Duplicate register or missing header")
            n = int(match[1])
            if not 0 < n <= 32:
                raise ValueError("Unsupported register size")
            angles = [ZERO] * n
        elif (match := GATE.fullmatch(line)) and header and n is not None:
            op, token, index = match.groups()
            q = int(index)
            if q >= n:
                raise ValueError("Qubit outside declared register")
            theta = source_angle(token)
            angles[q] = add(angles[q], theta)
            if op == "rz":
                scal = add(scal, (-theta[0] / 2, -theta[1] / 2))
        else:
            raise ValueError(f"Unsupported QASM2 statement: {line!r}")
    if not header or n is None:
        raise ValueError("Missing QASM2 header or qreg")
    return tuple(angles), scal


def certify(left, right):
    a, scalar_a = parse_diagonal_qasm(left)
    b, scalar_b = parse_diagonal_qasm(right)
    witness = None
    if len(a) != len(b):
        verdict = "not_equivalent"
    else:
        witness = next((i for i, (x, y) in enumerate(zip(a, b))
                        if not zero_mod_2pi(sub(x, y))), None)
        if witness is not None:
            verdict = "not_equivalent"
        elif zero_mod_2pi(sub(scalar_a, scalar_b)):
            verdict = "equivalent"
        else:
            verdict = "equivalent*"
    return Certificate(
        verdict, witness,
        hashlib.sha256(left.encode()).hexdigest(),
        hashlib.sha256(right.encode()).hexdigest(),
    )

"""Fail-closed import of emitted QuPRS GPMC/Ganak weighted DIMACS.

The decimal strings are treated as exact *printed rational tokens*, not
certificates enclosing the underlying transcendental weights or solver output.
This module does not import the native solver, Path-sum or Qiskit.
"""
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import re

from interval_wmc import (
    ComplexInterval, Interval, MAX_VARIABLES, WeightedCNF,
    _sqrt_fraction_bounds,
)

_DECIMAL = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


def decimal_token(token):
    """Exact rational value of a *printed* finite decimal, with safety limits."""
    if len(token) > 120 or not _DECIMAL.fullmatch(token):
        raise ValueError("Unsupported decimal weight token")
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal weight token") from exc
    if not value.is_finite() or abs(value.as_tuple().exponent) > 120:
        raise ValueError("Unsafe or nonfinite decimal weight")
    return Fraction(value)


def parse_weight(payload, solver):
    if solver == "gpmc":
        if len(payload) != 3 or payload[-1] != "0":
            raise ValueError("Expected GPMC real imaginary 0")
        real, imag = decimal_token(payload[0]), decimal_token(payload[1])
    elif solver == "ganak":
        if (len(payload) != 4 or payload[-1] != "0"
                or payload[1] not in ("+", "-")
                or not payload[2].endswith("i")):
            raise ValueError("Expected Ganak real +/- imaginaryi 0")
        real = decimal_token(payload[0])
        imag = decimal_token(payload[2][:-1])
        if imag < 0:
            raise ValueError("Expected Ganak unsigned imaginary magnitude")
        if payload[1] == "-":
            imag = -imag
    else:
        raise ValueError("Unknown weighted DIMACS solver dialect")
    return ComplexInterval.exact(real, imag)


def parse_emitted_dimacs(raw, *, solver):
    """Parse precisely the format emitted by Python QuPRS.to_DIMACS().

    Requires one header, the weighted-count marker, declared in-range literals,
    one zero terminator per clause, no contradictory duplicate weight records
    and a clause count matching the DIMACS header. Unmentioned literals have
    unit positive AND negative weights. All assignments of auxiliary variables
    are enumerated; no CNF is silently truncated or simplified.
    """
    if solver not in ("ganak", "gpmc"):
        raise ValueError("Select ganak or gpmc explicitly")
    if not isinstance(raw, str) or len(raw) > 400_000:
        raise ValueError("Missing or oversized DIMACS source")
    n = None
    expected_clauses = None
    clauses = []
    literals = {}
    header_seen = False
    marker_seen = False
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        fields = stripped.split()
        if fields[:1] == ["p"]:
            if header_seen or fields[:2] != ["p", "cnf"] or len(fields) != 4:
                raise ValueError("Invalid or repeated CNF header")
            try:
                n, expected_clauses = int(fields[2]), int(fields[3])
            except ValueError as exc:
                raise ValueError("Invalid CNF dimensions") from exc
            if not 1 <= n <= MAX_VARIABLES or expected_clauses < 0:
                raise ValueError("CNF outside independent-reference size bound")
            header_seen = True
            continue
        if fields[:2] == ["c", "t"]:
            if fields != ["c", "t", "wmc"] or marker_seen:
                raise ValueError("Missing or duplicate weighted count marker")
            marker_seen = True
            continue
        if fields[:3] == ["c", "p", "weight"]:
            if not header_seen or not marker_seen or len(fields) < 7:
                raise ValueError("Weight outside marked CNF")
            try:
                lit = int(fields[3])
            except ValueError as exc:
                raise ValueError("Invalid weight literal") from exc
            if not lit or abs(lit) > n or lit in literals:
                raise ValueError("Duplicate or out-of-range weighted literal")
            literals[lit] = parse_weight(fields[4:], solver)
            continue
        if fields[0] == "c":
            # Unexpected metadata is not part of this encoder's dialect.
            raise ValueError("Unsupported weighted DIMACS comment")
        if not header_seen or not marker_seen or fields[-1] != "0":
            raise ValueError("Malformed clause or missing WMC header")
        try:
            clause = tuple(int(token) for token in fields[:-1])
        except ValueError as exc:
            raise ValueError("Nonnumeric clause literal") from exc
        if any(lit == 0 or abs(lit) > n for lit in clause):
            raise ValueError("Invalid clause literal")
        clauses.append(clause)
    if not header_seen or not marker_seen or len(clauses) != expected_clauses:
        raise ValueError("Incomplete weighted CNF or clause-count mismatch")
    unit = ComplexInterval.exact(1)
    weights = tuple((literals.get(i, unit), literals.get(-i, unit))
                    for i in range(1, n + 1))
    return WeightedCNF(tuple(clauses), weights)


def normalized_for_pathsum(count, *, num_qubits, num_pathvar):
    """Enclose |count|/2**(n+p/2) for integers n,p without float sqrt.

    The normalization formula follows the Python QuPRS WMC call site.
    This is a bound on the *imported printed weights' reference count* only.
    """
    if (not isinstance(num_qubits, int) or isinstance(num_qubits, bool)
            or not isinstance(num_pathvar, int) or isinstance(num_pathvar, bool)
            or num_qubits < 1 or num_pathvar < 0 or num_qubits > MAX_VARIABLES
            or num_pathvar > MAX_VARIABLES):
        raise ValueError("Unsupported pathsum normalization metadata")
    if not isinstance(count, ComplexInterval):
        raise TypeError("Expected an interval complex count")
    squared = count.abs_squared().divided_by_positive_integer(
        1 << (2 * num_qubits + num_pathvar)
    )
    lo, _ = _sqrt_fraction_bounds(squared.lower)
    _, hi = _sqrt_fraction_bounds(squared.upper)
    return Interval(lo, hi)


def serialized_count_verdict(record):
    """A conservative interpretation of the reference, never native proof."""
    mag = record
    if not isinstance(mag, Interval):
        raise TypeError("Expected magnitude interval")
    if mag.upper < 1:
        return "REFERENCE_MAGNITUDE_BELOW_ONE"
    if mag.lower == mag.upper == 1:
        return "PRINTED_WEIGHT_REFERENCE_EXACTLY_ONE"
    return "REFERENCE_UNRESOLVED"

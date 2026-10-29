"""Independent exact-rational weighted count for small *printed* GPMC CNFs.

This deliberately does not call GPMC, Qiskit, path-sum, or a complex-float
library. It proves only the weighted sum described by the printed CNF, not
the distance between the original quantum circuits or arbitrary GPMC runs.

Usage is bounded (2**12 assignments) and research-only; reject unsupported
CNF directives rather than asserting a reference for a different language.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from fractions import Fraction


MAX_EXACT_VARIABLES = 12
ONE = (Fraction(1), Fraction(0))


def _decimal(token: str) -> Fraction:
    if "/" in token:
        raise ValueError("rational weight extension not in GPMC decimal CNF")
    try:
        value = Decimal(token)
        if not value.is_finite():
            raise ValueError("nonfinite CNF decimal weight")
        return Fraction(value)
    except InvalidOperation as error:
        raise ValueError("invalid decimal CNF token: " + repr(token[:64])) from error


def count_printed_cnf_exact(dimacs: str, *, max_variables: int = MAX_EXACT_VARIABLES):
    """Enumerate all satisfying assignments and sum their complex weights.

    Exact rational multiplication/addition of the *printed* decimal weights
    eliminates solver-arithmetic uncertainty from this reference only.
    """
    variables = None
    declared_clauses = None
    clauses = []
    weights = {}
    mode = None

    for raw in dimacs.splitlines():
        line = raw.strip()
        if not line:
            continue
        t = line.split()
        if t[:2] == ["c", "t"]:
            if t != ["c", "t", "wmc"] or mode is not None:
                raise ValueError("unsupported CNF counting directive")
            mode = "wmc"
        elif t[:3] == ["c", "p", "weight"]:
            if len(t) != 7 or t[-1] != "0":
                raise ValueError("invalid complex GPMC weight line")
            v = int(t[3])
            if not v or v in weights:
                raise ValueError("invalid or duplicate literal weight")
            weights[v] = (_decimal(t[4]), _decimal(t[5]))
        elif line.startswith("c"):
            # Other comments carry no counting semantics.
            if t[:3] == ["c", "p", "gweight"]:
                raise ValueError("unsupported global weight directive")
            continue
        elif t[:2] == ["p", "cnf"]:
            if len(t) != 4 or variables is not None:
                raise ValueError("invalid CNF header")
            variables, declared_clauses = int(t[2]), int(t[3])
            if variables < 0 or declared_clauses < 0:
                raise ValueError("negative header count")
            if variables > max_variables:
                return {"status": "skipped", "reason": "variable_limit",
                        "variables": variables, "limit": max_variables}
        else:
            if variables is None or t[-1] != "0":
                raise ValueError("invalid or unterminated CNF clause")
            clause = tuple(int(x) for x in t[:-1])
            if any(lit == 0 or abs(lit) > variables for lit in clause):
                raise ValueError("clause variable out of range")
            clauses.append(clause)

    if variables is None or mode != "wmc" or len(clauses) != declared_clauses:
        raise ValueError("CNF header/mode/clause count mismatch")
    if any(abs(lit) > variables for lit in weights):
        raise ValueError("weight variable out of range")

    total_re, total_im = Fraction(0), Fraction(0)
    sat_count = 0
    for assignment in range(1 << variables):
        if not all(
            any(
                bool(assignment & (1 << (abs(lit)-1))) == (lit > 0)
                for lit in clause
            )
            for clause in clauses
        ):
            continue
        sat_count += 1
        real, imag = ONE
        for var in range(1, variables + 1):
            lit = var if assignment & (1 << (var - 1)) else -var
            wr, wi = weights.get(lit, ONE)
            real, imag = real * wr - imag * wi, real * wi + imag * wr
        total_re += real
        total_im += imag

    return {
        "status": "observed",
        "variables": variables,
        "clauses": len(clauses),
        "assignments_visited": 1 << variables,
        "satisfying_assignments": sat_count,
        "real": total_re,
        "imag": total_im,
    }


def exact_count_distance_classification(real, imag, twice_log2, eps):
    """Physical distance decision of the exact *printed-CNF* weighted sum."""
    squared = real * real + imag * imag
    norm_sq = Fraction(2) ** twice_log2
    epsilon = Fraction(Decimal(str(eps)))
    if norm_sq <= 0 or not 0 < epsilon < 1:
        raise ValueError("invalid normalization or distance tolerance")
    if squared > norm_sq:
        return "unknown_overshoot"
    return ("not_equivalent" if squared < norm_sq * (1 - epsilon * epsilon)
            else "inside_threshold")

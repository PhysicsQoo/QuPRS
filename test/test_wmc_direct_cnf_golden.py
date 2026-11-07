"""Small independent direct-CNF Complex WMC golden cases for both solvers.

The Fraction oracle enumerates complete Boolean assignments rather than using
either solver, the circuit encoder, or an approximate equivalence verdict.
This is a bounded conformance regression, not a general solver certificate.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import product

import pytest

from QuPRS.interface.ps2wmc import run_wmc


Weight = tuple[Fraction, Fraction]  # Exact (real, imaginary) rational pair.
WEIGHTS: dict[int, Weight] = {
    1: (Fraction(3, 2), Fraction(1, 4)),
    -1: (Fraction(3, 2), Fraction(-1, 4)),  # Conjugate of weight(+1).
    2: (Fraction(-1, 2), Fraction(1, 4)),
    -2: (Fraction(3, 4), Fraction(-1, 4)),
}
CANCEL_WEIGHTS = {
    **WEIGHTS,
    -1: (-WEIGHTS[1][0], -WEIGHTS[1][1]),
}


def _multiply(left: Weight, right: Weight) -> Weight:
    a, b = left
    c, d = right
    return a * c - b * d, a * d + b * c


def _exact_count(
    clauses: tuple[tuple[int, ...], ...], weights: dict[int, Weight]
) -> complex:
    real, imag = Fraction(0), Fraction(0)
    for values in product((False, True), repeat=2):
        if not all(
            any(values[abs(literal) - 1] == (literal > 0) for literal in clause)
            for clause in clauses
        ):
            continue
        first = weights[1 if values[0] else -1]
        second = weights[2 if values[1] else -2]
        re, im = _multiply(first, second)
        real += re
        imag += im
    return complex(float(real), float(imag))


def _solver_cnf(
    solver: str, clauses: tuple[tuple[int, ...], ...], weights: dict[int, Weight]
) -> str:
    lines = [f"p cnf 2 {len(clauses)}", "c t wmc"]
    for literal, (real, imag) in weights.items():
        re, im = float(real), float(imag)
        if solver == "ganak":
            value = f"{re:.17g} {'+' if im >= 0 else '-'} {abs(im):.17g}i"
        else:
            value = f"{re:.17g} {im:.17g}"
        lines.append(f"c p weight {literal} {value} 0")
    lines.extend(" ".join(map(str, clause)) + " 0" for clause in clauses)
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("solver", ("ganak", "gpmc"))
@pytest.mark.parametrize(
    "clauses,weights",
    [
        pytest.param((), WEIGHTS, id="unconstrained"),
        pytest.param(((1,), (-2,)), WEIGHTS, id="forced-sat"),
        pytest.param(((1,), (-1,)), WEIGHTS, id="contradictory-unsat"),
        pytest.param(((1, 2),), WEIGHTS, id="disjunction"),
        pytest.param(((1, 2), (-1, -2)), WEIGHTS, id="xor"),
        pytest.param((), CANCEL_WEIGHTS, id="complex-cancellation"),
    ],
)
def test_direct_weighted_cnf_matches_exact_enumeration(
    tmp_path, solver: str, clauses: tuple[tuple[int, ...], ...],
    weights: dict[int, Weight],
) -> None:
    # All literal weights here are exactly representable in binary64.
    # Ganak's printed-count precision still limits observational agreement.
    expected = _exact_count(clauses, weights)
    cnf = tmp_path / f"{solver}.cnf"
    cnf.write_text(_solver_cnf(solver, clauses, weights), encoding="utf-8")
    observed = complex(*run_wmc(str(cnf), solver))
    assert observed == pytest.approx(expected, rel=1e-8, abs=1e-12)

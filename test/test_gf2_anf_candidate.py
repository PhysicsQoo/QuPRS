"""Isolated GF(2) ANF candidate: does not change QuPRS production code.

This proof of concept is deliberately local to the tests. The production
output-state map still exposes SymPy expressions, and phase-polynomial
coefficients remain in their separate arithmetic domain.
"""

from dataclasses import dataclass
from itertools import product
from random import Random

import pytest
import sympy as sp
from sympy.logic.boolalg import to_anf


@dataclass(frozen=True, slots=True)
class ANFCandidate:
    """A Boolean polynomial over GF(2), using square-free monomials.

    The empty monomial represents one; the empty polynomial represents zero.
    Symmetric difference cancels duplicate monomials. This intentionally
    supports only Boolean algebra, not rational-valued quantum phases.
    """

    monomials: frozenset[frozenset[str]]

    @staticmethod
    def zero():
        return ANFCandidate(frozenset())

    @staticmethod
    def one():
        return ANFCandidate(frozenset({frozenset()}))

    @staticmethod
    def variable(name: str):
        if not isinstance(name, str) or not name:
            raise ValueError("Boolean variable name must be nonempty")
        return ANFCandidate(frozenset({frozenset({name})}))

    def __xor__(self, other):
        if not isinstance(other, ANFCandidate):
            return NotImplemented
        return ANFCandidate(self.monomials ^ other.monomials)

    def __and__(self, other):
        if not isinstance(other, ANFCandidate):
            return NotImplemented
        terms: set[frozenset[str]] = set()
        for left in self.monomials:
            for right in other.monomials:
                monomial = left | right  # x*x == x for Boolean variables.
                if monomial in terms:
                    terms.remove(monomial)
                else:
                    terms.add(monomial)
        return ANFCandidate(frozenset(terms))

    def __invert__(self):
        return self ^ self.one()

    def substitute(self, name: str, replacement: "ANFCandidate"):
        """Single replacement of one variable, not recursive."""
        if not isinstance(replacement, ANFCandidate):
            raise TypeError("Replacement must be a Boolean ANF candidate")
        result = self.zero()
        for term in self.monomials:
            if name in term:
                remaining = ANFCandidate(frozenset({term - {name}}))
                result ^= remaining & replacement
            else:
                result ^= ANFCandidate(frozenset({term}))
        return result

    def evaluate(self, assignment: dict[str, bool]) -> bool:
        return bool(sum(all(assignment[name] for name in mono)
                        for mono in self.monomials) % 2)


def _from_sympy(expr):
    """Test-only parser; not a production SymPy-free conversion bridge."""
    expr = sp.sympify(expr)
    if expr is sp.true or expr == sp.Integer(1):
        return ANFCandidate.one()
    if expr is sp.false or expr == sp.Integer(0):
        return ANFCandidate.zero()
    if isinstance(expr, sp.Symbol):
        return ANFCandidate.variable(str(expr))
    if isinstance(expr, sp.Not):
        return ~_from_sympy(expr.args[0])
    if isinstance(expr, sp.Xor):
        result = ANFCandidate.zero()
        for arg in expr.args:
            result ^= _from_sympy(arg)
        return result
    if isinstance(expr, sp.And):
        result = ANFCandidate.one()
        for arg in expr.args:
            result &= _from_sympy(arg)
        return result
    if isinstance(expr, sp.Or):
        # De Morgan works for Boolean OR; never substitute a numeric addition.
        result = ANFCandidate.one()
        for arg in expr.args:
            result &= ~_from_sympy(arg)
        return ~result
    raise TypeError(f"Unsupported Boolean expression: {type(expr).__name__}")


_VARS = sp.symbols("gf_x gf_y gf_z gf_w")


def _assert_same_truth_table(candidate, oracle):
    oracle = to_anf(sp.sympify(oracle))
    for bits in product((False, True), repeat=len(_VARS)):
        values = dict(zip(_VARS, bits))
        observed = candidate.evaluate({str(k): v for k, v in values.items()})
        expected = bool(oracle.subs(values))
        assert observed == expected, (candidate, oracle, values)


@pytest.mark.parametrize("expr", [
    sp.true, sp.false, 0, 1,
    _VARS[0], sp.Not(_VARS[0]),
    sp.And(_VARS[0], _VARS[0]),
    sp.Xor(_VARS[0], _VARS[0]),
    sp.Or(_VARS[0], _VARS[1]),
    sp.Xor(_VARS[0], sp.And(_VARS[0], _VARS[1])),
    sp.Not(sp.Xor(_VARS[0], _VARS[1])),
    sp.Or(sp.And(_VARS[0], _VARS[1]),
          sp.Not(sp.Xor(_VARS[2], _VARS[3]))),
])
def test_canonical_candidate_matches_sympy_anf_truth_table(expr):
    _assert_same_truth_table(_from_sympy(expr), expr)


def test_boolean_idempotence_and_xor_cancellation():
    x, y = (ANFCandidate.variable(str(s)) for s in _VARS[:2])
    assert x & x == x
    assert x ^ x == ANFCandidate.zero()
    assert x & ~x == ANFCandidate.zero()
    assert x ^ (x & y) ^ (x & y) == x
    assert ~(~x) == x


@pytest.mark.parametrize("replacement", [
    sp.true, sp.false, _VARS[1], sp.Not(_VARS[1]),
    sp.Xor(_VARS[0], _VARS[1]),
    sp.Or(_VARS[2], _VARS[3]),
])
def test_single_symbol_substitution_matches_sympy(replacement):
    x, y, z, w = _VARS
    expressions = (
        x, sp.Xor(x, y), sp.And(x, z), sp.Or(x, z),
        sp.Not(x), sp.Xor(sp.And(x, y), sp.And(x, z)),
        sp.And(y, z), sp.Not(sp.Or(y, w)),
    )
    for expr in expressions:
        candidate = _from_sympy(expr).substitute(str(x), _from_sympy(replacement))
        _assert_same_truth_table(candidate, sp.sympify(expr).subs(x, replacement))


def test_repeated_substitutions_are_explicitly_sequential():
    x, y, z, _ = _VARS
    candidate = _from_sympy(sp.Xor(x, y))
    substitutions = ((str(x), _from_sympy(sp.Xor(y, z))),
                     (str(y), ANFCandidate.one()))
    oracle = sp.Xor(x, y)
    for name, replacement in substitutions:
        candidate = candidate.substitute(name, replacement)
    oracle = to_anf(oracle.subs(x, sp.Xor(y, z)))
    oracle = to_anf(oracle.subs(y, sp.true))
    _assert_same_truth_table(candidate, oracle)


def test_deterministic_nested_boolean_holdouts():
    random = Random(171)
    terminals = list(_VARS) + [sp.true, sp.false]

    def generated(depth):
        if depth == 0:
            return random.choice(terminals)
        operation = random.choice(("not", "and", "or", "xor"))
        a = generated(depth - 1)
        if operation == "not":
            return sp.Not(a)
        b = generated(depth - 1)
        return {"and": sp.And, "or": sp.Or, "xor": sp.Xor}[operation](a, b)

    for _ in range(100):
        expr = generated(3)
        _assert_same_truth_table(_from_sympy(expr), expr)


def test_nonboolean_phase_expression_fails_closed():
    with pytest.raises(TypeError, match="Unsupported Boolean"):
        _from_sympy(sp.Rational(1, 4))
    with pytest.raises(TypeError, match="Unsupported Boolean"):
        _from_sympy(sp.sin(_VARS[0]))
    with pytest.raises(TypeError, match="Replacement"):
        ANFCandidate.variable("x").substitute("x", sp.true)

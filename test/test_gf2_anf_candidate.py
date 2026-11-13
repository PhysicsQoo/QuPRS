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

import symengine as se

from benchmarks.codspeed.test_python_core import _anf_absent, _anf_replace
from QuPRS.pathsum.core import F, PathSum


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


# Boundary research only: keep all public F objects and production logic intact.

def _candidate_as_public_sympy(candidate: ANFCandidate):
    """Rebuild the historical ANF-shaped SymPy object, including constants.

    The final to_anf() call is REQUIRED for public structural parity.
    This conversion carries a real cost, so functional parity alone must not
    be interpreted as a faster drop-in implementation of F.sub().
    """
    terms = []
    for monomial in sorted(
        candidate.monomials, key=lambda m: (len(m), tuple(sorted(m)))
    ):
        if not monomial:
            terms.append(sp.true)
        else:
            terms.append(sp.And(*(sp.Symbol(name) for name in sorted(monomial))))
    return to_anf(sp.Xor(*terms))


def _candidate_public_substitute(value, target, replacement):
    """Explicitly constrained compatibility bridge, never production code.

    F.sub() can retain numeric Integer(0/1) objects and symbol assumptions.
    The candidate models Boolean algebra only and indexes by symbol names.
    For those ambiguous public cases the bridge must reject input rather than
    silently change externally observable representation or symbol identity.
    """
    value = sp.sympify(value)
    target = sp.sympify(target)
    replacement = sp.sympify(replacement)
    if not isinstance(target, sp.Symbol):
        raise TypeError("GF(2) bridge only supports Symbol substitution targets")
    if isinstance(value, sp.Number) or isinstance(replacement, sp.Number):
        raise TypeError("GF(2) bridge does not preserve numeric scalar types")
    symbols = value.free_symbols | replacement.free_symbols | {target}
    if any(symbol != sp.Symbol(str(symbol)) for symbol in symbols):
        raise TypeError("GF(2) string-keyed candidate loses symbol assumptions")
    return _candidate_as_public_sympy(
        _from_sympy(value).substitute(str(target), _from_sympy(replacement))
    )


@pytest.mark.parametrize("value", (
    sp.true,
    sp.false,
    sp.Symbol("gf_x"),
    se.Symbol("gf_y"),
    sp.Xor(sp.Symbol("gf_x"), sp.Symbol("gf_y")),
    sp.And(sp.Symbol("gf_x"), sp.Symbol("gf_y")),
    sp.Xor(sp.Symbol("gf_x"), sp.And(sp.Symbol("gf_x"), sp.Symbol("gf_z"))),
    sp.Or(sp.Symbol("gf_y"), sp.Symbol("gf_z")),  # Non-ANF, absent target
    sp.Not(sp.Symbol("gf_y")),  # Non-ANF, absent target
    sp.Not(sp.Xor(sp.Symbol("gf_x"), sp.Symbol("gf_z"))),
))
@pytest.mark.parametrize("replacement", (
    sp.true,
    sp.false,
    sp.Symbol("gf_z"),
    sp.Not(sp.Symbol("gf_y")),
    sp.Xor(sp.Symbol("gf_x"), sp.Symbol("gf_y")),  # Self-referential
    sp.Or(sp.Symbol("gf_y"), sp.Symbol("gf_z")),
))
def test_public_f_sub_anf_representation_and_type_parity(value, replacement):
    """The full observable SymPy expression type must match F.sub(), not
    merely its truth table or an abstract Boolean result.
    """
    target = sp.Symbol("gf_x")
    original = F(data={"bit": value}, bits=("bit",))
    before = dict(original.data)
    expected = original.sub(target, replacement)
    candidate = _candidate_public_substitute(value, target, replacement)
    assert candidate == expected["bit"]
    assert type(candidate) is type(expected["bit"])
    assert original.data == before, "F.sub must not mutate its input mapping"


@pytest.mark.parametrize("factory", (_anf_absent, _anf_replace), ids=(
    "anf_target_absent", "anf_target_present"
))
def test_frozen_codspeed_f_sub_fixture_semantics_without_timing(factory):
    """Compare existing benchmark inputs, never register or rename IDs."""
    mapping, target, replacement = factory()
    expected = mapping.sub(target, replacement)
    actual = mapping.update_data({
        key: _candidate_public_substitute(value, target, replacement)
        for key, value in mapping.items()
    })
    assert actual.bits == expected.bits
    assert list(actual.items()) == list(expected.items())
    assert repr(actual) == repr(expected)


def test_public_mapping_order_live_items_and_repr_are_not_discarded():
    x, y, z = sp.symbols("gf_x gf_y gf_z")
    mapping = F(
        data={"a": sp.Or(y, z), "b": sp.Xor(x, y)},
        bits=("a", "b"),
    )
    original_items = mapping.items()  # Public live mapping view.
    expected = mapping.sub(x, sp.Not(z))
    candidate = mapping.update_data({
        key: _candidate_public_substitute(value, x, sp.Not(z))
        for key, value in mapping.items()
    })
    assert candidate.bits == expected.bits == ("a", "b")
    assert list(candidate.items()) == list(expected.items())
    assert repr(candidate) == repr(expected)
    assert list(original_items) == [
        ("a", sp.Or(y, z)), ("b", sp.Xor(x, y))
    ]
    assert list(mapping.items()) == list(original_items)


def test_sequential_substitution_preserves_public_expression_types():
    x, y, z = sp.symbols("gf_x gf_y gf_z")
    original = F(
        data={"a": sp.Xor(x, sp.And(y, z)), "b": sp.Or(x, y)},
        bits=("a", "b"),
    )
    expected = original
    candidate = original
    for target, replacement in (
        (x, sp.Xor(y, z)),
        (y, sp.true),
        (z, sp.Not(x)),
    ):
        expected = expected.sub(target, replacement)
        candidate = candidate.update_data({
            key: _candidate_public_substitute(value, target, replacement)
            for key, value in candidate.items()
        })
        assert list(candidate.items()) == list(expected.items())
        assert all(type(candidate[key]) is type(expected[key])
                   for key in candidate.bits)
    assert list(original.items()) == [
        ("a", sp.Xor(x, sp.And(y, z))), ("b", sp.Or(x, y))
    ]


def test_public_numeric_initial_state_has_different_type_from_boolean():
    """SymPy to_anf(1/0) returns Integer, not BooleanTrue/BooleanFalse."""
    x, y = sp.symbols("gf_x gf_y")
    mapping = F(data={"zero": 0, "one": 1}, bits=("zero", "one"))
    result = mapping.sub(x, y)
    assert result["zero"] == sp.Integer(0)
    assert result["one"] == sp.Integer(1)
    assert type(result["zero"]) is type(sp.Integer(0))
    assert type(result["one"]) is type(sp.Integer(1))
    for value in (0, 1):
        with pytest.raises(TypeError, match="numeric scalar"):
            _candidate_public_substitute(value, x, y)
        with pytest.raises(TypeError, match="numeric scalar"):
            _candidate_public_substitute(x, x, value)


def test_assumed_and_dummy_symbols_are_not_string_keyed_equivalent():
    x = sp.Symbol("gf_x")
    for specialized in (sp.Symbol("gf_x", positive=True), sp.Dummy("gf_x")):
        assert specialized != sp.Symbol(str(specialized))
        with pytest.raises(TypeError, match="symbol assumptions"):
            _candidate_public_substitute(specialized, x, sp.true)
        with pytest.raises(TypeError, match="symbol assumptions"):
            _candidate_public_substitute(x, specialized, sp.true)


def test_expression_target_and_phase_values_rejected_at_public_boundary():
    x, y = sp.symbols("gf_x gf_y")
    with pytest.raises(TypeError, match="substitution targets"):
        _candidate_public_substitute(sp.Xor(x, y), sp.And(x, y), sp.true)
    with pytest.raises(TypeError, match="Unsupported Boolean"):
        _candidate_public_substitute(sp.Rational(1, 4) * x, x, y)


def test_real_cx_ccx_output_state_is_compatible_for_untouched_substitution():
    """Use the actual Python gate constructors, without replacing them."""
    circuit = PathSum.QuantumCircuit(3).cx(0, 1).ccx(0, 1, 2)
    absent_target = sp.Symbol("gf_absent")
    for value in circuit.f:
        expected = to_anf(sp.sympify(value))
        candidate = _candidate_public_substitute(
            value, absent_target, sp.true
        )
        assert candidate == expected
        assert type(candidate) is type(expected)

"""F.sub fast-path preserves the historical ANF output and substitution semantics."""
import pytest
import symengine as se
import sympy as sp
from sympy.logic.boolalg import to_anf

from QuPRS.pathsum.core import F


@pytest.mark.parametrize("replacement", [
    sp.Symbol("fastpath_z"),
    sp.Xor(sp.Symbol("fastpath_z"), sp.Symbol("fastpath_w")),
])
def test_output_substitution_matches_full_sympy_oracle(replacement):
    x, y, z, w = sp.symbols("fastpath_x fastpath_y fastpath_z fastpath_w")
    exprs = (
        sp.true,
        sp.false,
        sp.Symbol("unaffected"),
        se.Symbol("also_unaffected"),
        sp.Xor(y, sp.And(y, z)),  # normalized ANF and unaffected
        sp.And(y, z),  # normalized monomial and unaffected
        sp.Or(y, z),  # NOT ANF: still normalize even without x
        sp.Not(y),  # NOT ANF: still normalize even without x
        sp.Xor(x, sp.And(x, y)),  # substitution needed
        sp.And(x, z),  # substitution needed
        sp.Xor(y, sp.And(x, z)),
    )
    original = {str(i): expr for i, expr in enumerate(exprs)}
    f = F(data=original, bits=tuple(original))
    reduced = f.sub(x, replacement)
    for key, expr in original.items():
        assert reduced.data[key] == to_anf(sp.sympify(expr).subs(x, replacement))


def test_unaffected_source_symengine_and_boolean_output_representations():
    x = sp.Symbol("absent_target")
    y = se.Symbol("unaffected_pathvar")
    values = {"0": y, "1": sp.true, "2": sp.false}
    f = F(data=values, bits=tuple(values))
    updated = f.sub(x, sp.Xor(x, sp.Symbol("next_target")))
    assert updated.data == {
        key: to_anf(sp.sympify(value).subs(x, sp.Xor(x, sp.Symbol("next_target"))))
        for key, value in values.items()
    }


def test_unrelated_or_and_not_are_not_skipped():
    x, y, z = sp.symbols("fast_oracle_x fast_oracle_y fast_oracle_z")
    exprs = {"or": sp.Or(y, z), "not": sp.Not(y)}
    f = F(data=exprs, bits=tuple(exprs))
    result = f.sub(x, z)
    assert result.data["or"] == to_anf(exprs["or"])
    assert result.data["not"] == to_anf(exprs["not"])
    assert result.data["or"] != exprs["or"]
    assert result.data["not"] != exprs["not"]

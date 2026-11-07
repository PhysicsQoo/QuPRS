"""Input type and value-domain regressions for symbolic PathSum primitives.

The annotations do not alter the existing conversion or substitution semantics.
"""

from collections.abc import ItemsView

import pytest
import symengine as se
import sympy as sp
from qiskit import QuantumCircuit
from sympy.logic.boolalg import to_anf

from QuPRS.interface.load_qiskit import build_circuit, initialize
from QuPRS.pathsum import F, PathSum


@pytest.mark.parametrize("values", (
    (True, False),
    (sp.true, sp.false),
    (1, 0),
    (sp.Symbol("a"), se.Symbol("b")),
    (sp.Or(sp.Symbol("a"), sp.Symbol("b")), sp.Not(sp.Symbol("a"))),
))
def test_initial_state_sequences_keep_anf_semantics(values):
    ps = PathSum.QuantumCircuit(2, initial_state=values)
    for i, value in enumerate(values):
        assert ps.f[i] == to_anf(value)


def test_qiskit_initial_state_entry_points_keep_sequence_values():
    circuit = QuantumCircuit(2)
    values = (sp.true, sp.false)
    expected = PathSum.QuantumCircuit(2, initial_state=values).f.data
    assert initialize(circuit, initial_state=values).f.data == expected
    assert build_circuit(circuit, initial_state=values).f.data == expected


@pytest.mark.parametrize("collection_type", (set, frozenset))
def test_pathvar_accepts_symbol_sets_without_changing_contents(collection_type):
    base = PathSum.QuantumCircuit(1)
    symbol = se.Symbol("typed_pathvar")
    ps = PathSum(base.P, base.f, collection_type({symbol}))
    assert isinstance(ps.pathvar, frozenset)
    assert ps.pathvar == frozenset({symbol})


def test_f_items_is_a_live_mapping_view_and_keeps_symbolic_values():
    values = {"a": se.Symbol("typed_output"), "b": sp.Xor(sp.Symbol("x"), sp.Symbol("y"))}
    f = F(data=values, bits=tuple(values))
    items = f.items()
    assert isinstance(items, ItemsView)
    assert dict(items) == values
    f.data["c"] = sp.true
    assert dict(items)["c"] is sp.true

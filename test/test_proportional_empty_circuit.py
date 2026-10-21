"""QOO-137: Python Proportional on empty gate lists (native Rust parity).

Clifford fixtures avoid the independent QOO-136 near-unit WMC tolerance bug.
The Qiskit dense-matrix oracle is independent of PathSum and WMC.
"""
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence
from QuPRS.utils import strategy as strategy_module


@pytest.mark.parametrize(
    "ket,bra,expected_order",
    [
        ((), (), ()),
        (("x1", "x2"), (), (("x1", False), ("x2", False))),
        ((), ("x1", "x2"), (("x1", True), ("x2", True))),
    ],
)
def test_proportional_zero_side_preserves_bra_ket_and_reduces(
    monkeypatch, ket, bra, expected_order
):
    """Directly test gate direction, insertion order and returned gate count."""
    events = []

    class DummyPathsum:
        def reduction(self):
            events.append(("reduction",))
            return self

    def fake_add_gate(ps, gate, *, count, is_bra=False):
        events.append((gate, is_bra))
        return ps, count + 1

    monkeypatch.setattr(strategy_module, "add_gate", fake_add_gate)
    strategy = strategy_module.ProportionalStrategy()
    ps = DummyPathsum()
    out = strategy.run(ps, list(ket), list(bra))
    assert out is ps
    assert strategy.count == len(ket) + len(bra)
    assert events == [*expected_order, ("reduction",)]


CASES = (
    ("both_empty", (), (), "equivalent"),
    ("empty_vs_x", (), ("x",), "not_equivalent"),
    ("x_vs_empty", ("x",), (), "not_equivalent"),
    ("empty_vs_xx", (), ("x", "x"), "equivalent"),
    ("xx_vs_empty", ("x", "x"), (), "equivalent"),
    ("empty_vs_xz", (), ("x", "z"), "not_equivalent"),
)


def make_circuit(gates):
    qc = QuantumCircuit(1)
    for gate in gates:
        getattr(qc, gate)(0)
    return qc


@pytest.mark.parametrize("case,ket,bra,expected", CASES, ids=[x[0] for x in CASES])
@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("strategy", ("Naive", "Proportional"))
@pytest.mark.parametrize("method", ("reduction_rules", "hybrid"))
def test_proportional_empty_source_qasm_parity(
    case, ket, bra, expected, backend, strategy, method
):
    left, right = make_circuit(ket), make_circuit(bra)
    # Independent 2x2 oracle; no WMC magnitude acceptance used here.
    unitary_left = Operator(left)
    unitary_right = Operator(right)
    matrix_relation = (
        "equivalent"
        if np.allclose(unitary_left.data, unitary_right.data, atol=1e-12, rtol=0)
        else "equivalent*"
        if unitary_left.equiv(unitary_right, atol=1e-12, rtol=0)
        else "not_equivalent"
    )
    assert matrix_relation == expected, case

    result = check_equivalence(
        left, right, backend=backend, strategy=strategy,
        method=method, tool_name="gpmc", timeout=40,
    )
    assert result.equivalent == expected, (
        f"{case}: {backend}/{strategy}/{method}; "
        f"operator={expected}, got={result.equivalent}"
    )
    assert (result.gate_num, result.gate_num2) == (len(ket), len(bra))


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("method", ("reduction_rules", "hybrid", "wmc_only"))
@pytest.mark.parametrize("case,ket,bra,expected", CASES[:5], ids=[x[0] for x in CASES[:5]])
def test_proportional_wmc_method_regression(case, ket, bra, expected, backend, method):
    """WMC is checked using exact Clifford identities, not near-identity rotations."""
    result = check_equivalence(
        make_circuit(ket), make_circuit(bra),
        backend=backend, method=method, strategy="Proportional",
        tool_name="gpmc", timeout=40,
    )
    assert result.equivalent == expected, (
        case, backend, method, expected, result.equivalent
    )

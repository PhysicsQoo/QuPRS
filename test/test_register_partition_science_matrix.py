"""Small independent-operator regression matrix for register layout and bit order.

Unlike the original Issue #21 crash reproducer, these 20 distinct source
circuits compare the actual full operators as well as QuPRS classifications.
RR-only is allowed to remain incomplete; it must never assert the wrong sign.
No benchmark, performance claim, or mandatory extra solver is introduced.
"""
import pytest
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence


# Each source pattern is distinct; the flattened qubit positions are the
# physical wire identities, regardless of register names/partition.
_PATTERNS = (
    ("h0",),
    ("x1",),
    ("z0",),
    ("s1",),
    ("cx01",),
    ("cx10",),
    ("h0", "cx01"),
    ("x1", "cx10"),
    ("s0", "cx01"),
    ("h1", "cx10"),
    ("h0", "z1", "cx01"),
    ("x0", "h1", "cx10"),
    ("h2",),
    ("cx12",),
    ("cx02",),
    ("h0", "cx02"),
    ("x2", "cx21"),
    ("h1", "cx12"),
    ("s2", "cx02"),
    ("h0", "cx01", "cx12"),
)
_METHODS = ("hybrid", "wmc_only", "reduction_rules")
CASES = tuple(
    (index, pattern, 2 if index < 12 else 3,
     _METHODS[index % len(_METHODS)], index % 2 == 0)
    for index, pattern in enumerate(_PATTERNS)
)


def _apply(circuit, operations):
    for operation in operations:
        if operation.startswith("cx"):
            getattr(circuit, "cx")(int(operation[2]), int(operation[3]))
        else:
            getattr(circuit, operation[0])(int(operation[1]))


def _pair(pattern, count, should_equiv):
    left = QuantumCircuit(QuantumRegister(1, "data"),
                          QuantumRegister(count - 1, "ancilla"))
    right = QuantumCircuit(count)
    _apply(left, pattern)
    _apply(right, pattern)
    if not should_equiv:
        # Non-global difference on physical wire zero; testing a changed
        # source operation, not just different register names.
        right.x(0)
    return left, right


def test_matrix_covers_twenty_distinct_source_circuits():
    assert len(CASES) == len({(count, pattern) for _, pattern, count, _, _ in CASES}) == 20
    assert {method for _, _, _, method, _ in CASES} == set(_METHODS)
    assert {count for _, _, count, _, _ in CASES} == {2, 3}
    for method in _METHODS:
        outcomes = {expected for _, _, _, candidate, expected in CASES
                    if candidate == method}
        assert outcomes == {True, False}


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize(
    "index,pattern,count,method,expected",
    CASES,
    ids=[f"source-{index:02d}" for index in range(len(CASES))],
)
def test_register_partition_operator_oracle(
    backend, index, pattern, count, method, expected
):
    left, right = _pair(pattern, count, expected)
    oracle_equivalent = bool(Operator(left).equiv(Operator(right)))
    assert oracle_equivalent is expected, (
        "Incorrect independent dense-operator fixture", index, pattern
    )

    result = check_equivalence(
        left, right, backend=backend, method=method, strategy="Naive",
        tool_name="gpmc", timeout=30,
        rr_tolerance=0, approximate_distance_tolerance=1e-8,
    )
    if method == "reduction_rules":
        # RR-only is incomplete: unknown is neither a false equivalence
        # nor a false inequivalence. Do not demand a WMC call here.
        accepted = {"unknown", "equivalent", "equivalent*"} if expected else {
            "unknown", "not_equivalent"
        }
        assert result.equivalent in accepted, (
            index, backend, method, result.equivalent
        )
        assert result.wmc_solver_invoked is False
    else:
        # An unknown, Timeout or solver error is not a negative proof.
        accepted = {"equivalent", "equivalent*"} if expected else {"not_equivalent"}
        assert result.equivalent in accepted, (
            index, backend, method, expected, result.equivalent
        )

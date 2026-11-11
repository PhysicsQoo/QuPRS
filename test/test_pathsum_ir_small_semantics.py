"""Full-amplitude witnesses for small Python Path-sum IRs.

The same source-independent operator fixtures are consumed by the native Rust
Path-sum test. Internal symbolic strings and generated variable IDs are not
the semantic oracle; we enumerate the entire input/output matrix, including
global phase, path summation and normalization.
"""
import cmath
from itertools import product
from math import pi, sqrt
from pathlib import Path

import pytest
import symengine as se
import sympy as sp

from QuPRS.pathsum import PathSum


CASES = {
    "h": ("h",),
    "hh": ("h", "h"),
    "hsh": ("h", "s", "h"),
    "xzxz": ("x", "z", "x", "z"),
}


def _one_qubit_reference():
    path = Path(__file__).parent / "fixtures" / "pathsum_ir_small_semantics.tsv"
    cases = {name: [[None, None], [None, None]] for name in CASES}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        name, row, column, real, imag = raw.split()
        assert name in cases
        row, column = int(row), int(column)
        assert row in (0, 1) and column in (0, 1)
        assert cases[name][row][column] is None
        cases[name][row][column] = complex(float(real), float(imag))
    assert all(
        all(value is not None for row in matrix for value in row)
        for matrix in cases.values()
    )
    return cases


def _matrix_from_ir(pathsum):
    assert pathsum.num_qubits == 2
    internal = sorted(pathsum.pathvar, key=str)
    assert len(internal) <= 8, "Only bounded exact-structure examples allowed"
    size = 1 << pathsum.num_qubits
    matrix = [[0j for _ in range(size)] for _ in range(size)]
    normalization = sqrt(1 << len(internal))

    for input_state in range(size):
        for path_bits in product((0, 1), repeat=len(internal)):
            assignment = {
                **{name: (input_state >> q) & 1
                   for q, name in enumerate(pathsum.bits)},
                **{str(var): bit for var, bit in zip(internal, path_bits)},
            }
            phase_sub = {se.Symbol(name): val for name, val in assignment.items()}
            output_sub = {sp.Symbol(name): bool(val) for name, val in assignment.items()}
            phase = pathsum.P.subs(phase_sub)
            assert not phase.free_symbols, "Unbound phase variable in IR witness"
            output_state = 0
            for q in range(pathsum.num_qubits):
                bit_expr = sp.sympify(pathsum.f[q]).subs(output_sub)
                assert not getattr(bit_expr, "free_symbols", set()), (
                    "Unbound output variable in IR witness"
                )
                if bool(bit_expr):
                    output_state |= 1 << q
            matrix[output_state][input_state] += (
                cmath.exp(2j * pi * float(phase)) / normalization
            )
    return matrix


@pytest.mark.parametrize("reduced", (False, True), ids=("unreduced", "reduced"))
@pytest.mark.parametrize("name", tuple(CASES))
def test_pathsum_semantics_match_shared_operator_reference(name, reduced):
    reference = _one_qubit_reference()[name]
    ps = PathSum.QuantumCircuit(2)
    ps.set_reduction_switch(reduced)
    for gate in CASES[name]:
        ps = getattr(ps, gate)(0)
    if reduced:
        ps = ps.reduction()
    actual = _matrix_from_ir(ps)

    for output in range(4):
        for input_state in range(4):
            # Qubit 1 must remain untouched. Qubit 0 follows the fixture.
            expected = (
                reference[output & 1][input_state & 1]
                if (output & 2) == (input_state & 2) else 0j
            )
            assert abs(actual[output][input_state] - expected) < 2e-11, (
                name, reduced, output, input_state,
                actual[output][input_state], expected,
            )

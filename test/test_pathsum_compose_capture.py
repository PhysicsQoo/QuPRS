"""Full-amplitude check for collision-free composition of independent Path-sums.

Independent circuits start with the same internal summation-variable names.
Composition must rename the second circuit's bound variables rather than
accidentally identifying two independent summation variables.
"""
import cmath
from itertools import product
from math import pi, sqrt

import pytest
import symengine as se
import sympy as sp
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS.pathsum import PathSum


def _operator_from_pathsum(pathsum):
    """Enumerate all input, output and summed bits for a bounded 2-qubit IR."""
    assert pathsum.num_qubits == 2
    summed = sorted(pathsum.pathvar, key=str)
    assert len(summed) <= 4
    matrix = [[0j] * 4 for _ in range(4)]
    normalization = sqrt(1 << len(summed))

    for input_bits in range(4):
        for path_bits in product((0, 1), repeat=len(summed)):
            values = {
                **{name: (input_bits >> q) & 1
                   for q, name in enumerate(pathsum.bits)},
                **{str(var): bit for var, bit in zip(summed, path_bits)},
            }
            phase_sub = {se.Symbol(name): bit for name, bit in values.items()}
            boolean_sub = {sp.Symbol(name): bool(bit) for name, bit in values.items()}
            phase = pathsum.P.subs(phase_sub)
            assert not phase.free_symbols
            output_bits = 0
            for q in range(2):
                value = sp.sympify(pathsum.f[q]).subs(boolean_sub)
                assert not getattr(value, "free_symbols", set())
                if bool(value):
                    output_bits |= 1 << q
            matrix[output_bits][input_bits] += (
                cmath.exp(2j * pi * float(phase)) / normalization
            )
    return matrix


@pytest.mark.parametrize("middle", (None, "z", "t"), ids=("hh", "hzh", "hth"))
def test_compose_avoids_summation_variable_capture(middle):
    first = PathSum.QuantumCircuit(2)
    first.set_reduction_switch(False)
    first = first.h(0)
    if middle is not None:
        first = getattr(first, middle)(0)

    second = PathSum.QuantumCircuit(2)
    second.set_reduction_switch(False)
    second = second.h(0)

    assert len(first.pathvar) == len(second.pathvar) == 1
    assert first.pathvar == second.pathvar, "Must exercise an actual name collision"

    composed = first.compose(second)
    assert len(composed.pathvar) == 2, "Independent sums must not be captured"
    assert len(first.pathvar) == len(second.pathvar) == 1

    oracle = QuantumCircuit(2)
    oracle.h(0)
    if middle is not None:
        getattr(oracle, middle)(0)
    oracle.h(0)
    expected = Operator(oracle).data

    for reduced in (False, True):
        result = composed
        if reduced:
            result.set_reduction_switch(True)
            result = result.reduction()
        observed = _operator_from_pathsum(result)
        for output in range(4):
            for input_state in range(4):
                assert abs(observed[output][input_state] - expected[output, input_state]) < 2e-11, (
                    middle, reduced, output, input_state,
                    observed[output][input_state], expected[output, input_state],
                )

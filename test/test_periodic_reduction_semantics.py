"""Small independent operator checks for the scheduled Rust backend."""
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence


def circuit_pair(case):
    n = 2 if case in ('cx', 'swap') else 1
    a, b = QuantumCircuit(n), QuantumCircuit(n)
    # Cross the default checkpoint, then leave a tail; both inputs stay nonempty.
    for circuit in (a, b):
        for _ in range(12):
            circuit.h(0)
    if case == 'hh':
        a.h(0)
        a.h(0)
    elif case == 'cx':
        a.cx(0, 1)
        b.h(1)
        b.cz(0, 1)
        b.h(1)
    elif case == 'swap':
        a.swap(0, 1)
        # The existing Rust QASM parser does not accept native SWAP. Test the
        # common frontend basis; native core SWAP is covered by Rust matrices.
        original = Operator(a).data
        a = a.decompose(gates_to_decompose=['swap'])
        assert np.allclose(Operator(a).data, original, atol=1e-10, rtol=0)
        b.cx(0, 1)
        b.cx(1, 0)
        b.cx(0, 1)
    elif case == 'phase':
        a.x(0)
        a.z(0)
        a.x(0)
        a.z(0)
    elif case == 'different':
        a.x(0)
    elif case == 'non_clifford':
        for circuit in (a, b):
            circuit.t(0)
            circuit.h(0)
            circuit.s(0)
    return a, b


@pytest.mark.parametrize('case', ['hh', 'cx', 'swap', 'phase', 'different', 'non_clifford'])
@pytest.mark.parametrize('strategy', ['Naive', 'Straightforward', 'Proportional', 'Difference'])
@pytest.mark.parametrize('method', ['reduction_rules', 'hybrid', 'wmc_only'])
def test_periodic_backend_status_matches_independent_matrix(case, strategy, method):
    a, b = circuit_pair(case)
    # Qiskit's dense complex operator is independent of either path-sum reducer.
    left, right = Operator(a).data, Operator(b).data
    if np.allclose(left, right, atol=1e-10, rtol=0):
        expected = 'equivalent'
    elif Operator(a).equiv(Operator(b), atol=1e-10, rtol=0):
        expected = 'equivalent*'
    else:
        expected = 'not_equivalent'
    for backend in ('python', 'rust'):
        result = check_equivalence(a, b, method=method, strategy=strategy,
                                   tool_name='ganak', backend=backend)
        assert result.equivalent == expected, (case, strategy, method, backend, result)

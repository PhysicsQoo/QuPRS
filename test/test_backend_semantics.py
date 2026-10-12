"""Small matrix-oracle regressions for both verification backends."""
import itertools
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from QuPRS import check_equivalence

STRATEGIES = ['Difference', 'Straightforward', 'Naive', 'Proportional']

def circuits(case):
    n = 2 if case in ('cx', 'cz') else 3 if case == 'ccx' else 1
    a, b = QuantumCircuit(n), QuantumCircuit(n)
    if case in ('x', 'z', 's', 't', 'sx', 'sxdg'): getattr(b, case)(0)
    elif case in ('cx', 'cz'): getattr(b, case)(0, 1)
    elif case == 'ccx': b.ccx(0, 1, 2)
    elif case == 'hh': b.h(0); b.h(0)
    elif case == 'p': b.p(np.pi, 0)
    elif case == 'small_rz': b.rz(0.001, 0)
    elif case == 'minus_i': b.x(0); b.z(0); b.x(0); b.z(0)
    elif case == 'rz_p': a.rz(0.3, 0); b.p(0.3, 0)
    elif case == 'metadata': b.global_phase = np.pi / 2
    elif case == 'phase_cancel': a.rz(0.3, 0); a.global_phase = 0.15; b.p(0.3, 0)
    return a, b

def expected(a, b):
    ua, ub = Operator(a).data, Operator(b).data
    if np.allclose(ua, ub, atol=1e-12, rtol=0): return 'equivalent'
    if abs(abs(np.trace(ua.conj().T @ ub))/len(ua)-1) < 1e-12: return 'equivalent*'
    return 'not_equivalent'

@pytest.mark.parametrize('backend', ['python', 'rust'])
@pytest.mark.parametrize('method', ['hybrid', 'wmc_only', 'reduction_rules'])
@pytest.mark.parametrize('strategy', STRATEGIES)
@pytest.mark.parametrize('case', ['identity', 'hh', 'x', 'z', 's', 't', 'sx', 'sxdg', 'cx', 'cz', 'ccx', 'p', 'small_rz', 'minus_i', 'rz_p', 'metadata', 'phase_cancel'])
def test_matrix_oracle(backend, method, strategy, case):
    a, b = circuits(case)
    result = check_equivalence(a, b, backend=backend, method=method, strategy=strategy, timeout=10)
    if method == 'reduction_rules' and result.equivalent == 'unknown': return
    assert result.equivalent == expected(a, b)

@pytest.mark.parametrize('source', [
    'OPENQASM 2.0;\nqreg q[1];\nunsupported q[0];',
    'OPENQASM 2.0;\nqreg q[1];\nrx q[0];',
])
def test_rust_parser_rejects_invalid_gates(source):
    from QuPRS import _pathsum_rust
    with pytest.raises(ValueError):
        _pathsum_rust.check_equivalence(source, source, method='reduction_rules')

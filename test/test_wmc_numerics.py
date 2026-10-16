"""Floating WMC acceptance fixtures, independent of solver implementation."""
import pytest
from qiskit import QuantumCircuit

from QuPRS import check_equivalence, config
from QuPRS.interface.ps2wmc import run_wmc


# Mode 6 prints nine significant digits. This is a fixture comparison budget,
# not an error bound for arbitrary circuits or an equivalence tolerance.
COUNT_REL_TOL = 1e-8
COUNT_ABS_TOL = 1e-12


@pytest.mark.parametrize('positive,negative', [
    (complex(1.23456789123, -2.34567891234), complex(1, 0)),
    (complex(1e-12, -2.5e-11), complex(1, 0)),
    (complex(1.5, .25), complex(-1.5, -.25)),
    (complex(1.5, .25), complex(-1.5 + 1e-8, -.25)),
])
def test_floating_counts_match_hand_computed_models(tmp_path, positive, negative):
    counts = {}
    expected = positive + negative
    for solver in ('ganak', 'gpmc'):
        weights = []
        for literal, z in ((1, positive), (-1, negative)):
            if solver == 'ganak':
                value = f'{z.real:.17g} {"+" if z.imag >= 0 else "-"} {abs(z.imag):.17g}i'
            else:
                value = f'{z.real:.17g} {z.imag:.17g}'
            weights.append(f'c p weight {literal} {value} 0')
        cnf = tmp_path / f'{solver}.cnf'
        cnf.write_text('p cnf 1 0\nc t wmc\n' + '\n'.join(weights) + '\n')
        counts[solver] = complex(*run_wmc(str(cnf), solver))
        assert counts[solver] == pytest.approx(expected, rel=COUNT_REL_TOL, abs=COUNT_ABS_TOL)
    assert counts['ganak'] == pytest.approx(counts['gpmc'], rel=COUNT_REL_TOL, abs=COUNT_ABS_TOL)


@pytest.mark.parametrize('solver', ['ganak', 'gpmc'])
@pytest.mark.parametrize('log_offset,expected', [(0.00049, 'equivalent'), (0.00051, 'not_equivalent')])
def test_python_existing_rounded_log_boundary(monkeypatch, solver, log_offset, expected):
    import QuPRS.interface.ps2wmc as adapter
    # H H leaves two path variables when reduction is disabled: expected log2=2.
    count = 2 ** (2 + log_offset)
    monkeypatch.setattr(adapter, 'run_wmc', lambda *args: (count, 0.0))
    monkeypatch.setattr(config, 'TOLERANCE', 1e-10)
    identity = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    hh.h(0)
    hh.h(0)
    result = check_equivalence(identity, hh, method='wmc_only', tool_name=solver, backend='python')
    assert result.equivalent == expected


@pytest.mark.parametrize('solver', ['ganak', 'gpmc'])
@pytest.mark.parametrize('backend,angle,accepted', [
    ('python', 0.0, True), ('python', 0.05, True), ('python', 0.06, False),
    ('rust', 0.0, True), ('rust', 0.0026, True), ('rust', 0.003, False),
])
def test_real_solvers_near_existing_decision_boundaries(backend, solver, angle, accepted):
    # |tr(RZ(angle))|/2 = cos(angle/2). Exercise the existing Python rounded-log
    # boundary (~0.0005) and Rust normalized-magnitude boundary (1e-6).
    identity = QuantumCircuit(1)
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.rz(angle, 0)
    circuit.h(0)
    result = check_equivalence(identity, circuit, method='wmc_only', tool_name=solver, backend=backend)
    if accepted:
        assert result.equivalent in {'equivalent', 'equivalent*'}
    else:
        assert result.equivalent == 'not_equivalent'


@pytest.mark.parametrize('solver', ['ganak', 'gpmc'])
def test_large_normalization_identity_with_real_solver(solver):
    identity = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    for _ in range(60):
        hh.h(0)
    # Expected count 2**31 needs more significant digits than mode 6 prints.
    result = check_equivalence(identity, hh, method='wmc_only', tool_name=solver, backend='python')
    assert result.equivalent == 'equivalent'

"""Distribution and exact-count regression gates for the selected solver."""
from pathlib import Path
import pytest

from QuPRS.utils import WMC
from QuPRS.interface.ps2wmc import run_wmc


def test_explicit_ganak_override_is_preserved(monkeypatch, tmp_path):
    binary = tmp_path / 'ganak'
    binary.write_bytes(b'explicit-user-executable')
    monkeypatch.setenv('QUPRS_GANAK_PATH', str(binary))
    with WMC('ganak') as selected:
        assert Path(selected) == binary


@pytest.mark.parametrize('real,imag,negative,expected', [
    ('1.5', '0.25', '1 + 0i', (1.5, .25)),
    ('-1.5', '-0.25', '1 + 0i', (-1.5, -.25)),
    ('0', '1', '1 + 0i', (0, 1)),
    ('0', '0', '1 + 0i', (0, 0)),
    ('1e-5', '-2.5e-6', '1 + 0i', (1e-5, -2.5e-6)),
])
def test_ganak_exact_unit_weight(tmp_path, real, imag, negative, expected):
    cnf = tmp_path / 'unit.cnf'
    cnf.write_text(f'p cnf 1 1\nc t wmc\nc p weight 1 {real} + {imag}i 0\nc p weight -1 {negative} 0\n1 0\n')
    assert run_wmc(str(cnf), 'ganak') == expected


def test_ganak_exact_cancellation(tmp_path):
    cnf = tmp_path / 'cancel.cnf'
    cnf.write_text('p cnf 1 0\nc t wmc\nc p weight 1 1.5 + 0.25i 0\nc p weight -1 -1.5 - 0.25i 0\n')
    assert run_wmc(str(cnf), 'ganak') == (0, 0)

@pytest.mark.parametrize('payload', [b'old cached binary', b'\x7fELF\x02\x01' + b'\0' * 80])
def test_unverified_binary_rejected(tmp_path, payload):
    from QuPRS.utils.ganak_distribution import binary_diagnostics
    binary = tmp_path / 'ganak'
    binary.write_bytes(payload)
    with pytest.raises(RuntimeError):
        binary_diagnostics(binary)


def test_packaged_binary_provenance(monkeypatch):
    from QuPRS.utils.ganak_distribution import binary_diagnostics
    monkeypatch.delenv('QUPRS_GANAK_PATH', raising=False)
    with WMC('ganak') as binary:
        info = binary_diagnostics(binary)
    assert info['pinned'] is True
    assert info['requested_version'] == '2.8.0'
    assert 'b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281' in info['embedded_version']


@pytest.mark.parametrize('stdout,status', [
    ('c s exact arb frac 999', 7), ('c s exact quadruple float 999', -11), ('no count', 0),
    ('c s exact arb frac malformed', 0), ('c s exact arb frac 1/0', 0),
    ('c s exact arb frac NaN', 0), ('c s exact unsupported 0', 0),
])
@pytest.mark.parametrize('solver', ['ganak', 'gpmc'])
def test_solver_failure_is_not_a_count(monkeypatch, stdout, status, solver):
    from contextlib import contextmanager
    from types import SimpleNamespace
    import QuPRS.interface.ps2wmc as module
    import QuPRS.utils.ganak_distribution as distribution
    @contextmanager
    def executable(name):
        assert name == solver
        yield '/test/selected-solver'
    monkeypatch.setattr(module, 'WMC', executable)
    monkeypatch.setattr(distribution, 'binary_diagnostics', lambda *args: {})
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: SimpleNamespace(
        stdout=stdout, stderr='diagnostic', returncode=status))
    with pytest.raises((ValueError, RuntimeError, ArithmeticError)):
        run_wmc('fixture.cnf', solver)

def test_rust_dispatch_does_not_leave_an_implicit_override(monkeypatch):
    import os
    from qiskit import QuantumCircuit
    from QuPRS import check_equivalence
    monkeypatch.delenv('QUPRS_GANAK_PATH', raising=False)
    circuit = QuantumCircuit(1)
    check_equivalence(circuit, circuit, backend='rust', method='reduction_rules', tool_name='ganak')
    assert 'QUPRS_GANAK_PATH' not in os.environ

@pytest.mark.parametrize('clauses,expected', [('', (2, 0)), ('1 0\n-1 0\n', (0, 0))])
def test_ganak_unweighted_sat_and_unsat(tmp_path, clauses, expected):
    cnf = tmp_path / 'sat.cnf'
    cnf.write_text(f'p cnf 1 {len(clauses.splitlines())}\nc t wmc\n{clauses}')
    assert run_wmc(str(cnf), 'ganak') == expected


def test_ganak_conjugate_weights(tmp_path):
    cnf = tmp_path / 'conjugate.cnf'
    cnf.write_text('p cnf 1 0\nc t wmc\nc p weight 1 1.5 + 0.25i 0\nc p weight -1 1.5 - 0.25i 0\n')
    assert run_wmc(str(cnf), 'ganak') == (3, 0)

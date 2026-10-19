"""Solver format regressions; no cross-solver fallback is permitted."""
from contextlib import contextmanager
from types import SimpleNamespace
import pytest
from QuPRS.utils.wmc_solvers import parse_count_line, SOLVER_ARGUMENTS
from QuPRS.interface.ps2wmc import run_wmc

@pytest.mark.parametrize('line, expected', [
    ('c s exact arb frac 3/2 + 1/4i', complex(1.5, .25)),
    ('c s exact arb frac -3/2 - 1/4i', complex(-1.5, -.25)),
    ('c s exact double prec-sci 1.25e-10 - 2.5e-11i', complex(1.25e-10, -2.5e-11)),
    ('c s exact arb frac 1/2', complex(.5, 0)),
])
def test_count_formats(line, expected):
    assert parse_count_line(line) == expected

def test_solver_modes_are_independent():
    assert SOLVER_ARGUMENTS['ganak'] == ('--mode=6',)
    assert SOLVER_ARGUMENTS['gpmc'] == ('-mode=1',)

@pytest.mark.parametrize('value, expected', [
    ('9.28154511e-01 + 2.42960040e+10i', complex(.928154511, 2.42960040e10)),
    ('-1.25E+03 - 2.5E-11i', complex(-1250, -2.5e-11)),
    ('1e-12 + -2e+03i', complex(1e-12, -2000)),
    ('+i', 1j), ('-i', -1j), ('0', 0),
    ('1\t+\t2i', complex(1, 2)),
])
def test_mode6_complex_scientific_output(value, expected):
    assert parse_count_line('c s exact quadruple float ' + value) == expected

def test_result_prefix_requires_a_token_boundary():
    assert parse_count_line('c s exact quadruple floating 1') is None

@pytest.mark.parametrize('value', ['nan', 'inf', '1e999', '1 + infi', '1e-2-3e+i'])
def test_mode6_rejects_invalid_or_nonfinite_counts(value):
    with pytest.raises((ValueError, ArithmeticError)):
        parse_count_line('c s exact quadruple float ' + value)

def test_fraction_exceeding_python_integer_digit_limit():
    digits = '1' + '0' * 5000
    assert parse_count_line(f'c s exact arb frac {digits}/{digits}') == 1

@pytest.mark.parametrize('line', ['c s exact arb frac 1/0', 'c s exact arb frac malformed'])
def test_invalid_count_is_not_silently_zero(line):
    with pytest.raises((ValueError, ArithmeticError)):
        parse_count_line(line)

@pytest.mark.parametrize('solver', ['ganak', 'gpmc'])
def test_solver_runs_independently(monkeypatch, solver):
    import QuPRS.interface.ps2wmc as module
    import QuPRS.utils.ganak_distribution as distribution
    monkeypatch.setattr(distribution, "binary_diagnostics", lambda *args: {})
    calls = []
    @contextmanager
    def executable(name):
        assert name == solver
        yield '/solvers/' + solver
    def run(command, **kwargs):
        assert kwargs['timeout'] == 600.0
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout='c s exact arb frac 3/2 + 1/4i', stderr='')
    monkeypatch.setattr(module, 'WMC', executable)
    import QuPRS.utils.solver_process as process
    monkeypatch.setattr(process, 'run', run)
    assert run_wmc('test.cnf', solver) == (1.5, .25)
    assert calls == [['/solvers/' + solver, *SOLVER_ARGUMENTS[solver], 'test.cnf']]

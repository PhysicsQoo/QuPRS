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

def test_fraction_exceeding_python_integer_digit_limit():
    digits = '1' + '0' * 5000
    assert parse_count_line(f'c s exact arb frac {digits}/{digits}') == 1

@pytest.mark.parametrize('line', ['c s exact arb frac 1/0', 'c s exact arb frac malformed'])
def test_invalid_count_is_not_silently_zero(line):
    with pytest.raises((ValueError, ArithmeticError)):
        parse_count_line(line)

def test_ganak_runs_independently(monkeypatch):
    import QuPRS.interface.ps2wmc as module
    import QuPRS.utils.ganak_distribution as distribution
    monkeypatch.setattr(distribution, "binary_diagnostics", lambda *args: {})
    calls = []
    @contextmanager
    def executable(name):
        assert name == 'ganak'
        yield '/solvers/ganak'
    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout='c s exact arb frac 3/2 + 1/4i', stderr='')
    monkeypatch.setattr(module, 'WMC', executable)
    monkeypatch.setattr(module.subprocess, 'run', run)
    assert run_wmc('test.cnf', 'ganak') == (1.5, .25)
    assert calls == [['/solvers/ganak', *SOLVER_ARGUMENTS['ganak'], 'test.cnf']]

def test_benchmark_does_not_skip_a_ganak_crash(monkeypatch):
    import test_MQT as benchmark_module
    def crash(*args, **kwargs):
        raise RuntimeError('solver exited with signal')
    monkeypatch.setattr(benchmark_module, 'check_equivalence', crash)
    with pytest.raises(RuntimeError, match='signal'):
        benchmark_module.generate_test('fixture.qasm', tool_name='ganak')

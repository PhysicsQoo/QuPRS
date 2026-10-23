"""GPMC/Ganak selection, typed failures, and optional third solver."""
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from QuPRS.interface.ps2wmc import run_wmc, wlogi_to_clauses
from QuPRS.utils.solver_adapter import (
    SolverAdapter, SolverCapabilities, SolverExecutionError, SolverResultError,
    execute_solver, get_solver_adapter, registered_solver_adapter,
)


def test_independent_solver_contracts():
    a, b = get_solver_adapter("gpmc"), get_solver_adapter("ganak")
    assert a.arguments == ("-mode=1",)
    assert b.arguments == ("--mode=6",)
    assert a.format_weights(1, -2) == ("1 -2 0", "1.0 0.0 0")
    assert b.format_weights(1, -2) == ("1 - 2i 0", "1.0 + 0.0i 0")
    assert not a.capabilities.exact_count_certificate
    assert not b.capabilities.exact_count_certificate


def test_unsupported_solver_fails_closed():
    with pytest.raises(ValueError, match="Unsupported solver"):
        wlogi_to_clauses([], {}, tool_name="third")
    with pytest.raises(ValueError, match="Unsupported solver"):
        run_wmc("unused.cnf", "third")


@pytest.mark.parametrize("solver", ["ganak", "gpmc"])
@pytest.mark.parametrize("fault, expected", [
    ("success", None), ("nonzero", SolverExecutionError),
    ("malformed", SolverResultError), ("timeout", TimeoutError),
])
def test_selected_solver_only(monkeypatch, solver, fault, expected):
    import QuPRS.interface.ps2wmc as impl
    import QuPRS.utils.solver_process as process
    import QuPRS.utils.ganak_distribution as dist

    @contextmanager
    def resource(name):
        assert name == solver
        yield "/fixtures/" + name

    calls = []

    def runner(command, *, timeout):
        from QuPRS.utils.solver_process import SolverTimeout
        assert timeout > 0
        calls.append(command)
        if fault == "timeout":
            raise SolverTimeout("fixture timeout")
        if fault == "nonzero":
            return SimpleNamespace(returncode=7, stdout="c s exact arb frac 3/2", stderr="failure")
        if fault == "malformed":
            return SimpleNamespace(returncode=0, stdout="no weighted count", stderr="")
        return SimpleNamespace(returncode=0, stdout="c s exact arb frac 3/2 + 1/4i", stderr="")

    monkeypatch.setattr(impl, "WMC", resource)
    monkeypatch.setattr(process, "run", runner)
    monkeypatch.setattr(dist, "binary_diagnostics", lambda *args, **kwargs: {})
    if expected:
        with pytest.raises(expected):
            run_wmc("input.cnf", solver, timeout=5)
    else:
        assert run_wmc("input.cnf", solver, timeout=5) == (1.5, .25)
    assert calls == [["/fixtures/" + solver, *get_solver_adapter(solver).arguments, "input.cnf"]]


class ThirdAdapter(SolverAdapter):
    def format_weights(self, real, imag):
        return f"{real} {imag} 0", "1.0 0.0 0"
    def parse_output(self, stdout):
        if stdout.strip() != "fixture:7":
            raise SolverResultError("invalid mock count")
        return 7 + 0j


def test_third_adapter_can_extend_without_core_changes(monkeypatch):
    import QuPRS.utils.solver_process as process
    @contextmanager
    def resource():
        yield "/fixtures/mock"
    adapter = ThirdAdapter(
        "mock", ("--test",), SolverCapabilities("fixture"), resource,
    )
    seen = []
    def runner(command, *, timeout):
        seen.append(command)
        return SimpleNamespace(returncode=0, stdout="fixture:7", stderr="")
    monkeypatch.setattr(process, "run", runner)
    with registered_solver_adapter(adapter):
        assert wlogi_to_clauses([], {}, tool_name="mock")[0] == []
        assert run_wmc("input.cnf", "mock") == (7.0, 0.0)
        with pytest.raises(ValueError, match="already registered"):
            with registered_solver_adapter(adapter):
                pass
    assert seen == [["/fixtures/mock", "--test", "input.cnf"]]
    with pytest.raises(ValueError, match="Unsupported solver"):
        get_solver_adapter("mock")

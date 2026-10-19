"""Independent Python solver lifecycle regressions using harmless fake processes."""
from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from QuPRS.utils.solver_process import (
    SolverOutputLimitError,
    SolverProcessError,
    SolverTimeout,
    run,
)


def command(code):
    return [sys.executable, "-c", code]


def test_python_solver_success_drains_both_streams():
    result = run(
        command("import sys; print('c s exact arb frac 1/2'); "
                "print('diagnostic', file=sys.stderr)"),
        timeout=3,
    )
    assert result.returncode == 0
    assert "exact arb frac" in result.stdout
    assert "diagnostic" in result.stderr


def test_python_solver_timeout_kills_child():
    start = time.monotonic()
    with pytest.raises(SolverTimeout):
        run(command("import time; time.sleep(30)"), timeout=0.15)
    assert time.monotonic() - start < 3


def test_python_solver_oversized_stdout_is_rejected():
    start = time.monotonic()
    with pytest.raises(SolverOutputLimitError):
        run(command("import sys; "
                    "sys.stdout.write('X'*2000000); sys.stdout.flush(); "
                    "import time; time.sleep(30)"), timeout=3)
    assert time.monotonic() - start < 3


def test_python_solver_missing_binary_is_an_error():
    with pytest.raises(SolverProcessError, match="SolverUnavailable"):
        run(["quprs-this-executable-must-not-exist-59919"], timeout=1)


@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
def test_python_nonzero_with_valid_looking_count_is_not_equivalence(monkeypatch, solver):
    import QuPRS.interface.ps2wmc as wmc
    import QuPRS.utils.solver_process as process
    import QuPRS.utils.ganak_distribution as distribution

    @contextmanager
    def resource(name):
        assert name == solver
        yield "/fake/" + name

    calls = []
    def fake_run(command, timeout):
        calls.append((command, timeout))
        return SimpleNamespace(
            returncode=7, stdout="c s exact arb frac 1/1", stderr="fail"
        )

    monkeypatch.setattr(wmc, "WMC", resource)
    monkeypatch.setattr(process, "run", fake_run)
    monkeypatch.setattr(distribution, "binary_diagnostics", lambda *a: {})
    with pytest.raises(RuntimeError, match="status=7"):
        wmc.run_wmc("test.cnf", solver, timeout=1)
    assert len(calls) == 1
    assert solver in calls[0][0][0]
    assert 0 < calls[0][1] <= 1


@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
def test_python_malformed_output_is_not_a_count(monkeypatch, solver):
    import QuPRS.interface.ps2wmc as wmc
    import QuPRS.utils.solver_process as process
    import QuPRS.utils.ganak_distribution as distribution

    @contextmanager
    def resource(name):
        yield "/fake/" + name

    monkeypatch.setattr(wmc, "WMC", resource)
    monkeypatch.setattr(distribution, "binary_diagnostics", lambda *a: {})
    monkeypatch.setattr(
        process, "run",
        lambda *_a, **_kw: SimpleNamespace(returncode=0, stdout="no count", stderr=""),
    )
    with pytest.raises(ValueError, match="output format error"):
        wmc.run_wmc("test.cnf", solver, timeout=1)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux /proc needed for descendant liveness")
def test_python_timeout_stops_process_descendants(tmp_path):
    marker = tmp_path / "descendant.pid"
    script = (
        "import subprocess, sys, time; "
        "p=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
        f"open({str(marker)!r}, 'w').write(str(p.pid)); "
        "time.sleep(30)"
    )
    with pytest.raises(SolverTimeout):
        run(command(script), timeout=0.5)
    pid = int(marker.read_text())
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        stat = f"/proc/{pid}/stat"
        if not os.path.exists(stat) or open(stat).read().split()[2] == "Z":
            break
        time.sleep(0.02)
    else:
        pytest.fail("solver grandchild remained alive after timeout")


def test_python_cnf_removed_even_when_solver_times_out(tmp_path, monkeypatch):
    from qiskit import QuantumCircuit
    import tempfile
    import QuPRS.interface.ps2wmc as wmc
    from QuPRS import check_equivalence

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    def timeout(*args, **kwargs):
        raise SolverTimeout("SolverTimeout: fake hung WMC")
    monkeypatch.setattr(wmc, "run_wmc", timeout)
    result = check_equivalence(
        QuantumCircuit(1), QuantumCircuit(1),
        method="wmc_only", backend="python", timeout=4,
    )
    assert result.equivalent == "Timeout"
    assert not list(tmp_path.glob("*.cnf"))

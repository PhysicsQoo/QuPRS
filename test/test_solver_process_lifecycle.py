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


def _assert_no_live_posix_pids(pids):
    """A zombie has stopped executing; its final reap belongs to its adopter."""
    import subprocess

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        living = []
        for pid in pids:
            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "stat="],
                capture_output=True, text=True, check=False, timeout=3,
            )
            state = result.stdout.strip()
            if result.returncode == 0 and state and not state.startswith("Z"):
                living.append((pid, state))
        if not living:
            return
        time.sleep(0.04)
    pytest.fail(f"live subprocess descendants left behind: {living}")


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group lifecycle contract")
@pytest.mark.parametrize("exit_kind", ["timeout", "success"])
def test_python_solver_process_tree_has_no_live_descendants(tmp_path, exit_kind):
    """Check actual solver and grandchild PIDs on both Linux and macOS."""
    marker = tmp_path / f"{exit_kind}.pids"
    script = (
        "import os, pathlib, subprocess, sys, time; "
        "p=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
        f"pathlib.Path({str(marker)!r}).write_text(str(os.getpid())+' '+str(p.pid)); "
        + ("time.sleep(30)" if exit_kind == "timeout" else "print('ready', flush=True)")
    )
    if exit_kind == "timeout":
        with pytest.raises(SolverTimeout):
            run(command(script), timeout=2)
    else:
        result = run(command(script), timeout=5)
        assert result.returncode == 0
        assert "ready" in result.stdout

    assert marker.exists(), "fake solver must record its live descendant before exit"
    pids = [int(value) for value in marker.read_text().split()]
    assert len(pids) == 2
    _assert_no_live_posix_pids(pids)


@pytest.mark.parametrize(
    ("outcome", "expected_exception"),
    [
        ("nonzero", RuntimeError),
        ("malformed", ValueError),
        ("output_limit", SolverOutputLimitError),
        ("timeout", None),
    ],
)
def test_python_public_api_keeps_solver_outcomes_distinct(
    monkeypatch, tmp_path, outcome, expected_exception,
):
    """A broken solver is never allowed to mean circuit inequivalence."""
    from qiskit import QuantumCircuit
    from QuPRS import check_equivalence
    import QuPRS.interface.ps2wmc as wmc

    def simulated_solver(*_args, **_kwargs):
        if outcome == "timeout":
            raise SolverTimeout("SolverTimeout: fake deadline")
        if outcome == "output_limit":
            raise SolverOutputLimitError("SolverOutputLimit: fake overflow")
        if outcome == "nonzero":
            raise RuntimeError("GPMC failed: status=7, valid-looking count rejected")
        raise ValueError("WMC output format error")

    monkeypatch.setattr(wmc, "run_wmc", simulated_solver)
    # H followed by H has a nontrivial WMC encoding but is mathematically the
    # identity. Do not reinterpret a solver failure as NotEquivalent.
    identity = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    hh.h(0)
    hh.h(0)
    if expected_exception is None:
        result = check_equivalence(
            identity, hh, method="wmc_only", backend="python", timeout=5
        )
        assert result.equivalent == "Timeout"
    else:
        with pytest.raises(expected_exception):
            check_equivalence(
                identity, hh, method="wmc_only", backend="python", timeout=5
            )



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


@pytest.mark.skipif(os.name != "posix", reason="Fake POSIX solver script")
@pytest.mark.parametrize("failure", ["timeout", "nonzero"])
def test_rust_public_api_keeps_solver_failure_distinct(monkeypatch, tmp_path, failure):
    """Exercise the actual Rust FFI and status mapping, not just WmcManager."""
    from qiskit import QuantumCircuit
    from QuPRS import check_equivalence
    import QuPRS.utils as resources

    fake = tmp_path / "fake-gpmc"
    if failure == "timeout":
        fake.write_text("#!/bin/sh\nsleep 30\n")
    else:
        fake.write_text("#!/bin/sh\necho 'c s exact quadruple float 999'\nexit 7\n")
    fake.chmod(0o700)

    @contextmanager
    def fake_resource(tool_name):
        assert tool_name == "gpmc"
        yield fake

    monkeypatch.setattr(resources, "WMC", fake_resource)
    identity = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    hh.h(0)
    hh.h(0)
    if failure == "timeout":
        result = check_equivalence(
            identity, hh, backend="rust", method="wmc_only",
            tool_name="gpmc", timeout=2,
        )
        assert result.equivalent == "Timeout", result.equivalent
    else:
        with pytest.raises(ValueError, match="Verification Engine Failed"):
            check_equivalence(
                identity, hh, backend="rust", method="wmc_only",
                tool_name="gpmc", timeout=2,
            )


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_reduction_incomplete_is_unknown_not_solver_failure(backend):
    from qiskit import QuantumCircuit
    from QuPRS import check_equivalence

    identity = QuantumCircuit(1)
    hadamard = QuantumCircuit(1)
    hadamard.h(0)
    result = check_equivalence(
        identity, hadamard, backend=backend,
        method="reduction_rules", timeout=15,
    )
    assert result.equivalent == "unknown", (
        f"backend={backend}, returned {result.equivalent} "
        "for intentionally incomplete reduction"
    )

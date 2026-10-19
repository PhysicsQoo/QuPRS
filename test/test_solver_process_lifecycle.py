"""Independent Python solver lifecycle regressions using harmless fake processes."""
from __future__ import annotations

import os
import signal
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


def _pid_execution_state(pid):
    """Return a process state without depending on procps inside Docker.

    Linux /proc is available in the project's slim test container. On macOS,
    /proc is absent and the native ps command provides the state instead.
    Return None only when the process no longer exists.
    """
    if sys.platform.startswith("linux"):
        from pathlib import Path

        stat_path = Path("/proc") / str(pid) / "stat"
        try:
            stat_line = stat_path.read_text()
        except FileNotFoundError:
            return None
        # /proc/PID/stat encloses the command name in parentheses; split at
        # the last ')' to avoid interpreting spaces in a process name.
        return stat_line.rsplit(")", 1)[-1].strip().split()[0]

    import subprocess

    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "stat="],
        capture_output=True, text=True, check=False, timeout=3,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _assert_no_live_posix_pids(pids):
    """A zombie has stopped executing; its final reap belongs to its adopter."""
    deadline = time.monotonic() + 3
    while True:
        living = [
            (pid, state)
            for pid in pids
            if (state := _pid_execution_state(pid)) is not None
            and not state.startswith(("Z", "X"))
        ]
        if not living:
            return
        if time.monotonic() >= deadline:
            pytest.fail(f"live subprocess descendants left behind: {living}")
        time.sleep(0.04)


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


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_proven_inequivalence_is_not_unknown_timeout_or_solver_error(backend):
    """A reversible X on |0> changes the operator; reduction is decisive."""
    from qiskit import QuantumCircuit
    from QuPRS import check_equivalence

    identity = QuantumCircuit(1)
    not_identity = QuantumCircuit(1)
    not_identity.x(0)
    result = check_equivalence(
        identity, not_identity, backend=backend,
        method="reduction_rules", timeout=15,
    )
    assert result.equivalent == "not_equivalent", (
        f"backend={backend} misclassified an analytically nonidentity circuit"
    )


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_public_api_rejects_zero_timeout_before_spawning_solver(backend):
    from qiskit import QuantumCircuit
    from QuPRS import check_equivalence

    circuit = QuantumCircuit(1)
    with pytest.raises(ValueError, match="timeout must be a positive"):
        check_equivalence(
            circuit, circuit, backend=backend,
            method="wmc_only", timeout=0,
        )


def test_parallel_rust_solver_resource_override_is_serialized(monkeypatch, tmp_path):
    """A Rust invocation cannot observe a different concurrent solver path."""
    from concurrent.futures import ThreadPoolExecutor
    from contextlib import contextmanager
    import threading
    import time

    from qiskit import QuantumCircuit
    from QuPRS import check_equivalence, _pathsum_rust
    import QuPRS.utils as resources

    key = "QUPRS_GPMC_PATH"
    previous = os.environ.get(key)
    barrier = threading.Barrier(2)
    active = [0]
    observed = []
    counter_lock = threading.Lock()

    @contextmanager
    def resource(tool_name):
        assert tool_name == "gpmc"
        yield tmp_path / ("solver-" + threading.current_thread().name)

    def fake_rust(*args, **kwargs):
        with counter_lock:
            active[0] += 1
            observed.append((threading.current_thread().name, os.environ.get(key)))
            assert active[0] == 1, "parallel Rust invocations raced on os.environ"
        time.sleep(0.04)
        with counter_lock:
            active[0] -= 1
        return {"status": "Unknown"}

    monkeypatch.setattr(resources, "WMC", resource)
    monkeypatch.setattr(_pathsum_rust, "check_equivalence", fake_rust)

    def check():
        barrier.wait(timeout=5)
        q = QuantumCircuit(1)
        return check_equivalence(
            q, q, method="reduction_rules", backend="rust", timeout=5
        ).equivalent

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: check(), range(2))) == ["unknown", "unknown"]
    assert len(observed) == 2
    for name, path in observed:
        assert path is not None and path.endswith("solver-" + name)
    assert os.environ.get(key) == previous



@pytest.mark.skipif(
    not (hasattr(signal, "setitimer") and hasattr(signal, "SIGALRM")),
    reason="POSIX SIGALRM only",
)
@pytest.mark.parametrize("failure", [False, True])
def test_existing_host_sigalrm_timer_is_never_replaced(monkeypatch, failure):
    """Nested/library use must not reset an already scheduled host alarm."""
    from qiskit import QuantumCircuit
    from QuPRS import check_equivalence

    import QuPRS.interface.ps2wmc as wmc
    original_handler = signal.getsignal(signal.SIGALRM)
    original_timer = signal.getitimer(signal.ITIMER_REAL)
    started = time.monotonic()

    def host_handler(_signum, _frame):
        raise RuntimeError("host SIGALRM fired")

    def fail_solver(*_args, **_kwargs):
        raise RuntimeError("intentional solver failure")

    if failure:
        monkeypatch.setattr(wmc, "run_wmc", fail_solver)
    signal.signal(signal.SIGALRM, host_handler)
    signal.setitimer(signal.ITIMER_REAL, 30)
    try:
        circuit = QuantumCircuit(1)
        if failure:
            with pytest.raises(RuntimeError, match="intentional solver failure"):
                check_equivalence(circuit, circuit, method="wmc_only", timeout=5)
        else:
            result = check_equivalence(
                circuit, circuit, method="reduction_rules", timeout=5
            )
            assert result.equivalent == "equivalent"
        assert signal.getsignal(signal.SIGALRM) is host_handler
        remaining, interval = signal.getitimer(signal.ITIMER_REAL)
        assert interval == 0
        assert 0 < remaining <= 30
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, original_handler)
        if original_timer[0] > 0:
            elapsed = time.monotonic() - started
            signal.setitimer(
                signal.ITIMER_REAL, max(0.001, original_timer[0] - elapsed),
                original_timer[1],
            )


def test_rust_backend_lock_wait_uses_request_timeout(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from qiskit import QuantumCircuit
    from QuPRS import check_equivalence, _pathsum_rust
    from QuPRS.utils.solver_process import SOLVER_ENV_LOCK

    spawned = []
    monkeypatch.setattr(
        _pathsum_rust, "check_equivalence",
        lambda *_a, **_k: spawned.append(True) or {"status": "Unknown"},
    )

    def queued():
        circuit = QuantumCircuit(1)
        return check_equivalence(
            circuit, circuit, backend="rust", method="reduction_rules", timeout=1
        )

    with SOLVER_ENV_LOCK:
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(queued).result(timeout=4)
    assert result.equivalent == "Timeout"
    assert not spawned, "timed-out queued request must not reach Rust FFI"


def test_python_wmc_lock_wait_expires_without_spawning(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import QuPRS.interface.ps2wmc as wmc
    from QuPRS.utils.solver_process import SOLVER_ENV_LOCK, SolverTimeout

    def should_not_resolve(_name):
        raise AssertionError("expired request must not resolve a solver executable")

    monkeypatch.setattr(wmc, "WMC", should_not_resolve)
    with SOLVER_ENV_LOCK:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(wmc.run_wmc, "dummy.cnf", "gpmc", 0.15)
            with pytest.raises(SolverTimeout, match="solver lock"):
                future.result(timeout=4)


@pytest.mark.skipif(
    not (hasattr(signal, "setitimer") and hasattr(signal, "pause")),
    reason="Real host SIGALRM expiry is POSIX only",
)
def test_real_external_alarm_timeout_error_propagates(monkeypatch):
    """A host-owned, actually expiring SIGALRM is not a QuPRS result."""
    from qiskit import QuantumCircuit
    from QuPRS import check_equivalence
    from QuPRS.utils.strategy import Strategy

    prior_handler = signal.getsignal(signal.SIGALRM)
    prior_timer = signal.getitimer(signal.ITIMER_REAL)
    started = time.monotonic()
    triggered = []
    entered = []

    def host_handler(_signum, _frame):
        triggered.append(True)
        raise TimeoutError("host-owned alarm expired")

    class StrategyWaitingForHostAlarm:
        count = 0

        def run(self, _pathsum, _gates1, _gates2):
            entered.append(True)
            assert signal.getsignal(signal.SIGALRM) is host_handler
            assert signal.getitimer(signal.ITIMER_REAL)[0] > 0
            # Rearm the EXISTING host timer while inside the strategy so
            # the signal expires in the exception handler under review.
            signal.setitimer(signal.ITIMER_REAL, 0.08)
            signal.pause()
            pytest.fail("host SIGALRM did not interrupt the strategy")

    fake_strategy = StrategyWaitingForHostAlarm()
    monkeypatch.setattr(
        Strategy, "get", classmethod(lambda _cls, _name: fake_strategy)
    )

    signal.signal(signal.SIGALRM, host_handler)
    signal.setitimer(signal.ITIMER_REAL, 30.0)
    try:
        circuit = QuantumCircuit(1)
        with pytest.raises(TimeoutError, match="host-owned alarm expired"):
            check_equivalence(
                circuit, circuit, method="reduction_rules",
                backend="python", timeout=5,
            )
        assert entered == [True]
        assert triggered == [True], "host alarm must actually fire"
        assert signal.getsignal(signal.SIGALRM) is host_handler
        assert signal.getitimer(signal.ITIMER_REAL)[0] == 0
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prior_handler)
        if prior_timer[0] > 0:
            elapsed = time.monotonic() - started
            signal.setitimer(
                signal.ITIMER_REAL,
                max(0.001, prior_timer[0] - elapsed),
                prior_timer[1],
            )


def test_quprs_owned_strategy_timeout_remains_a_timeout_result(monkeypatch):
    from qiskit import QuantumCircuit
    from QuPRS import check_equivalence
    from QuPRS.utils.strategy import Strategy
    from QuPRS.utils.verification_timeout import VerificationTimeout

    class ExpiredStrategy:
        count = 0

        def safe_run(self, *_args, **_kwargs):
            raise VerificationTimeout("Strategy execution timed out.")

    monkeypatch.setattr(
        Strategy, "get", classmethod(lambda _cls, _name: ExpiredStrategy())
    )
    circuit = QuantumCircuit(1)
    result = check_equivalence(
        circuit, circuit, method="reduction_rules",
        backend="python", safe_mode=True, timeout=5,
    )
    assert result.equivalent == "Timeout"


def test_non_quprs_timeout_from_solver_callback_is_not_swallowed(monkeypatch):
    from qiskit import QuantumCircuit
    from QuPRS import check_equivalence
    import QuPRS.interface.ps2wmc as wmc

    def external_failure(*_args, **_kwargs):
        raise TimeoutError("external caller deadline")

    monkeypatch.setattr(wmc, "run_wmc", external_failure)
    circuit = QuantumCircuit(1)
    with pytest.raises(TimeoutError, match="external caller deadline"):
        check_equivalence(
            circuit, circuit, method="wmc_only",
            backend="python", timeout=5,
        )

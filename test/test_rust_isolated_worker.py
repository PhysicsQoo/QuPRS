"""Focused QOO-175 smoke, parity and isolated IPC fault injection.

These tests intentionally do not claim cgroup or detached solver-tree protection.
"""
import os
import signal
import textwrap
from pathlib import Path
import subprocess
import sys
import time

import pytest
from qiskit import QuantumCircuit

from QuPRS import check_equivalence
from QuPRS.interface.rust_isolation import (
    RustWorkerError,
    _WorkerDeadlineExceeded,
    _bounded_exchange,
    _parse_worker_response,
    _stop_worker,
)


pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX worker prototype")


def test_rust_safe_mode_identity_and_x_parity():
    identity = QuantumCircuit(1)
    other = QuantumCircuit(1)
    other.x(0)

    for left, right in ((identity, identity), (identity, other)):
        direct = check_equivalence(
            left, right, backend="rust", method="reduction_rules",
            safe_mode=False, timeout=30,
        )
        isolated = check_equivalence(
            left, right, backend="rust", method="reduction_rules",
            safe_mode=True, timeout=30,
        )
        assert isolated.equivalent == direct.equivalent
        assert isolated.rr_approximate == direct.rr_approximate
        assert isolated.wmc_solver_invoked == direct.wmc_solver_invoked
        assert isolated.Statistics == direct.Statistics
        assert isolated.final_pathsum == direct.final_pathsum


def test_rust_safe_mode_qasm_text_parity():
    qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    direct = check_equivalence(
        qasm, qasm, backend="rust", method="reduction_rules",
        safe_mode=False, timeout=30,
    )
    isolated = check_equivalence(
        qasm, qasm, backend="rust", method="reduction_rules",
        safe_mode=True, timeout=30,
    )
    assert direct.equivalent == isolated.equivalent == "equivalent"


def test_rust_safe_mode_preserves_global_phase_fail_closed():
    a = QuantumCircuit(1)
    b = QuantumCircuit(1)
    b.global_phase = 0.5
    with pytest.raises(ValueError, match="global_phase"):
        check_equivalence(
            a, b, backend="rust", method="reduction_rules",
            safe_mode=True, timeout=30,
        )


def test_rust_safe_mode_external_gpmc_wmc_parity():
    identity = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    altered = identity + "rz(0.001) q[0];\n"
    common = dict(
        backend="rust", method="wmc_only", tool_name="gpmc",
        timeout=60, approximate_distance_tolerance=1e-8,
    )
    direct = check_equivalence(identity, altered, safe_mode=False, **common)
    isolated = check_equivalence(identity, altered, safe_mode=True, **common)
    assert direct.equivalent == isolated.equivalent == "not_equivalent"
    assert direct.wmc_solver_invoked is True
    assert isolated.wmc_solver_invoked is True
    assert direct.wmc_printed_verdict == isolated.wmc_printed_verdict
    assert direct.wmc_numerical_verdict == isolated.wmc_numerical_verdict
    assert direct.wmc_precision_reason == isolated.wmc_precision_reason


def test_rust_safe_mode_up_to_global_phase_parity():
    identity = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    phased = identity + "s q[0];\nx q[0];\ns q[0];\nx q[0];\n"
    common = dict(backend="rust", method="hybrid", tool_name="gpmc", timeout=60)
    direct = check_equivalence(identity, phased, safe_mode=False, **common)
    isolated = check_equivalence(identity, phased, safe_mode=True, **common)
    assert isolated.equivalent == direct.equivalent == "equivalent*"
    assert isolated.wmc_solver_invoked == direct.wmc_solver_invoked
    assert isolated.rr_approximate == direct.rr_approximate


def _spawn_script(code):
    return subprocess.Popen(
        [sys.executable, "-c", code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        close_fds=True,
        bufsize=0,
    )


def test_bounded_worker_deadline_kills_hung_process():
    process = _spawn_script("import time; time.sleep(30)")
    try:
        with pytest.raises(_WorkerDeadlineExceeded):
            _bounded_exchange(process, b'{"version":1}', time.monotonic() + 0.2)
    finally:
        _stop_worker(process)
    assert process.poll() is not None


def test_bounded_worker_rejects_oversized_diagnostics():
    process = _spawn_script(
        "import sys; sys.stdin.buffer.read(); "
        "sys.stderr.buffer.write(b'x' * (1024 * 1024 + 1)); "
        "sys.stderr.buffer.flush()"
    )
    try:
        with pytest.raises(RustWorkerError, match="stderr exceeded IPC output limit"):
            _bounded_exchange(process, b'{"version":1}', time.monotonic() + 10)
    finally:
        _stop_worker(process)
    assert process.poll() is not None


def test_bounded_worker_rejects_incomplete_output():
    process = _spawn_script("import sys; sys.stdin.buffer.read(); sys.stdout.write('{')")
    try:
        stdout, stderr = _bounded_exchange(
            process, b'{"version":1}', time.monotonic() + 10,
        )
        assert stdout == b"{"
        assert stderr == b""
        assert process.returncode == 0
    finally:
        _stop_worker(process)
    with pytest.raises(RustWorkerError, match="invalid isolated Rust result envelope"):
        _parse_worker_response(stdout, stderr, 0)


def test_interrupt_cleanup_uses_private_process_group():
    process = _spawn_script("import time; time.sleep(30)")
    try:
        assert process.poll() is None
    finally:
        _stop_worker(process)
    assert process.poll() is not None


def test_bounded_worker_remote_error_never_becomes_science_verdict():
    response = (
        b'{"version":1,"ok":false,"error_type":"ValueError",'
        b'"message":"invalid solver request"}'
    )
    with pytest.raises(ValueError, match="invalid solver request"):
        _parse_worker_response(response, b"", 0)
    with pytest.raises(RustWorkerError, match="protocol version mismatch"):
        _parse_worker_response(b'{"version":42,"ok":true,"result":{}}', b"", 0)


def test_complete_worker_reply_must_have_valid_science_status_and_fields():
    bad_status = b'{"version":1,"ok":true,"result":{"status":"Fabricated"}}'
    with pytest.raises(RustWorkerError, match="invalid status"):
        _parse_worker_response(bad_status, b"", 0)
    missing_fields = b'{"version":1,"ok":true,"result":{"status":"Equivalent"}}'
    with pytest.raises(RustWorkerError, match="missing required fields"):
        _parse_worker_response(missing_fields, b"", 0)
    with pytest.raises(RustWorkerError, match="exited with 137"):
        _parse_worker_response(b"", b"OOM killed", 137)

@pytest.mark.skipif(sys.platform != "linux", reason="Linux-only child-subreaper contract")
def test_private_supervisor_reaps_detached_solver_descendants(tmp_path):
    from QuPRS.interface import rust_isolation

    supervisor = Path(rust_isolation.__file__).with_name("rust_supervisor.py")
    marker = tmp_path / "detached.pid"
    witness = textwrap.dedent("""
        import importlib.util, os, signal, subprocess, sys, time
        spec = importlib.util.spec_from_file_location("private_supervisor", sys.argv[1])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module._set_supervisor_controls()
        child = (
            "import subprocess, sys, time;"
            "p = subprocess.Popen([sys.executable, '-c',"
            " 'import time;time.sleep(25)'],"
            " start_new_session=True, stdin=subprocess.DEVNULL,"
            " stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL);"
            "open(sys.argv[1], 'w').write(str(p.pid));"
            "time.sleep(25)"
        )
        worker = subprocess.Popen(
            [sys.executable, "-c", child, sys.argv[2]],
            start_new_session=True, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(200):
                if os.path.exists(sys.argv[2]):
                    break
                time.sleep(0.01)
            pid = int(open(sys.argv[2]).read())
            os.killpg(worker.pid, signal.SIGKILL)
            worker.wait(timeout=2)
            assert pid in module._children(), "detached process was not adopted"
            module._cleanup_adopted_children()
            assert pid not in module._children()
            print("SUPERVISOR_REAP_PASS")
        finally:
            if worker.poll() is None:
                worker.kill()
                worker.wait()
    """)
    env = os.environ.copy()
    env["QUPRS_RUST_SUPERVISOR_PARENT_PID"] = str(os.getpid())
    outcome = subprocess.run(
        [sys.executable, "-c", witness, str(supervisor), str(marker)],
        env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=12, check=False,
    )
    assert outcome.returncode == 0, outcome.stderr
    assert "SUPERVISOR_REAP_PASS" in outcome.stdout

@pytest.mark.parametrize("exit_code", (0, 125))
def test_timeout_requires_supervisor_cleanup_certification(monkeypatch, exit_code):
    import io
    from QuPRS.interface import rust_isolation as isolation

    class FakeSupervisor:
        def __init__(self):
            self.returncode = exit_code
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO()
            self.stderr = io.BytesIO()

        def poll(self):
            return self.returncode

    monkeypatch.setattr(isolation.subprocess, "Popen", lambda *args, **kwargs: FakeSupervisor())
    monkeypatch.setattr(isolation, "_stop_worker", lambda worker: None)

    def timeout(*args, **kwargs):
        raise isolation._WorkerDeadlineExceeded("controlled deadline")

    monkeypatch.setattr(isolation, "_bounded_exchange", timeout)
    now = time.monotonic()
    call = lambda: isolation.run_isolated(
        'OPENQASM 2.0;', 'OPENQASM 2.0;',
        options={"tool_name": "gpmc"}, request_started=now, request_deadline=now + 30,
    )
    if exit_code == 0:
        assert call()["status"] == "Timeout"
    else:
        with pytest.raises(isolation.RustWorkerError, match="cleanup failed after deadline"):
            call()

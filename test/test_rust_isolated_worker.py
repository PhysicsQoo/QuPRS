"""Focused QOO-175 smoke, parity and isolated IPC fault injection.

These tests intentionally do not claim cgroup or detached solver-tree protection.
"""
import os
import subprocess
import sys
import time

import psutil
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

def test_stop_worker_terminates_visible_detached_solver_child():
    # start_new_session gives the solver a separate process group, so
    # killpg(worker.pid) alone cannot end it.
    script = (
        "import subprocess, sys, time; "
        "p = subprocess.Popen([sys.executable, '-c', "
        "'import time; time.sleep(30)'], "
        "stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, "
        "stderr=subprocess.DEVNULL, start_new_session=True); "
        "print(p.pid, flush=True); time.sleep(30)"
    )
    worker = _spawn_script(script)
    solver_pid = int(worker.stdout.readline().decode().strip())
    try:
        assert psutil.pid_exists(solver_pid)
        _stop_worker(worker)
        for _ in range(20):
            try:
                child = psutil.Process(solver_pid)
                if child.status() == psutil.STATUS_ZOMBIE:
                    break
            except psutil.NoSuchProcess:
                break
            time.sleep(0.02)
        else:
            pytest.fail("detached solver child survived isolated-worker cleanup")
    finally:
        if worker.poll() is None:
            _stop_worker(worker)
        try:
            psutil.Process(solver_pid).kill()
        except psutil.NoSuchProcess:
            pass


def test_explicit_physical_memory_cap_fails_closed_without_cgroup(monkeypatch):
    monkeypatch.setenv("QUPRS_ISOLATED_MAX_MEMORY_MIB", "1024")
    qasm = 'OPENQASM 2.0;\\ninclude "qelib1.inc";\\nqreg q[1];\\n'
    with pytest.raises(RustWorkerError, match="requires an unavailable delegated cgroup"):
        check_equivalence(
            qasm, qasm, backend="rust", safe_mode=True,
            method="reduction_rules", timeout=30,
        )


def test_bad_address_space_limit_fails_before_worker_import(monkeypatch):
    monkeypatch.setenv("QUPRS_ISOLATED_MAX_ADDRESS_SPACE_MIB", "invalid")
    qasm = 'OPENQASM 2.0;\\ninclude "qelib1.inc";\\nqreg q[1];\\n'
    with pytest.raises(RustWorkerError, match="exited with 125"):
        check_equivalence(
            qasm, qasm, backend="rust", safe_mode=True,
            method="reduction_rules", timeout=30,
        )


def test_address_space_cap_applies_only_inside_worker(monkeypatch):
    import resource

    if not hasattr(resource, "RLIMIT_AS"):
        pytest.skip("RLIMIT_AS unsupported on this platform")
    code = (
        "import os, resource; "
        "from QuPRS._rust_worker_bootstrap import _apply_address_space_cap; "
        "_apply_address_space_cap(); "
        "print(resource.getrlimit(resource.RLIMIT_AS)[0])"
    )
    env = os.environ.copy()
    env["QUPRS_ISOLATED_MAX_ADDRESS_SPACE_MIB"] = "4096"
    parent_before = resource.getrlimit(resource.RLIMIT_AS)
    completed = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True,
        text=True, timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
    assert int(completed.stdout.strip()) <= 4096 * 1024 * 1024
    assert resource.getrlimit(resource.RLIMIT_AS) == parent_before



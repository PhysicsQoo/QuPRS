"""No QuPRS dependency: worker transport and warm-process policy regressions."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import textwrap

import pytest

HELPER = Path(__file__).resolve().parents[1] / "scripts" / "codspeed_paired_walltime.py"
spec = importlib.util.spec_from_file_location("codspeed_paired_walltime", HELPER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _fake_source(tmp_path: Path):
    source = tmp_path / "base"
    pkg = tmp_path / "packages"
    source.mkdir()
    pkg.mkdir()
    (pkg / "QuPRS.py").write_text(textwrap.dedent('''
        from types import SimpleNamespace
        import os
        count = 0
        def check_equivalence(left, right, **kw):
            global count
            count += 1
            assert kw['method'] == 'hybrid'
            assert kw['timeout'] == 120
            return SimpleNamespace(equivalent='equivalent', wmc_solver_invoked=True,
                                   rr_approximate=False)
    '''))
    root = source / "benchmarks" / "MQTBench"
    (root / "h,ry,rz,cx").mkdir(parents=True)
    for filename, *_ in module.CASES.values():
        (root / filename).write_text("OPENQASM 2.0;\n")
        (root / "h,ry,rz,cx" / filename).write_text("OPENQASM 2.0;\n")
    return source, pkg


def test_persistent_process_and_metadata(tmp_path, monkeypatch):
    root, pkg = _fake_source(tmp_path)
    monkeypatch.setenv("PYTHONPATH", str(pkg))
    sock = tmp_path / "socket" / "worker.sock"
    with module.PersistentWorker(Path(sys.executable), HELPER, root, sock) as worker:
        a = worker.verify("vqe4_gpmc")
        b = worker.verify("qft16_ganak")
        assert a["pid"] == b["pid"] == worker.process.pid
        assert a["solver_invoked"] == "true"
        assert a["stage"] == "wmc"
        assert a["verdict"] == "equivalent"
        assert b["case"] == "qft16_ganak"
    assert not sock.exists()
    assert worker.process is None


def test_worker_rejects_missing_fixture_without_inventing_measurement(tmp_path, monkeypatch):
    root, pkg = _fake_source(tmp_path)
    target = root / "benchmarks" / "MQTBench" / "vqe_nativegates_ibm_qiskit_opt0_4.qasm"
    target.unlink()
    monkeypatch.setenv("PYTHONPATH", str(pkg))
    sock = tmp_path / "socket2" / "worker.sock"
    with module.PersistentWorker(Path(sys.executable), HELPER, root, sock) as worker:
        with pytest.raises(RuntimeError, match="FileNotFoundError"):
            worker.verify("vqe4_gpmc")
        assert worker.verify("qft16_gpmc")["verdict"] == "equivalent"
    assert not sock.exists()


def test_worker_validates_requested_case_before_timing(tmp_path, monkeypatch):
    root, pkg = _fake_source(tmp_path)
    monkeypatch.setenv("PYTHONPATH", str(pkg))
    sock = tmp_path / "socket3" / "worker.sock"
    with module.PersistentWorker(Path(sys.executable), HELPER, root, sock) as worker:
        with pytest.raises(KeyError):
            worker.verify("typo_case")

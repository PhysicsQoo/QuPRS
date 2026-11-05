"""Minimal PyO3 worker must not import the expensive QuPRS/Qiskit package."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from QuPRS import _pathsum_rust
from QuPRS.interface import rust_isolation


QASM = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'


def test_standalone_loader_runs_native_rr_without_package_import():
    script = r"""
import importlib.util, pathlib, sys
p = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(p.parent))
import rust_worker_standalone
assert 'QuPRS' not in sys.modules
assert 'qiskit' not in sys.modules
native = rust_worker_standalone._load_native_extension(sys.argv[2])
assert 'QuPRS' not in sys.modules
assert 'qiskit' not in sys.modules
qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
r = native.check_equivalence(qasm, qasm, method='reduction_rules')
assert r['status'] == 'Equivalent', r
print('MINIMAL_NATIVE_RR_PASS')
"""
    path = Path(rust_isolation.__file__).with_name("rust_worker_standalone.py")
    done = subprocess.run(
        [sys.executable, "-c", script, str(path), _pathsum_rust.__file__],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=25,
    )
    assert done.returncode == 0, done.stderr
    assert "MINIMAL_NATIVE_RR_PASS" in done.stdout


def test_standalone_worker_json_result_matches_direct_native_rr():
    options = {
        "method": "reduction_rules",
        "strategy": "Difference",
        "tool_name": "gpmc",
        "timeout": 30,
        "wmc_phase_tolerance": 1e-8,
        "approximate_distance_tolerance": 1e-8,
        "rr_tolerance": 1e-10,
        "phase_tolerance": 1e-8,
        "gpmc_precision_digits": 30,
    }
    payload = {
        "version": 1,
        "circuit1": QASM,
        "circuit2": QASM,
        "options": options,
        "rust_extension_path": _pathsum_rust.__file__,
    }
    path = Path(rust_isolation.__file__).with_name("rust_worker_standalone.py")
    result = subprocess.run(
        [sys.executable, str(path)],
        input=json.dumps(payload), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25,
    )
    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)
    assert response["ok"] is True, response
    assert response["result"]["status"] == "Equivalent"
    assert response["result"]["stats"] == _pathsum_rust.check_equivalence(
        QASM, QASM, method="reduction_rules",
    )["stats"]

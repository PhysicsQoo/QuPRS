"""Regression tests for the source-CNF interval bridge's provenance contract.

All fixtures here are synthetic and verify rejection logic only. The workflow
separately runs the bridge over actual Python/Rust emitted CNF artifacts.
"""
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from run_source_interval_bridge import check_observation, GATES, HEADER  # noqa: E402


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture(tmp_path, case="t", solver="gpmc"):
    source = (HEADER + GATES[case]).encode()
    python_cnf = b"python fixture\n"
    rust_cnf = b"rust fixture\n"
    (tmp_path / f"{case}.qasm").write_bytes(source)
    (tmp_path / f"{case}-python-{solver}.cnf").write_bytes(python_cnf)
    (tmp_path / f"{case}-{solver}.cnf").write_bytes(rust_cnf)
    record = {
        "case": case,
        "solver": solver,
        "observational_pass": True,
        "formal_equivalence_certificate": False,
        "exit_code": 0,
        "native_stdout": "fixture only",
        "native_stderr": "",
        "source_qasm_sha256": digest(source),
        "python_emitted_cnf_sha256": digest(python_cnf),
        "rust_emitted_cnf_sha256": digest(rust_cnf),
        "cnf_bytes_equal": False,
        "selected_binary_sha256": "a" * 64,
    }
    record_path = tmp_path / f"{case}-python-{solver}.json"
    record_path.write_text(json.dumps(record))
    return record, record_path


@pytest.mark.parametrize("case", ["hh", "x", "t"])
@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
def test_exact_observation_artifact_identity(tmp_path, case, solver):
    record, _ = fixture(tmp_path, case, solver)
    observed, source, path = check_observation(tmp_path, case, solver)
    assert observed == record
    assert source == HEADER + GATES[case]
    assert path.name == f"{case}-python-{solver}.cnf"


@pytest.mark.parametrize("tampering", [
    "python_cnf", "rust_cnf", "qasm", "case", "solver", "failed_solver",
    "false_certification", "missing_binary_provenance", "incorrect_byte_equality",
])
def test_mismatched_provenance_refused(tmp_path, tampering):
    record, record_path = fixture(tmp_path)
    if tampering == "python_cnf":
        (tmp_path / "t-python-gpmc.cnf").write_bytes(b"modified")
    elif tampering == "rust_cnf":
        (tmp_path / "t-gpmc.cnf").write_bytes(b"modified")
    elif tampering == "qasm":
        (tmp_path / "t.qasm").write_bytes(b"new source")
    elif tampering == "case":
        record["case"] = "x"
    elif tampering == "solver":
        record["solver"] = "ganak"
    elif tampering == "failed_solver":
        record["exit_code"] = 1
    elif tampering == "false_certification":
        record["formal_equivalence_certificate"] = True
    elif tampering == "missing_binary_provenance":
        record["selected_binary_sha256"] = None
    elif tampering == "incorrect_byte_equality":
        record["cnf_bytes_equal"] = True
    record_path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        check_observation(tmp_path, "t", "gpmc")


def test_changed_qasm_even_with_recomputed_hash_is_rejected(tmp_path):
    record, record_path = fixture(tmp_path)
    modified = (HEADER + "rz(0.001) q[0];\n").encode()
    (tmp_path / "t.qasm").write_bytes(modified)
    record["source_qasm_sha256"] = digest(modified)
    record_path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="exact supported fixture"):
        check_observation(tmp_path, "t", "gpmc")

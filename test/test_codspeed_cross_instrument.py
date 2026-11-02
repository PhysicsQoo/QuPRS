"""Audit cross-instrument CodSpeed identity without manufacturing timings."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sha_audit", ROOT / "scripts/report_codspeed_cross_instrument.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
SHA = "a" * 40
BASE = "b" * 40


def fixture_tree(tmp_path, monkeypatch, *, bad_sha=False, omit_case=False):
    ids = [f"test/test_Feynman.py::case[{i}]" for i in range(29)]
    ids += [f"test/test_MQT.py::test_all_benchmarks[{case}.qasm-proportional-False-gpmc-rust]"
            for case in ("vqe_nativegates_ibm_qiskit_opt0_4",
                         "qaoa_nativegates_ibm_qiskit_opt0_7",
                         "qft_nativegates_ibm_qiskit_opt0_16")]
    assert len(ids) == 32
    monkeypatch.setattr(module, "CANONICAL_SHA",
                        hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest())
    for shard in range(5):
        folder = tmp_path / f"quprs-sha-simulation-{shard}"
        folder.mkdir()
        entries = [{"uri": key, "stats": {"cpu_total_ns": (shard + 1) * 10}}
                   for pos, key in enumerate(ids) if pos % 5 == shard]
        if omit_case and shard == 2:
            entries.pop()
        raw = json.dumps({"instrument": {"type": "cpu"}, "benchmarks": entries}).encode()
        (folder / f"simulation-{shard}.json").write_bytes(raw)
        (folder / "manifest.json").write_text(json.dumps({
            "schema": "quprs-codspeed-sha-v2",
            "sha": BASE if bad_sha and shard == 0 else SHA,
            "fixture_revision_sha": SHA,
            "measurement_status": "uploaded_by_codspeed_action",
            "family": "simulation-shard", "instrument": "simulation",
            "shard": shard, "num_shards": 5,
            "measurement_sha256": hashlib.sha256(raw).hexdigest(),
        }))
    native = tmp_path / "quprs-sha-rust-core-simulation"
    native.mkdir()
    (native / "manifest.json").write_text(json.dumps({
        "schema": "quprs-codspeed-sha-v2", "sha": SHA,
        "fixture_revision_sha": SHA,
        "measurement_status": "uploaded_by_codspeed_action",
        "family": "rust-core", "instrument": "simulation",
        "expected_ids": [f"native-case-{i}" for i in range(11)],
    }))
    wall = tmp_path / "walltime-report"
    wall.mkdir()
    cases = []
    for case in ("vqe4_gpmc", "qaoa7_gpmc", "qft16_gpmc",
                 "grover4_ganak", "vqe4_ganak", "vqe4_gpmc_python",
                 "vqe4_ganak_python"):
        cases.append({
            "case": case, "base_median_ms": 900, "head_median_ms": 880,
            "change_percent": -2.0, "verdict_base": "equivalent",
            "verdict_head": "equivalent", "performance_comparable": True,
            "solver_invoked_base": True, "solver_invoked_head": True,
        })
    (wall / "paired-walltime-report.json").write_text(json.dumps({
        "base_sha": BASE, "head_sha": SHA, "status": "PRECISION_LIMITED",
        "errors": [], "cases": cases,
    }))


def test_reports_same_sha_without_certifying_precision_limited(tmp_path, monkeypatch):
    fixture_tree(tmp_path, monkeypatch)
    output = module.produce(tmp_path, SHA, BASE)
    assert output["five_shard_canonical_count"] == 32
    assert output["native_core_expected_count"] == 11
    assert output["walltime_paired_cases"] == 7
    assert output["scientific_status"] == "PRECISION_LIMITED"
    assert output["performance_certified"] is False
    assert {row["case"] for row in output["cross_instrument_rows"]} == {
        "vqe4_gpmc", "qaoa7_gpmc", "qft16_gpmc"
    }


@pytest.mark.parametrize("corruption, expected", [
    ({"bad_sha": True}, "wrong SHA"),
    ({"omit_case": True}, "incomplete canonical five-shard"),
])
def test_source_identity_and_missing_case_block_cross_report(tmp_path, monkeypatch,
                                                              corruption, expected):
    fixture_tree(tmp_path, monkeypatch, **corruption)
    with pytest.raises(ValueError, match=expected):
        module.produce(tmp_path, SHA, BASE)


def test_missing_walltime_is_baseline_only(tmp_path, monkeypatch):
    fixture_tree(tmp_path, monkeypatch)
    result = module.produce(tmp_path, SHA, "")
    assert result["scientific_status"] == "BASELINE_ONLY"
    assert result["walltime_paired_cases"] == 0

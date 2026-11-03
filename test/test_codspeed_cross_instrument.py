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
from benchmarks.codspeed.case_registry import NATIVE_IDS

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
        "expected_ids": list(NATIVE_IDS),
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
    assert output["native_core_expected_count"] == len(NATIVE_IDS)
    assert output["walltime_paired_cases"] == 7
    assert output["scientific_status"] == "PRECISION_LIMITED"
    assert output["performance_certified"] is False
    assert {row["case"] for row in output["cross_instrument_rows"]} == {
        "vqe4_gpmc", "qaoa7_gpmc", "qft16_gpmc"
    }


@pytest.mark.parametrize("corruption, expected", [
    ({"bad_sha": True}, "wrong SHA"),
    ({"omit_case": True}, "original 32 CodSpeed benchmark identities changed"),
])
def test_source_identity_and_missing_case_block_cross_report(tmp_path, monkeypatch,
                                                              corruption, expected):
    fixture_tree(tmp_path, monkeypatch, **corruption)
    with pytest.raises(ValueError, match=expected):
        module.produce(tmp_path, SHA, BASE)


def test_additive_qasm261_12_uris_coexist_with_legacy_32(tmp_path, monkeypatch):
    from benchmarks.codspeed.simulation_addon import (
        QASM261_COUNT, QASM261_SHA256, QASM261_URIS,
    )
    fixture_tree(tmp_path, monkeypatch)
    # Reconstruct a complete expanded suite without overwriting legacy data.
    for shard in range(5):
        folder = tmp_path / f"quprs-sha-simulation-{shard}"
        json_file = folder / f"simulation-{shard}.json"
        current = json.loads(json_file.read_text())
        current["benchmarks"].extend(
            {"uri": uri, "stats": {"cpu_total_ns": 55}}
            for i, uri in enumerate(QASM261_URIS) if i % 5 == shard
        )
        raw = json.dumps(current).encode()
        json_file.write_bytes(raw)
        meta_file = folder / "manifest.json"
        meta = json.loads(meta_file.read_text())
        meta["measurement_sha256"] = hashlib.sha256(raw).hexdigest()
        meta["simulation_addon"] = {
            "suite": "qiskit-2.6.1-opt0-v2-cpu",
            "count": QASM261_COUNT, "identity_sha256": QASM261_SHA256,
        }
        meta_file.write_text(json.dumps(meta))
    output = module.produce(tmp_path, SHA, BASE)
    assert output["five_shard_canonical_count"] == 32
    assert output["qasm261_addon_count"] == 12
    assert output["simulation_total_count"] == 44
    assert len(output["simulation_uris"]) == 44
    # Missing even one modern URI fails; archive 32 do not hide incomplete 12.
    first = tmp_path / "quprs-sha-simulation-0" / "simulation-0.json"
    contents = json.loads(first.read_text())
    contents["benchmarks"] = [
        x for x in contents["benchmarks"]
        if x["uri"] != QASM261_URIS[0]
    ]
    raw = json.dumps(contents).encode()
    first.write_bytes(raw)
    metadata = first.parent / "manifest.json"
    row = json.loads(metadata.read_text())
    row["measurement_sha256"] = hashlib.sha256(raw).hexdigest()
    metadata.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="incomplete QASM261"):
        module.produce(tmp_path, SHA, BASE)


def test_missing_walltime_is_baseline_only(tmp_path, monkeypatch):
    fixture_tree(tmp_path, monkeypatch)
    result = module.produce(tmp_path, SHA, "")
    assert result["scientific_status"] == "BASELINE_ONLY"
    assert result["walltime_paired_cases"] == 0


def test_versioned_simulation_v3_dynamic_three_shards(tmp_path):
    from benchmarks.codspeed.suite_compat import suite_spec_digest, load_catalog
    suite = load_catalog()["suites"][1]
    names = [f"benchmarks/codspeed/test_curated.py::candidate[{i}]"
             for i in range(4)]
    for shard in range(3):
        directory = tmp_path / f"curated-{shard}"
        directory.mkdir()
        payload = json.dumps({"benchmarks": [
            {"uri": uri, "stats": {"cpu_total_ns": 123}}
            for i, uri in enumerate(names) if i % 3 == shard
        ]}).encode()
        (directory / f"simulation-{shard}.json").write_bytes(payload)
        record = {
            "schema": "quprs-codspeed-sha-v3", "family": "curated-cpu",
            "sha": SHA, "fixture_revision_sha": SHA,
            "measurement_status": "uploaded_by_codspeed_action",
            "instrument": "simulation",
            "suite_id": suite["suite_id"], "suite_version": suite["version"],
            "suite_spec_sha256": suite_spec_digest(suite),
            "measurement_scope": suite["measurement_scope"],
            "simulation_track_subprocess": False,
            "metric_units": "modeled_cpu_seconds",
            "runner_cohort": "linux-hosted-cpu-a",
            "shard": shard, "num_shards": 3,
            "measurement_sha256": hashlib.sha256(payload).hexdigest(),
        }
        (directory / "manifest.json").write_text(json.dumps(record))
    found = module.validate_curated_simulation(
        tmp_path, SHA, suite_id=suite["suite_id"], expected_uris=names,
    )
    assert set(found) == set(names)
    with pytest.raises(ValueError, match="incomplete candidate URI"):
        module.validate_curated_simulation(
            tmp_path, SHA, suite_id=suite["suite_id"],
            expected_uris=names+["unmeasured-case"],
        )
    (tmp_path / "curated-2" / "simulation-2.json").write_text("{}")
    with pytest.raises(ValueError, match="digest mismatch"):
        module.validate_curated_simulation(
            tmp_path, SHA, suite_id=suite["suite_id"], expected_uris=names,
        )

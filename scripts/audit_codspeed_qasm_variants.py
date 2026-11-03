#!/usr/bin/env python3
"""Read-only exact-blob audit for the CodSpeed QASM v2 candidate review.

No Solver or CodSpeed run; never use its output as measured runtime.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from benchmarks.codspeed import case_registry as reg

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "benchmarks/codspeed/qasm_variant_audit.json"
CORPUS = ROOT / "benchmarks/MQTBench/qiskit-2.6.1-opt0"


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _file_blob(path: str, expected: str) -> None:
    data = (ROOT / path).read_bytes()
    actual = _git_blob_sha(data)
    if actual != expected:
        raise AssertionError(f"Git blob mismatch: {path}: {actual} != {expected}")


def _file_sha256(path: str, expected: str) -> None:
    actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    if actual != expected:
        raise AssertionError(f"QASM SHA256 mismatch: {path}: {actual} != {expected}")


def selected_by_registry() -> dict[str, set[str]]:
    spec = importlib.util.spec_from_file_location(
        "legacy_cases_qasm_audit", ROOT / "test/_benchmark_cases.py"
    )
    legacy = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(legacy)
    catalog = json.loads((ROOT / "benchmarks/codspeed/suite_catalog.json").read_text())
    return {
        "legacy-simulation-32": {row[0] for row in legacy.MQT_CASES},
        "solver-walltime-7": {row[1] for row in reg.WALLTIME_CASES},
        "solver-cpu-opt-in": {row[1] for row in reg.SOLVER_CPU_CASES},
        "cross-method-opt-in": {row[1] for row in reg.CROSS_CIRCUITS},
        "pilot-eight-opt-in": {case.qasm for case in reg.PILOT_CASES},
        "paper-gap-seven-opt-in": {case.qasm for case in reg.PAPER_GAP_PILOT_CASES},
        "curated-v2-proposed": {
            row["qasm"] for row in catalog["suites"][1]["candidates"]
        },
    }


def audit() -> dict:
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    negatives = json.loads(
        (CORPUS / "random-rotation-manifest.json").read_text(encoding="utf-8")
    )
    registered = json.loads((CORPUS / "source-register.json").read_text(encoding="utf-8"))
    actual_selected = selected_by_registry()
    manifest_by_file = {x["file"]: x for x in manifest["files"]}
    neg_by_file = {x["file"]: x for x in negatives["cases"]}
    source_by_file = {x["path"]: x for x in registered["source_qasms"]}
    rows = doc["mqt"]
    assert len(rows) == len(manifest_by_file) == len(neg_by_file) == len(source_by_file) == 37
    assert {x["file"] for x in rows} == set(manifest_by_file)
    assert set(actual_selected) == set.union(*(set(x["selected_by"]) for x in rows))
    assert doc["policy"]["main_legacy_benchmark_identities"] == 32
    assert doc["policy"]["canonical_shards"] == 5
    assert doc["policy"]["main_identity_sha256"] == reg.LEGACY_IDENTITY_SHA256
    assert doc["selected_mqt_unique"] == 20
    assert doc["selected_feynman_unique"] == 4

    science = {"cases": 0, "observations": 0, "matched": 0, "censored": 0, "contradictions": 0}
    for row in rows:
        name = row["file"]
        generated = manifest_by_file[name]
        original = source_by_file[name]
        negative = neg_by_file[name]
        expected_tags = sorted(k for k, names in actual_selected.items() if name in names)
        assert sorted(row["selected_by"]) == expected_tags, name
        assert row["source"]["git_blob_sha1"] == original["git_blob_sha1"]
        assert row["qiskit261_positive"]["sha256"] == generated["generated_sha256"]
        assert row["qiskit261_negative"]["sha256"] == negative["output_sha256"]
        assert negative["baseline_qasm_sha256"] == generated["generated_sha256"]
        _file_blob(**{"path": row["source"]["path"],
                       "expected": row["source"]["git_blob_sha1"]})
        _file_blob(row["historical_target"]["path"],
                   row["historical_target"]["git_blob_sha1"])
        _file_sha256(row["qiskit261_positive"]["path"],
                     row["qiskit261_positive"]["sha256"])
        _file_sha256(row["qiskit261_negative"]["path"],
                     row["qiskit261_negative"]["sha256"])
        for variant in ("positive", "negative"):
            for method in ("hybrid", "wmc_only"):
                observation = row["strict_1e8_gpmc30"][f"{variant}_{method}"]
                assert observation["matched"] + observation["censored"] + observation["contradictions"] == 2
                science["observations"] += 2
                for key in ("matched", "censored", "contradictions"):
                    science[key] += observation[key]
        science["cases"] += 1

    legacy_spec = importlib.util.spec_from_file_location(
        "legacy_feynman_qasm_audit", ROOT / "test/_benchmark_cases.py"
    )
    legacy = importlib.util.module_from_spec(legacy_spec)
    assert legacy_spec and legacy_spec.loader
    legacy_spec.loader.exec_module(legacy)
    assert {row["file"] for row in doc["feynman"]} == {x[0] for x in legacy.FEYNMAN_CASES}
    for row in doc["feynman"]:
        _file_blob(row["source"]["path"], row["source"]["git_blob_sha1"])
        _file_blob(row["historical_target"]["path"], row["historical_target"]["git_blob_sha1"])

    expected = doc["science_evidence"]
    assert science == {"cases": 37, "observations": 296, "matched": 244,
                       "censored": 52, "contradictions": 0}
    assert (expected["total"], expected["returned_and_binary_matching"],
            expected["censored"], expected["determinate_binary_contradictions"]) == (296, 244, 52, 0)
    assert expected["solver_arithmetic_certified"] is False
    assert expected["not_codspeed_performance_data"] is True

    legacy_mqt = [row for row in rows if "legacy-simulation-32" in row["selected_by"]]
    assert len(legacy_mqt) == 6
    assert sum(obs["matched"] for row in legacy_mqt
               for obs in row["strict_1e8_gpmc30"].values()) == 48
    for case in reg.QASM261_PILOT_CASES:
        assert case.qasm_corpus == "qiskit-2.6.1-opt0"
        row = next(x for x in rows if x["file"] == case.qasm)
        variant = "negative" if case.pair_variant == "random_rotation" else "positive"
        obs = row["strict_1e8_gpmc30"][f"{variant}_hybrid"]
        assert obs["matched"] == 2 and obs["censored"] == 0
    assert len({x.id for x in reg.QASM261_PILOT_CASES}) == len(reg.QASM261_PILOT_CASES)
    assert not ({x.id for x in reg.QASM261_PILOT_CASES} &
                {x.id for x in (*reg.PILOT_CASES, *reg.PAPER_GAP_PILOT_CASES)})
    return {"status": "QASM261_SOURCE_REVIEW_PASS", **science,
            "selected_mqt": 20, "feynman": 4,
            "versioned_pilots": len(reg.QASM261_PILOT_CASES)}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))

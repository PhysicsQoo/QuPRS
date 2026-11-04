"""Frozen legacy and additive QASM261 Simulation source identity guards."""
import hashlib
import json
from pathlib import Path

from benchmarks.codspeed.simulation_addon import (
    BACKENDS, CORPUS_VERSION, QASM261_CASES, QASM261_COUNT,
    QASM261_SHA256, QASM261_URIS, SOLVERS,
)
ROOT = Path(__file__).resolve().parents[1]


def test_additive_12_cpu_uri_identities_preserve_legacy_32():
    assert len(QASM261_CASES) == 6
    assert len(QASM261_URIS) == len(set(QASM261_URIS)) == QASM261_COUNT == 12
    assert hashlib.sha256(
        "\n".join(sorted(QASM261_URIS)).encode("utf-8")
    ).hexdigest() == QASM261_SHA256
    assert {u.split("::")[0] for u in QASM261_URIS} == {
        "benchmarks/codspeed/test_mqt_qasm261_simulation.py"
    }
    assert len(BACKENDS) == 2 and SOLVERS == ("gpmc",)
    # Before v0.14 release, the Ganak aliases were dev-only and retired:
    # CPU Simulation cannot include the actual child Solver subprocess.
    assert all("_ganak_" not in uri for uri in QASM261_URIS)
    assert all("_gpmc_" in uri for uri in QASM261_URIS)


def test_all_six_additive_pairs_match_qiskit261_source_manifest():
    manifest = json.loads((
        ROOT / "benchmarks/MQTBench" / CORPUS_VERSION / "manifest.json"
    ).read_text(encoding="utf-8"))
    index = {row["file"]: row for row in manifest["files"]}
    for case_id, filename, strategy, reverse in QASM261_CASES:
        row = index[filename]
        original = ROOT / "benchmarks/MQTBench" / filename
        translated = ROOT / row["generated_path"]
        assert (ROOT / row["source_path"]) == original
        assert translated == (
            ROOT / "benchmarks/MQTBench" / CORPUS_VERSION
            / "h,ry,rz,cx" / filename
        )
        assert hashlib.sha256(original.read_bytes()).hexdigest() == row["source_sha256"]
        assert hashlib.sha256(translated.read_bytes()).hexdigest() == row["generated_sha256"]


def test_additive_does_not_change_legacy_case_selection():
    import importlib.util
    module_path = ROOT / "test/_benchmark_cases.py"
    spec = importlib.util.spec_from_file_location("legacy_cases_exact", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert 2 * len(module.FEYNMAN_CASES) + 4 * len(module.MQT_CASES) == 32

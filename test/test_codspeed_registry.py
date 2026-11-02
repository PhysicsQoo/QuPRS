"""Frozen ID, artifact fixture and timeout-contract tests for CodSpeed v3."""
import importlib.util
import json
from pathlib import Path

from benchmarks.codspeed.case_registry import (
    CROSS_INSTRUMENT_MATCH, CROSS_METHOD_CASES, CROSS_METHOD_CPU_IDS,
    GANAK_PRECISION_LIMIT_CASES, LEGACY_CASE_COUNT, LEGACY_SHARD_COUNT,
    PILOT_CASES, SOLVER_CPU_CASES, WALLTIME_CASES, WALLTIME_CASE_IDS,
    PYTHON_CORE_CASE_IDS, NATIVE_IDS,
)

ROOT = Path(__file__).resolve().parents[1]
DIFFICULTY = ROOT / "benchmarks" / "codspeed" / "paper_difficulty.json"
FIXTURES = ROOT / "benchmarks" / "MQTBench"


def test_frozen_original_five_shards_and_32_node_id_contract():
    spec = importlib.util.spec_from_file_location(
        "legacy_cases", ROOT / "test" / "_benchmark_cases.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert LEGACY_SHARD_COUNT == 5
    assert 2 * len(module.FEYNMAN_CASES) + 4 * len(module.MQT_CASES) == LEGACY_CASE_COUNT == 32


def test_shared_registry_stable_7_plus_7_and_cross_case_ids():
    assert len(WALLTIME_CASES) == len(WALLTIME_CASE_IDS) == 7
    assert len(set(case[0] for case in SOLVER_CPU_CASES)) == len(SOLVER_CPU_CASES) == 7
    assert len(CROSS_METHOD_CASES) == 24
    assert len(CROSS_METHOD_CPU_IDS) == 4
    assert len(PYTHON_CORE_CASE_IDS) == 5
    assert len(NATIVE_IDS) == 14
    assert set(CROSS_METHOD_CPU_IDS).issubset({case[0] for case in CROSS_METHOD_CASES})
    assert set(GANAK_PRECISION_LIMIT_CASES).issubset(WALLTIME_CASE_IDS)
    for case_id, filename in CROSS_INSTRUMENT_MATCH.items():
        assert case_id in WALLTIME_CASE_IDS
        assert any(x[0] == case_id and x[1] == filename for x in WALLTIME_CASES)


def test_paper_candidates_source_pinned_and_history_not_promoted():
    report = json.loads(DIFFICULTY.read_text(encoding="utf-8"))
    cases = report["cases"]
    assert len(cases) >= 30
    assert len({x["id"] for x in cases}) == len(cases)
    for case in cases:
        assert (FIXTURES / case["fixture"]).is_file(), case["id"]
        assert case["modern_codspeed_status"] in ("NOT_MEASURED", "RUN_INDEX_ONLY")
        assert not case["promoted"]
        assert case["modern_solver_stage"] == "UNVERIFIED"
        assert case["modern_verdict"] == "UNVERIFIED"
        assert case["modern_memory_risk"] == "UNVERIFIED"
        # Never reuse the old runtime as a modern CodSpeed observation.
        assert "codspeed_seconds" not in case
    assert cases[0]["positive_hybrid_seconds"] == 0.027


def test_pilot_is_bounded_and_not_dependent_on_a_historical_runtime():
    assert len(PILOT_CASES) == len({x.id for x in PILOT_CASES}) == 8
    for case in PILOT_CASES:
        assert (FIXTURES / case.qasm).is_file()
        assert 0 < case.solver_timeout_s < case.watchdog_s <= 30
        assert case.method == "hybrid"
        assert case.expected_solver_invoked is None

"""Frozen ID, artifact fixture and timeout-contract tests for CodSpeed v3."""
import importlib.util
import json
from pathlib import Path

from benchmarks.codspeed.case_registry import (
    CROSS_INSTRUMENT_MATCH, CROSS_METHOD_CASES, CROSS_METHOD_CPU_IDS,
    GANAK_PRECISION_LIMIT_CASES, LEGACY_CASE_COUNT, LEGACY_SHARD_COUNT,
    PILOT_CASES, PAPER_GAP_PILOT_CASES, SOLVER_CPU_CASES, WALLTIME_CASES, WALLTIME_CASE_IDS,
    PYTHON_CORE_CASE_IDS, NATIVE_IDS, REPEATABILITY_CASES,
    REPEATABILITY_EXPECTATIONS,
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
    assert len(NATIVE_IDS) == 25
    assert {"rr_elim_direct", "rr_hh_direct", "rr_omega_direct"}.issubset(set(NATIVE_IDS))
    assert len(REPEATABILITY_CASES) == 4
    assert {case.id for case in REPEATABILITY_CASES} == set(REPEATABILITY_EXPECTATIONS)
    assert set(CROSS_METHOD_CPU_IDS).issubset({case[0] for case in CROSS_METHOD_CASES})
    assert set(GANAK_PRECISION_LIMIT_CASES).issubset(WALLTIME_CASE_IDS)
    for case_id, filename in CROSS_INSTRUMENT_MATCH.items():
        assert case_id in WALLTIME_CASE_IDS
        assert any(x[0] == case_id and x[1] == filename for x in WALLTIME_CASES)


def test_paper_candidates_source_pinned_and_history_not_promoted():
    report = json.loads(DIFFICULTY.read_text(encoding="utf-8"))
    cases = report["cases"]
    assert len(cases) == 36
    assert len({x["id"] for x in cases}) == len(cases)
    measured = {
        "ghz64": ("equivalent*", False, False, 769024008),
        "graphstate32": ("equivalent", False, True, 767543173),
        "qpeexact8": ("equivalent*", False, True, 781616441),
        "qpeinexact8": ("equivalent*", False, True, 765944463),
        "qnn4": ("equivalent*", True, False, 828514013),
        "qwalk3": ("equivalent", False, True, 803068445),
        "wstate4": ("equivalent*", False, True, 802646287),
        "vqe8": ("equivalent", True, False, 808662940),
    }
    assert {x["id"] for x in cases if x["modern_codspeed_status"] == "MEASURED_PRIOR_SHA"} == set(measured)
    for case in cases:
        assert (FIXTURES / case["fixture"]).is_file(), case["id"]
        assert not case["promoted"]
        assert case["modern_memory_risk"] == "UNVERIFIED"
        assert "codspeed_seconds" not in case
        if case["id"] not in measured:
            assert case["modern_codspeed_status"] in ("NOT_MEASURED", "RUN_INDEX_ONLY")
            assert case["modern_solver_stage"] == "UNVERIFIED"
            assert case["modern_verdict"] == "UNVERIFIED"
            assert "modern_codspeed_evidence" not in case
            continue

        verdict, invoked, rr_approximate, elapsed_ns = measured[case["id"]]
        ev = case["modern_codspeed_evidence"]
        assert case["modern_codspeed_run_id"] == "6ae814ed9a84b3bf77ba5e3d"
        assert case["modern_verdict"] == verdict
        assert case["modern_solver_stage"] == (
            "GPMC_INVOKED_HYBRID" if invoked else "RR_TERMINATED_HYBRID"
        )
        assert ev["source_sha"] == "500f8ba66b30e0737de25e928dc3181dd1c2a3b8"
        assert ev["workflow_run_id"] == "41389522077"
        assert ev["artifact_id"] == 13116609534
        assert ev["measurement_sha256"] == "01dfa47e03235dc810c73e8f140fffdde761978459308421d5e10ffc2e2ad88f"
        assert len(ev["qasm_sha256"]) == 2
        assert all(len(s) == 64 and all(c in "0123456789abcdef" for c in s)
                   for s in ev["qasm_sha256"])
        assert (ev["instrument"], ev["measured_rounds"], ev["warmup_iters"]) == ("WallTime", 1, 1)
        assert ev["walltime_ns"] == elapsed_ns
        assert ev["runner_class"] == "GITHUB_HOSTED_NON_MACRO"
        assert (ev["method"], ev["backend"], ev["solver"]) == ("hybrid", "rust", "gpmc")
        assert ev["solver_invoked"] is invoked
        assert ev["rr_approximate"] is rr_approximate
        assert ev["approximate_distance_tolerance"] == 1e-8
        assert ev["completed"] is True and ev["exit_code"] == 0
        assert (ev["solver_timeout_s"], ev["watchdog_s"]) == (15, 24)
        assert ev["performance_certified"] is False
        if invoked:
            assert ev["wmc_precision_reason"] == "printed_count_uncertified_solver_arithmetic"
            assert ev["solver_arithmetic_certified"] is False
            assert ev["wmc_printed_verdict"] == "equivalent"
            assert ev["wmc_numerical_verdict"] == verdict
        else:
            assert ev["wmc_precision_reason"] is None
            assert ev["solver_arithmetic_certified"] is None
            assert ev["wmc_printed_verdict"] is None
            assert ev["wmc_numerical_verdict"] is None
    assert cases[0]["positive_hybrid_seconds"] == 0.027


def test_pilot_is_bounded_and_not_dependent_on_a_historical_runtime():
    assert len(PILOT_CASES) == len({x.id for x in PILOT_CASES}) == 8
    for case in PILOT_CASES:
        assert (FIXTURES / case.qasm).is_file()
        assert 0 < case.solver_timeout_s < case.watchdog_s <= 30
        assert case.method == "hybrid"
        assert case.expected_solver_invoked is None


def test_paper_gap_pilot_has_independent_ids_and_pinned_positive_negative_pairs():
    assert len(PAPER_GAP_PILOT_CASES) == 7
    assert len({c.id for c in PAPER_GAP_PILOT_CASES}) == 7
    assert not ({c.id for c in PAPER_GAP_PILOT_CASES}
                & {c.id for c in PILOT_CASES})
    assert {c.pair_variant for c in PAPER_GAP_PILOT_CASES} == {
        "transpiled", "random_rotation"
    }
    for case in PAPER_GAP_PILOT_CASES:
        counterpart = ("Random_Rotation"
                       if case.pair_variant == "random_rotation" else "h,ry,rz,cx")
        assert (FIXTURES / case.qasm).is_file()
        assert (FIXTURES / counterpart / case.qasm).is_file()
        assert 0 < case.solver_timeout_s < case.watchdog_s <= 30
        assert case.method == "hybrid"
        assert case.expected_solver_invoked is None
        if case.pair_variant == "random_rotation":
            assert case.expected_verdict == "not_equivalent"
        else:
            assert case.expected_verdict == "equivalent_or_phase"


def test_tacas_2026_pdf_table2_and_table3b_source_verified():
    """Fast no-Solver guard for original TACAS printed tables, not modern speed."""
    report = json.loads(DIFFICULTY.read_text(encoding="utf-8"))
    audit = report["source_paper_audit"]
    assert audit["table2_rows"] == 36
    assert audit["table3b_rows"] == 37
    assert audit["original_table2_positive_seconds_matched"] == 36
    assert audit["original_transpiler_version"] == "1.4.2"
    assert audit["current_qiskit261_sources_distinct"] is True
    assert audit["original_paper_says_35_prose_examples_but_table2_contains_36_rows"] is True
    cases = report["cases"]
    assert len(cases) == 36
    assert len({c["id"] for c in cases}) == 36
    assert sum(c["historical_positive_timeout"] for c in cases) == 6
    assert sum(c["historical_negative_timeout"] for c in cases) == 7
    assert sum(c["random_rotation_hybrid_seconds"] is not None for c in cases) == 29
    assert sum(c["positive_hybrid_seconds"] is not None for c in cases) == 30
    for case in cases:
        for suffix, time, timeout, page, table in (
            ("table2", "positive_hybrid_seconds", "historical_positive_timeout", 431, "Table 2"),
            ("table3b", "random_rotation_hybrid_seconds", "historical_negative_timeout", 434, "Table 3(b)"),
        ):
            source = case[f"historical_{suffix}_source"]
            assert source["paper_page"] == page and source["table"] == table
            assert source["hybrid_time_s"] == case[time]
            assert source["timeout"] is case[timeout]
            assert (case[time] is None) is case[timeout]
            if case[time] is not None:
                assert 0 < case[time] < report["timeout_seconds"]
        counts = case["historical_gate_counts"]
        assert all(isinstance(v, int) and v > 0 for v in counts.values())
        assert counts["table3b_injected_gates"] > counts["table2_transpiled_gates"]
        assert case["modern_codspeed_status"] in (
            "RUN_INDEX_ONLY", "MEASURED_PRIOR_SHA", "NOT_MEASURED"
        )
    # These exact values were visually checked against printed Table 3(b) p.434.
    new_finite = {
        "ghz64": .095, "ghz128": .352, "graphstate32": .399,
        "grover6": 45.913, "qaoa9": 1.046, "qaoa11": 1.806,
        "qpeexact16": .993, "qpeexact20": 9.718,
        "qpeinexact16": 2.147, "qpeinexact20": 9.124,
        "qpeinexact24": 1.934, "vqe16": 8.79, "wstate8": .187,
    }
    by_id = {x["id"]: x for x in cases}
    for case_id, value in new_finite.items():
        assert by_id[case_id]["random_rotation_hybrid_seconds"] == value
        assert by_id[case_id]["historical_negative_timeout"] is False
    for case_id in ("grover5", "qft22", "qft24", "qnn12",
                    "qpeexact24", "qwalk5", "wstate16"):
        assert by_id[case_id]["historical_negative_timeout"] is True
        assert by_id[case_id]["random_rotation_hybrid_seconds"] is None
    assert len(report["table3_only_cases"]) == 1
    extra = report["table3_only_cases"][0]
    assert extra["id"] == "wstate32"
    assert extra["paper_cohort"] == "table3_only_not_table2"
    assert extra["historical_negative_timeout"] is True
    assert extra["random_rotation_hybrid_seconds"] is None
    assert extra["historical_gate_counts"]["table3b_injected_gates"] == 264
    assert extra["historical_table3b_source"]["paper_page"] == 434

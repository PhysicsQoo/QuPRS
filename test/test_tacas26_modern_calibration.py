"""Pure, no-Solver tests for TACAS modern calibration on research branch."""
import json
from pathlib import Path

from scripts import tacas26_modern_calibration as m


def test_binary_oracle_requires_eq_versus_neq_agreement():
    assert m.binary("equivalent") == m.binary("equivalent*") == "EQUIVALENT"
    assert m.binary("not_equivalent") == "NOT_EQUIVALENT"
    assert m.binary("Timeout") is None
    assert m.classify("equivalent*", {"verdict": "equivalent"}) == "BINARY_MATCH"
    assert m.classify("equivalent", {"verdict": "not_equivalent"}) == "BINARY_MISMATCH"
    assert m.classify("not_equivalent", {"verdict": "equivalent*"}) == "BINARY_MISMATCH"
    assert m.classify("not_equivalent", {"verdict": "Timeout"}) == "CENSORED_OR_UNCLASSIFIABLE"


def test_experiment_matrix_is_bounded_and_checks_both_directions():
    plan = [entry for shard in range(4) for entry in m.experiment_plan(shard)]
    assert len(plan) == len(set(plan))
    assert len({entry[0] for entry in plan}) == 6
    for case in {entry[0] for entry in plan}:
        assert any(x[0] == case and x[1] == "rust" and x[3] == "1e-8" for x in plan)
        assert any(x[0] == case and x[1] == "rust" and x[3] == "2e-5" for x in plan)
        assert any(x[0] == case and x[1] == "python" and x[3] == "2e-5" for x in plan)
    for c in ("qpeinexact24", "qpeinexact20"):
        x = "table2:" + c + ":positive:hybrid"
        assert any(t[0] == x and t[3] == "1.4e-5" for t in plan)
        assert any(t[0] == x and t[3] == "3e-5" for t in plan)
    assert any(x[2] == "wmc_only" for x in plan)
    assert any(x[4] == "0" for x in plan)
    assert any(x[6] == 90 for x in plan)


def test_archive_real_labels_and_full_source_pin():
    archive = m.archive_labels(m.ROOT)
    canonical = {row["id"]: row for row in m.matrix(m.ROOT)}
    for case_id in (x for shard in m.SHARDS for x in shard):
        row, src, transformed = m.get_pinned_case(m.ROOT, case_id, canonical)
        assert src["sha256"] and transformed["sha256"]
        assert src["sha256"] != transformed["sha256"]
        assert src["historical_source"] == m.SOURCE_SHA
        expected = archive[case_id]["verdict"]
        assert m.binary(expected) == ("EQUIVALENT" if row["kind"] == "positive" else "NOT_EQUIVALENT")


def test_mock_process_preserves_overrides_and_solver_stage(monkeypatch):
    class Fake:
        returncode = 0
        def __init__(self, command, **kwargs):
            env = kwargs["env"]
            assert env["QUPRS_DIAGNOSTIC_DISTANCE_TOLERANCE"] == "2e-5"
            assert env["QUPRS_DIAGNOSTIC_GPMC_DIGITS"] == "90"
            assert env["QUPRS_CROSS_METHOD_SOLVER_TIMEOUT"] == "30"
            assert command[-2:] == ["random_rotation", "hybrid"]
        def communicate(self, timeout=None):
            return (m.MARKER + json.dumps({"verdict": "not_equivalent",
                "solver_invoked": True, "wmc_precision_reason": "printed_uncertified"}) + "\n", "")
    monkeypatch.setattr(m.subprocess, "Popen", Fake)
    spec = ("table3_negative:qaoa11:negative:hybrid", "rust", "hybrid",
            "2e-5", "1e-10", "1e-8", 90)
    row = m.run_probe(m.ROOT, {"kind": "negative",
        "a": "benchmarks/MQTBench/qaoa_nativegates_ibm_qiskit_opt0_11.qasm"},
        spec, solver_timeout=30, watchdog=48)
    assert row["run_status"] == "COMPLETED"
    assert row["solver_invoked"] is True
    assert m.classify("not_equivalent", row) == "BINARY_MATCH"


def test_no_runtime_gate_on_censored_or_invalid():
    for label in ("Timeout", "MemoryOut", "unknown", None):
        assert m.binary(label) is None
    assert m.classify("equivalent*", {"run_status": "WATCHDOG_CENSORED",
                                      "verdict": None}) == "CENSORED_OR_UNCLASSIFIABLE"

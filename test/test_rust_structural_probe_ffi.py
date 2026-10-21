"""Native Rust FFI contract for opt-in Elim structural counters.

This is a lightweight, solver-free integration test. The richer source-pinned
QAOA7/GHZ4 GPMC pilot remains a manual-only scientific experiment.
"""

from qiskit import QuantumCircuit, qasm2

from QuPRS import _pathsum_rust


def test_rust_structural_probe_ffi_is_opt_in_and_semantically_neutral(monkeypatch):
    qc = QuantumCircuit(1)
    qc.h(0)
    source = qasm2.dumps(qc)

    def check():
        return _pathsum_rust.check_equivalence(
            source,
            source,
            method="reduction_rules",
            strategy="Naive",
            tool_name="gpmc",
            timeout=30,
        )

    monkeypatch.delenv("QUPRS_STAGE_LEDGER", raising=False)
    unprofiled = check()
    assert unprofiled["status"] == "Equivalent"
    assert "stage_ledger" not in unprofiled

    monkeypatch.setenv("QUPRS_STAGE_LEDGER", "1")
    profiled = check()
    assert profiled["status"] == unprofiled["status"]
    assert profiled["stats"] == unprofiled["stats"]
    assert profiled["qubits"] == unprofiled["qubits"]
    stage = profiled["stage_ledger"]
    assert stage["schema"] == "quprs-rust-native-exclusive-v0"
    assert stage["stage_calls"].get("reduction", 0) > 0
    assert stage["solver_child_spawns"] == 0  # reduction-only: no GPMC subprocess
    assert not stage["has_stage_overlap"]
    assert abs(stage["closure_error_seconds"]) < 1e-6
    assert abs(sum(stage["exclusive_seconds"].values())
               - stage["total_native_wall_seconds"]) < 1e-6

    assert "elim_attempt_timings" not in stage
    assert "other_rule_timings" not in stage
    records = stage["structural_elim_attempts"]
    assert records, "H/H circuit should exercise actual native Elim attempts"
    expected_keys = {"k_r", "l_r", "v_r", "d_r", "w_redundant_estimated"}
    for sample in records:
        assert set(sample) == expected_keys
        assert all(isinstance(sample[k], int) and sample[k] >= 0
                   for k in expected_keys)
        assert sample["k_r"] <= sample["v_r"]
        assert sample["w_redundant_estimated"] == (
            max(sample["k_r"] - 1, 0) * sample["l_r"]
        )
    assert any(sample["k_r"] > 0 for sample in records)

    # Timing is explicitly opt-in on top of the already opt-in stage ledger.
    monkeypatch.setenv("QUPRS_ELIM_TIMING", "1")
    timed = check()
    assert timed["status"] == unprofiled["status"]
    assert timed["stats"] == unprofiled["stats"]
    timed_stage = timed["stage_ledger"]
    assert timed_stage["structural_elim_attempts"] == records
    elapsed = timed_stage["elim_attempt_timings"]
    assert len(elapsed) == len(records)
    assert [x["structural_index"] for x in elapsed] == list(range(len(records)))
    assert all(type(x["success"]) is bool
               and type(x["elapsed_ns"]) is int and x["elapsed_ns"] >= 0
               for x in elapsed)
    # All Elim calls in this fixture occur within full_reduce() spans.
    assert sum(x["elapsed_ns"] for x in elapsed) / 1e9 <= (
        timed_stage["exclusive_seconds"]["reduction"] + 1e-6
    )

    monkeypatch.setenv("QUPRS_OTHER_RULE_TIMING", "1")
    separate = check()
    assert separate["status"] == unprofiled["status"]
    assert separate["stats"] == unprofiled["stats"]
    other = separate["stage_ledger"]["other_rule_timings"]
    assert other
    assert any(x["rule"] == "candidate_discovery" for x in other)
    assert all(set(x) == {"rule", "elapsed_ns", "success", "candidate_count",
                          "within_reduction"} for x in other)
    assert all(x["elapsed_ns"] >= 0 and type(x["elapsed_ns"]) is int
               and type(x["success"]) is bool
               and type(x["within_reduction"]) is bool for x in other)
    assert sum(x["elapsed_ns"] for x in other if x["within_reduction"]) / 1e9 <= (
        separate["stage_ledger"]["exclusive_seconds"]["reduction"] + 1e-5
    )

    monkeypatch.delenv("QUPRS_STAGE_LEDGER", raising=False)
    after = check()
    assert "stage_ledger" not in after
    assert after["status"] == unprofiled["status"]
    assert after["stats"] == unprofiled["stats"]
    monkeypatch.delenv("QUPRS_ELIM_TIMING", raising=False)
    monkeypatch.delenv("QUPRS_OTHER_RULE_TIMING", raising=False)

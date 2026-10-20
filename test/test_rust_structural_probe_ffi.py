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

    monkeypatch.delenv("QUPRS_STAGE_LEDGER", raising=False)
    after = check()
    assert "stage_ledger" not in after
    assert after["status"] == unprofiled["status"]
    assert after["stats"] == unprofiled["stats"]

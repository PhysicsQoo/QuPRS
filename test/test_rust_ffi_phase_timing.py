"""Native PyO3 FFI phase profiler: opt-in-only structure and semantic parity."""
import os
from QuPRS import _pathsum_rust

QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
h q[0];
"""

def test_native_ffi_phase_timing_opt_in(monkeypatch):
    monkeypatch.setenv("QUPRS_STAGE_LEDGER", "1")
    monkeypatch.delenv("QUPRS_ELIM_TIMING", raising=False)
    monkeypatch.delenv("QUPRS_OTHER_RULE_TIMING", raising=False)
    monkeypatch.delenv("QUPRS_FFI_PHASE_TIMING", raising=False)
    def check():
        return _pathsum_rust.check_equivalence(
            QASM, QASM, method="reduction_rules", strategy="Proportional",
            timeout=15
        )
    control = check()
    assert "ffi_phase_timings" not in control
    monkeypatch.setenv("QUPRS_FFI_PHASE_TIMING", "1")
    profiled = check()
    assert profiled["status"] == control["status"]
    assert profiled["stats"] == control["stats"]
    assert profiled["final_ps"] == control["final_ps"]
    assert profiled["stage_ledger"] == control["stage_ledger"] or (
        profiled["stage_ledger"]["structural_elim_attempts"]
        == control["stage_ledger"]["structural_elim_attempts"]
    )
    phase = profiled["ffi_phase_timings"]
    assert phase["schema"] == "quprs-rust-ffi-phase-v1"
    assert set(phase) == {
        "schema", "qasm_extract_ns", "native_bridge_ns", "python_dict_build_ns",
        "stage_ledger_materialize_ns", "ffi_elapsed_excluding_phase_metadata_ns",
    }
    for key, value in phase.items():
        if key == "schema":
            continue
        assert type(value) is int and value >= 0
    assert phase["qasm_extract_ns"] > 0
    assert phase["native_bridge_ns"] > 0
    assert phase["stage_ledger_materialize_ns"] > 0
    assert phase["python_dict_build_ns"] >= phase["stage_ledger_materialize_ns"]
    assert phase["ffi_elapsed_excluding_phase_metadata_ns"] >= (
        phase["qasm_extract_ns"] + phase["native_bridge_ns"]
        + phase["python_dict_build_ns"]
    )
    monkeypatch.delenv("QUPRS_STAGE_LEDGER", raising=False)
    off = check()
    assert "stage_ledger" not in off
    assert "ffi_phase_timings" in off  # FFI instrumentation is independent.
    monkeypatch.delenv("QUPRS_FFI_PHASE_TIMING", raising=False)
    ordinary = check()
    assert "ffi_phase_timings" not in ordinary

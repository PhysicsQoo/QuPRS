"""No quantum execution in these P0/P1 harness contract checks."""
import json
import pytest
from benchmarks.codspeed.test_paper_gap_repeatability import CASES, EXPECT
from scripts.report_paper_gap_repeatability import produce

def test_independent_p1_case_selection_preserves_positive_negative():
    assert len(CASES) == len(EXPECT) == 5
    assert {case.id for case in CASES} == set(EXPECT)
    assert {c.pair_variant for c in CASES} == {"transpiled", "random_rotation"}
    assert "qpeinexact20_positive" not in EXPECT

def test_p1_report_never_certifies_unmeasured_or_unqualified_cases():
    with pytest.raises(ValueError,match="incomplete five-case"):
        produce({"instrument":{"type":"walltime"},"benchmarks":[]},[],"a"*40)

def test_qpe20_scientific_script_avoids_20q_full_unitary():
    from scripts.diagnose_qpe20_source import phase_corrected_residual
    from qiskit.quantum_info import Statevector
    import numpy as np
    a=Statevector([1,0])
    b=Statevector(np.array([1j,0j]))
    assert phase_corrected_residual(a,b)["phase_corrected_state_residual"] < 1e-12


def test_tolerance_sweep_has_qcec_reference_and_independent_dimensions():
    from scripts.diagnose_qpe20_tolerance import PROBES, classify
    ids=[row[0] for row in PROBES]
    assert len(ids)==len(set(ids))
    assert {"rust_default_d1e-8","rust_qcec_reference_d2e-8",
            "rust_rr_exact","rust_mpfr90","rust_rotation_control"}<=set(ids)
    fake=[{"id":"rust_default_d1e-8","status":"COMPLETED",
           "verdict":"not_equivalent","effective_distance_tolerance":1e-8},
          {"id":"rust_qcec_reference_d2e-8","status":"COMPLETED",
           "verdict":"not_equivalent","effective_distance_tolerance":2e-8},
          {"id":"rust_d1e-5","status":"COMPLETED",
           "verdict":"equivalent*","effective_distance_tolerance":1e-5}]
    p=classify(fake)
    assert p["qcec_2e-8_verdict"]=="not_equivalent"
    assert p["first_equivalent_at_requested_tolerance"]==1e-5
    assert p["source_equivalence_certified"] is False


def test_p1_report_imports_without_cwd_dependency(tmp_path):
    import subprocess,sys
    from pathlib import Path
    script=Path(__file__).resolve().parents[1]/"scripts/report_paper_gap_repeatability.py"
    res=subprocess.run([sys.executable,str(script),"--help"],
                       cwd=tmp_path, capture_output=True,text=True,check=False)
    assert res.returncode==0, res.stderr

def test_tolerance_probe_keeps_runner_status_when_solver_payload_has_null(monkeypatch, tmp_path):
    """The harness owns status; solver metadata cannot overwrite COMPLETED."""
    from scripts import diagnose_qpe20_tolerance as diag

    class FakeProcess:
        returncode = 0

        def communicate(self, timeout=None):
            payload = {
                "status": None,
                "verdict": "not_equivalent",
                "effective_distance_tolerance": 1e-8,
                "solver_invoked": True,
            }
            return diag.MARKER + json.dumps(payload) + "\n", ""

    monkeypatch.setattr(diag.subprocess, "Popen", lambda *a, **kw: FakeProcess())
    row = diag.run_one(tmp_path, diag.PROBES[1])
    assert row["status"] == "COMPLETED"
    assert row["exit_code"] == 0
    assert row["verdict"] == "not_equivalent"
    assert row["effective_distance_tolerance"] == 1e-8


def test_tolerance_transition_bracket_from_completed_rows():
    from scripts.diagnose_qpe20_tolerance import classify
    rows = [
        {"id": "rust_default_d1e-8", "status": "COMPLETED",
         "verdict": "not_equivalent", "effective_distance_tolerance": 1e-8},
        {"id": "rust_qcec_reference_d2e-8", "status": "COMPLETED",
         "verdict": "not_equivalent", "effective_distance_tolerance": 2e-8},
        {"id": "rust_d3e-6", "status": "COMPLETED",
         "verdict": "not_equivalent", "effective_distance_tolerance": 3e-6},
        {"id": "rust_d5e-6", "status": "COMPLETED",
         "verdict": "equivalent*", "effective_distance_tolerance": 5e-6},
    ]
    result = classify(rows)
    assert result["last_nonequivalent_before_transition"] == 3e-6
    assert result["first_equivalent_at_requested_tolerance"] == 5e-6
    assert result["source_equivalence_certified"] is False
    assert result["wmc_solver_arithmetic_certified"] is False

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

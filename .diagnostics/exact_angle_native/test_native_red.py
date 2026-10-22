"""exact-source-angle strict RED: actual Rust native false negatives from valid QASM.

Run explicitly, outside pytest's testpaths=['test']:
python -m pytest -q .diagnostics/exact_angle_native/test_native_red.py

Do not mark expected failures xfail/skip, relax phase tolerances, invoke WMC
in lieu of Reduction, or merge as a green correctness test.
"""
from pathlib import Path
import hashlib
import os

import numpy as np
import pytest
from qiskit import qasm2
from qiskit.quantum_info import Operator
from QuPRS import _pathsum_rust


QASM_HEADER = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
QPE = (
    "benchmarks/MQTBench/qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
    "benchmarks/MQTBench/h,ry,rz,cx/qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
)
QPE_SHA256 = (
    "8d514d06f7c9e81abda1042796cc34227624c9ed66097bee1ce5e97a87884dda",
    "227ab45a4eb033889aa57bb53e54938e74d757fea30eaa3d276b495048dc6141",
)
A = "-2.5802058126763807"
TWICE_A = "-5.1604116253527614"
C = "1.6198837120072371"
C_PLUS_A = "-0.9603221006691436"


def rz(*angles):
    return QASM_HEADER + "".join(f"rz({angle}) q[0];\n" for angle in angles)


def qpe():
    lhs, rhs = (Path(p) for p in QPE)
    hashes = tuple(hashlib.sha256(p.read_bytes()).hexdigest() for p in (lhs, rhs))
    assert hashes == QPE_SHA256, "The original QPEexact8 fixtures changed"
    return lhs.read_text(), rhs.read_text()


def unitary_oracle(lhs, rhs):
    u = Operator(qasm2.loads(lhs)).data
    v = Operator(qasm2.loads(rhs)).data
    assert u.shape == v.shape
    overlap = np.vdot(v.reshape(-1), u.reshape(-1))
    # Orthogonal unitaries are provably not globally phase equivalent.
    phase = overlap / abs(overlap) if abs(overlap) > 1e-14 else 1.0 + 0.0j
    residual = float(np.max(np.abs(u - phase * v)))
    return residual


@pytest.fixture(autouse=True)
def disable_unrelated_diagnostics(monkeypatch):
    monkeypatch.setenv("QUPRS_STAGE_LEDGER", "1")
    monkeypatch.delenv("QUPRS_OTHER_RULE_TIMING", raising=False)
    monkeypatch.delenv("QUPRS_ELIM_TIMING", raising=False)
    monkeypatch.delenv("QUPRS_FFI_PHASE_TIMING", raising=False)


@pytest.mark.parametrize("method", ["reduction_rules", "hybrid"])
@pytest.mark.parametrize("strategy", ["Naive", "Proportional"])
@pytest.mark.parametrize("case", ["rz_double", "rz_cross", "qpeexact8"])
def test_qoo134_native_equivalent_up_to_phase_red(case, method, strategy):
    if case == "rz_double":
        lhs, rhs = rz(A, A), rz(TWICE_A)
    elif case == "rz_cross":
        lhs, rhs = rz(C, A), rz(C_PLUS_A)
    else:
        lhs, rhs = qpe()
    discrepancy = unitary_oracle(lhs, rhs)
    assert discrepancy < 1e-9, f"Not genuinely unitary-equivalent: {discrepancy}"

    # The actual Reduction/Hybrid native branch must solve this without an
    # unsound near-identity WMC fallback (QOO-136 remains separate).
    result = _pathsum_rust.check_equivalence(
        lhs, rhs, method=method, strategy=strategy, tool_name="gpmc", timeout=30,
    )
    ledger = result["stage_ledger"]
    assert ledger["solver_child_spawns"] == 0, "Regression must isolate pre-WMC"
    assert result["status"] in {
        "Equivalent", "Equivalent (Up to Global Phase)"
    }, (
        f"exact-source-angle real Rust false negative: case={case}, method={method}, "
        f"strategy={strategy}, status={result['status']}, "
        f"source_unitary_error={discrepancy}, final_ps={result['final_ps']}"
    )


@pytest.mark.parametrize("method", ["reduction_rules", "hybrid"])
@pytest.mark.parametrize("strategy", ["Naive", "Proportional"])
@pytest.mark.parametrize("case", ["exact_symbolic_pi", "inequivalent_rz", "inequivalent_x"])
def test_native_control_semantics_remain_green(case, method, strategy):
    if case == "exact_symbolic_pi":
        lhs, rhs = rz("pi/8", "pi/8"), rz("pi/4")
        expected_equivalent = True
    elif case == "inequivalent_rz":
        lhs, rhs = rz("0.125"), rz("0.126")
        expected_equivalent = False
    else:
        lhs, rhs = QASM_HEADER, QASM_HEADER + "x q[0];\n"
        expected_equivalent = False

    residual = unitary_oracle(lhs, rhs)
    assert (residual < 1e-9) == expected_equivalent
    result = _pathsum_rust.check_equivalence(
        lhs, rhs, method=method, strategy=strategy, tool_name="gpmc", timeout=30,
    )
    expected = ({"Equivalent", "Equivalent (Up to Global Phase)"}
                if expected_equivalent else {"Not Equivalent"})
    assert result["status"] in expected, (
        f"Control changed: {case}, {method}, {strategy}, {result['status']}"
    )

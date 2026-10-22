"""Strict source-exact RED: distinguish true 1Q positives from certified QPE negative.

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
def test_native_source_exact_contract_red(case, method, strategy):
    if case == "rz_double":
        lhs, rhs = rz(A, A), rz(TWICE_A)
    elif case == "rz_cross":
        lhs, rhs = rz(C, A), rz(C_PLUS_A)
    else:
        lhs, rhs = qpe()
    discrepancy = unitary_oracle(lhs, rhs)
    # This is a *float-rounded diagnostic*, not an exact equality oracle.
    # Pinned Arb source-ball witnesses prove both QPE and Graphstate literal
    # QASM pairs are NOT exactly equivalent modulo global phase.
    assert discrepancy < 1e-9, f"Qiskit numeric baseline changed: {discrepancy}"

    # The actual Reduction/Hybrid native branch must solve this without an
    # unsound near-identity WMC fallback (QOO-136 remains separate).
    result = _pathsum_rust.check_equivalence(
        lhs, rhs, method=method, strategy=strategy, tool_name="gpmc", timeout=30,
    )
    ledger = result["stage_ledger"]
    if case == "qpeexact8":
        # Certified nonzero projective minor from original SOURCE QASM at
        # 256-bit Arb precision: workflow qpe-source-ball-witness.yml.
        # Native Unknown is fail-closed, but still INCOMPLETE; don't label
        # it a false negative or manufacture an Equivalent result.
        assert result["status"] == "Not Equivalent", (
            f"Source-exact QPE non-equivalence certificate is not implemented "
            f"in native Rust: method={method}, strategy={strategy}, "
            f"status={result['status']}, numeric_residual={discrepancy}"
        )
    else:
        # Valid exact source-decimal additivity must reduce without WMC.
        assert ledger["solver_child_spawns"] == 0, "Exact 1Q proof must isolate pre-WMC"
        assert result["status"] in {
            "Equivalent", "Equivalent (Up to Global Phase)"
        }, (
            f"Exact 1Q source equality regressed: {case}, {method}, {strategy}, "
            f"{result['status']}, qiskit_numeric_residual={discrepancy}"
        )


@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
@pytest.mark.parametrize("delta", ["0.001", "0.000001"])
def test_native_wmc_near_unity_is_not_exact_proof(solver, delta):
    # Real native solver calls, not monkeypatched counts. A count printed
    # close to one is never an equivalence certificate.
    result = _pathsum_rust.check_equivalence(
        QASM_HEADER, rz(delta), method="wmc_only", strategy="Naive",
        tool_name=solver, timeout=30,
    )
    assert result["status"] == "Unknown", (solver, delta, result["status"])
    assert result.get("wmc_solver_time_sec") is not None


@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
@pytest.mark.parametrize("strategy", ["Naive", "Proportional"])
def test_native_qpe_hybrid_does_not_manufacture_equivalence(solver, strategy):
    lhs, rhs = qpe()
    result = _pathsum_rust.check_equivalence(
        lhs, rhs, method="hybrid", strategy=strategy,
        tool_name=solver, timeout=30,
    )
    # The independent Arb source proof is negative. A full native negative
    # certificate is still missing, so Unknown is sound but incomplete.
    assert result["status"] in {"Unknown", "Not Equivalent"}, (
        solver, strategy, result["status"],
    )


GRAPH = (
    "benchmarks/MQTBench/graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
    "benchmarks/MQTBench/h,ry,rz,cx/graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
)
GRAPH_SHA256 = (
    "cf068868f970e553ac9a8fb4998c7c2a6a2e3e6e7a437e3a636f477e34682e36",
    "d2c38d1663dc26757ecb09748918be41c0064cc67bc52d4d7c1c2dfc3fbdd1c9",
)


@pytest.mark.parametrize("method", ["reduction_rules", "hybrid"])
@pytest.mark.parametrize("solver", ["gpmc", "ganak"])
def test_graphstate_source_exact_negative(solver, method):
    # Full 16Q Arb ball proof: graph-source-ball-witness.yml, input 0,
    # outputs 0 and 8, certified nonzero projective minor.
    files = tuple(Path(p) for p in GRAPH)
    hashes = tuple(hashlib.sha256(p.read_bytes()).hexdigest() for p in files)
    assert hashes == GRAPH_SHA256
    lhs, rhs = (p.read_text() for p in files)
    result = _pathsum_rust.check_equivalence(
        lhs, rhs, method=method, strategy="Naive",
        tool_name=solver, timeout=30,
    )
    assert result["stage_ledger"]["solver_child_spawns"] == 0
    assert result["status"] == "Not Equivalent", (
        "Exact-source 16Q result must not be relabeled equivalent due to "
        f"rounded-Qiskit acceptance: {solver}, {method}, {result['status']}"
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

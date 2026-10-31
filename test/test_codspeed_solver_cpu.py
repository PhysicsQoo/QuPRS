"""Solver-inclusive CodSpeed CPU experiments (v1 pilot).

These IDs are intentionally distinct from legacy host-only `test_MQT.py`
Simulation results. They MUST run with simulation-track-subprocess=true.
No baseline comparison is valid until coverage and invocation are proven.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from QuPRS import check_equivalence

ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "MQTBench"
POSITIVE = {"equivalent", "equivalent*"}

# id, fixture, reduction strategy, reverse inputs, solver, backend.
# Diverse cases deliberately avoid making Graphstate16's variable RR/WMC
# path into a supposedly fixed solver benchmark.
CASES = (
    ("vqe4-gpmc-rust", "vqe_nativegates_ibm_qiskit_opt0_4.qasm",
     "proportional", False, "gpmc", "rust"),
    ("vqe4-gpmc-python", "vqe_nativegates_ibm_qiskit_opt0_4.qasm",
     "proportional", False, "gpmc", "python"),
    ("grover4-gpmc-rust", "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
     "proportional", True, "gpmc", "rust"),
    ("qft16-gpmc-rust", "qft_nativegates_ibm_qiskit_opt0_16.qasm",
     "proportional", True, "gpmc", "rust"),
    ("qft16-ganak-rust", "qft_nativegates_ibm_qiskit_opt0_16.qasm",
     "proportional", True, "ganak", "rust"),
    ("qaoa7-gpmc-rust", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
     "proportional", False, "gpmc", "rust"),
    ("qaoa7-ganak-python", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
     "proportional", False, "ganak", "python"),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "case_id,filename,strategy,reverse,solver,backend",
    CASES,
    ids=[case[0] for case in CASES],
)
def test_solver_cpu_inclusive(
    benchmark, case_id, filename, strategy, reverse, solver, backend
):
    """Hybrid source-pinned verification, including its external Solver CPU."""
    lhs = ROOT / filename
    rhs = ROOT / "h,ry,rz,cx" / filename
    assert lhs.is_file() and rhs.is_file(), filename
    input_hashes = (_sha256(lhs), _sha256(rhs))
    if reverse:
        lhs, rhs = rhs, lhs

    # Any oracle, manifest or SHA calculation stays OUTSIDE the timed call.
    result = benchmark(
        check_equivalence,
        str(lhs),
        str(rhs),
        method="hybrid",
        strategy=strategy,
        tool_name=solver,
        backend=backend,
        # Solver-inclusive Simulation instruments GPMC/Ganak under Valgrind.
        # Its actual elapsed time can greatly exceed native execution time.
        # Bound the two observed instrumentation-timeout cases separately;
        # do not use this limit to certify uninstrumented WallTime behavior.
        timeout=300 if case_id in {
            "qft16-gpmc-rust", "qaoa7-ganak-python"
        } else 120,
    )
    verdict = str(result.equivalent)
    invoked = bool(result.wmc_solver_invoked)
    benchmark.extra_info.update({
        "measurement_contract": "solver-inclusive-simulation-v1",
        "case_id": case_id,
        "backend": backend,
        "method": "hybrid",
        "solver": solver,
        "strategy": strategy,
        "reverse": str(reverse),
        "qasm_sha256": ",".join(input_hashes),
        "solver_invoked": str(invoked),
        "verdict": verdict,
        "rr_approximate": str(result.rr_approximate),
        "precision_reason": str(result.wmc_precision_reason),
    })

    # A path that terminates in RR is NOT a Solver CPU benchmark.
    # Never turn missing solver invocations into a zero-duration success.
    assert invoked, (case_id, "Expected external WMC solver invocation", verdict)
    # These QASM pairs are source-pinned positive controls. A false negative,
    # an unknown verdict or a solver format error is a correctness failure,
    # not a performance PASS.
    assert verdict in POSITIVE, (case_id, verdict)

"""Bounded REAL-SOLVER experimental candidate-default distance sweep.

Research-only calibration: no production solver retries. JUnit properties
record actual Python/Rust, GPMC/Ganak outcomes and evidence for offline audit.
Do not read an equiv result as a source-exact certificate.
"""
import math
from pathlib import Path

import pytest

from QuPRS import check_equivalence


ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "MQTBench"
QASM = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
EPSILONS = (1e-4, math.sqrt(2e-8 - 1e-16), 2e-4)
CASES = (
    "h60", "h80", "rz_0.00010", "rz_0.00020",
    "rz_0.00032", "rz_0.00048",
)
GRID = [(case, eps) for case in CASES for eps in EPSILONS]
GRID += [
    ("graphstate16", EPSILONS[1]),
    ("qft16", EPSILONS[1]),
]


def circuit_pair(case):
    if case.startswith("h"):
        return QASM, QASM + "h q[0];\n" * int(case[1:]), "exact_identity", 0.0, "wmc_only", "Naive"
    if case.startswith("rz_"):
        theta = float(case[3:])
        return (QASM, QASM + f"rz({theta}) q[0];\n",
                "strict_nonidentical", abs(math.sin(theta / 2)),
                "wmc_only", "Naive")
    if case == "graphstate16":
        file = "graphstate_nativegates_ibm_qiskit_opt0_16.qasm"
        return (str(ROOT / file), str(ROOT / "h,ry,rz,cx" / file),
                "source_pinned_approximate", 2.143e-15,
                "hybrid", "Naive")
    if case == "qft16":
        file = "qft_nativegates_ibm_qiskit_opt0_16.qasm"
        return (str(ROOT / "h,ry,rz,cx" / file), str(ROOT / file),
                "paper_intended_equivalence", None, "hybrid", "proportional")
    raise AssertionError(case)


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("solver", ("gpmc", "ganak"))
@pytest.mark.parametrize("case,epsilon", GRID)
def test_real_solver_distance_default_calibration(
    backend, solver, case, epsilon, record_property,
):
    a, b, truth, distance, method, strategy = circuit_pair(case)
    result = check_equivalence(
        a, b, backend=backend, method=method, strategy=strategy,
        tool_name=solver, timeout=75,
        approximate_distance_tolerance=epsilon,
    )
    expected = "reference_oracle_unavailable"
    if distance is not None:
        if abs(distance - epsilon) < 2e-8:
            expected = "within_numerical_boundary"
        else:
            expected = ("within_distance" if distance < epsilon
                        else "outside_distance")
    for key, val in (
        ("calibration_case", case),
        ("calibration_backend", backend),
        ("calibration_solver", solver),
        ("calibration_distance_epsilon", format(epsilon, ".17g")),
        ("calibration_truth", truth),
        ("calibration_oracle_distance", str(distance)),
        ("calibration_expected_range", expected),
        ("calibration_verdict", result.equivalent),
        ("calibration_wmc_invoked", result.wmc_solver_invoked),
        ("calibration_wmc_time", result.wmc_time),
        ("calibration_precision_reason", result.wmc_precision_reason),
        ("calibration_printed_verdict", result.wmc_printed_verdict),
    ):
        record_property(key, str(val))
    assert result.equivalent in (
        "equivalent", "equivalent*", "not_equivalent", "unknown",
    ), (case, backend, solver, epsilon, result.equivalent)
    # Definitive contrary labels are unsafe relative to independent
    # analytical 1-qubit projective-distance oracle, not merely uncertain.
    if expected == "outside_distance":
        assert result.equivalent not in ("equivalent", "equivalent*"), (
            case, backend, solver, epsilon, result.equivalent,
        )
    if expected == "within_distance":
        assert result.equivalent != "not_equivalent", (
            case, backend, solver, epsilon, result.equivalent,
        )

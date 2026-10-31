"""Python/Rust RR tolerance and reduction-result parity on pinned QASM inputs.

These controls use public APIs and do not invoke WMC to conceal divergent
reduction behavior. The source-exact/non-exact distinction is intentional.
"""
from pathlib import Path

import pytest

from QuPRS import check_equivalence


_IDENTITY = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
"""


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize(
    "angle,epsilon,expected",
    (
        ("0.00000000002", 1e-10, "equivalent"),
        ("0.00000000002", 1e-12, "not_equivalent"),
        ("0.00001", 1e-10, "not_equivalent"),
        ("0", 0, "equivalent"),
        ("0.00000000002", 0, "not_equivalent"),
    ),
)
def test_rr_tolerance_parity_for_exact_qasm_decimals(backend, angle, epsilon, expected):
    rotated = _IDENTITY + f"rz({angle}) q[0];\n"
    result = check_equivalence(
        _IDENTITY, rotated,
        method="reduction_rules", strategy="Naive",
        tool_name="gpmc", backend=backend, timeout=30,
        rr_tolerance=epsilon,
    )
    assert result.equivalent == expected, (backend, angle, epsilon, result.equivalent)
    assert result.wmc_solver_invoked is False
    assert result.tool_time is None
    if expected == "equivalent":
        assert result.rr_approximate is True, (
            "Nonzero exact source-angle residual must be reported as approximate",
            backend, angle,
        )


_ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "MQTBench"
_GRAPH_LEFT = _ROOT / "graphstate_nativegates_ibm_qiskit_opt0_16.qasm"
_GRAPH_RIGHT = _ROOT / "h,ry,rz,cx" / "graphstate_nativegates_ibm_qiskit_opt0_16.qasm"


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_graphstate16_rr_approximate_parity_without_solver(backend):
    from test_graphstate16_source_contract import independent_source_contract
    independent_source_contract()  # exact QASM bytes and decomposition identity

    result = check_equivalence(
        str(_GRAPH_LEFT), str(_GRAPH_RIGHT),
        method="reduction_rules", strategy="Naive",
        tool_name="gpmc", backend=backend, timeout=90,
        rr_tolerance=1e-10,
    )
    assert result.equivalent in ("equivalent", "equivalent*"), (
        backend, result.equivalent,
    )
    assert result.rr_approximate is True, backend
    assert result.wmc_solver_invoked is False
    assert result.tool_time is None

"""Python/Rust RR tolerance and reduction-result parity on pinned QASM inputs.

These controls use public APIs to check RR decisions and explicit residual
handoff to the real WMC solver. The source-exact/non-exact distinction
is intentional.
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
        assert result.rr_approximate is (angle != "0"), (
            "Only a nonzero source-angle residual needs an approximate RR match",
            backend, angle,
        )


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_rr_approximation_is_independent_of_global_phase_label(backend):
    rotated = _IDENTITY + "rz(0.000000001) q[0];\n"
    result = check_equivalence(
        _IDENTITY, rotated,
        method="reduction_rules", strategy="Naive",
        backend=backend, rr_tolerance=1e-8,
        phase_tolerance=1e-12,
    )
    assert result.equivalent == "equivalent*"
    assert result.rr_approximate is True
    assert result.wmc_solver_invoked is False


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


_TWO_QUBIT_IDENTITY = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
"""
# The first small rotation is removed by tolerant RR; the second survives,
# so RR alone cannot establish equivalence and Hybrid must invoke WMC.
_TWO_QUBIT_RESIDUAL = (
    _TWO_QUBIT_IDENTITY
    + "rz(0.000000001) q[0];\n"
    + "rz(0.5) q[1];\n"
)


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("rr_tolerance", (0, 1e-8))
def test_hybrid_wmc_consumes_rr_residual_like_python(backend, rr_tolerance):
    common = dict(
        backend=backend, strategy="Naive", tool_name="gpmc",
        timeout=60, rr_tolerance=rr_tolerance,
        approximate_distance_tolerance=1e-8,
    )
    rr_only = check_equivalence(
        _TWO_QUBIT_IDENTITY, _TWO_QUBIT_RESIDUAL,
        method="reduction_rules", **common,
    )
    hybrid = check_equivalence(
        _TWO_QUBIT_IDENTITY, _TWO_QUBIT_RESIDUAL,
        method="hybrid", **common,
    )
    assert rr_only.equivalent == "not_equivalent"
    assert rr_only.wmc_solver_invoked is False
    assert hybrid.equivalent == "not_equivalent"
    assert hybrid.wmc_solver_invoked is True
    # An inconclusive approximated RR result may require an on-demand
    # strict replay solely to preserve WMC's original-source distance.
    strict_rr = check_equivalence(
        _TWO_QUBIT_IDENTITY, _TWO_QUBIT_RESIDUAL,
        method="reduction_rules", **{**common, "rr_tolerance": 0},
    )
    assert hybrid.final_pathsum == strict_rr.final_pathsum
    # Match Python's public result: once WMC provides the result, the
    # rr_approximate flag does not claim that RR proved equivalence.
    assert hybrid.rr_approximate is False


def test_rust_hybrid_reconstructs_faithful_wmc_residual_if_needed(monkeypatch):
    from QuPRS import _pathsum_rust

    monkeypatch.setenv("QUPRS_STAGE_LEDGER", "1")

    def run(method, rr_tolerance):
        return _pathsum_rust.check_equivalence(
            _TWO_QUBIT_IDENTITY, _TWO_QUBIT_RESIDUAL,
            method=method, strategy="Naive", tool_name="gpmc",
            timeout=60, rr_tolerance=rr_tolerance,
            approximate_distance_tolerance=1e-8,
        )

    # Raw native FFI does not set Python's packaged Solver override.
    # Resolve the wheel's actual native binary within its resource lifetime,
    # so isolated Docker runtime and normal CI validate the same Solver.
    from QuPRS.utils import WMC
    with WMC("gpmc") as solver_binary:
        assert solver_binary.is_file()
        monkeypatch.setenv("QUPRS_GPMC_PATH", str(solver_binary))
        strict_rr = run("reduction_rules", 0)
        tolerant_rr = run("reduction_rules", 1e-8)
        tolerant_hybrid = run("hybrid", 1e-8)

    # The approximate rule must actually have changed the residual. Merely
    # comparing two runs where RR did no work would not detect a replay.
    assert strict_rr["final_ps"] != tolerant_rr["final_ps"]
    assert tolerant_hybrid["final_ps"] == strict_rr["final_ps"]
    assert tolerant_hybrid["final_ps"] != tolerant_rr["final_ps"]
    assert tolerant_hybrid["wmc_solver_invoked"] is True
    assert tolerant_hybrid["rr_approximate"] is False
    assert tolerant_hybrid["rr_residual_approximate"] is False
    assert strict_rr["rr_residual_approximate"] is False
    # The RR proof followed the tolerant path; only the WMC residual
    # is reconstructed strictly after RR could not decide.
    assert tolerant_hybrid["stage_ledger"]["stage_calls"].get("reduction", 0) >= 1


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("angle", ("0", "0.00000000002"))
def test_hybrid_and_rr_only_use_the_same_decisive_rr(backend, angle):
    """A tolerant RR proof must not change with the fallback method."""
    source = _IDENTITY + f"rz({angle}) q[0];\nh q[0];\nh q[0];\n"
    options = dict(
        backend=backend, strategy="Naive", tool_name="gpmc",
        rr_tolerance=1e-8, phase_tolerance=1e-8, timeout=45,
    )
    rr = check_equivalence(
        _IDENTITY, source, method="reduction_rules", **options
    )
    hybrid = check_equivalence(
        _IDENTITY, source, method="hybrid", **options
    )
    assert rr.equivalent == hybrid.equivalent == "equivalent"
    assert rr.rr_approximate == hybrid.rr_approximate == (angle != "0")
    assert rr.final_pathsum == hybrid.final_pathsum
    assert rr.wmc_solver_invoked is hybrid.wmc_solver_invoked is False

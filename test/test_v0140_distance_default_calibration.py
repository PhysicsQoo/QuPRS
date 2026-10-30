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


# QCEC's opt-in approximate distance threshold is 1e-8. The following
# tests enforce that QuPRS never accepts an analytically inequivalent
# one-qubit rotation at that threshold merely because the WMC count
# rounds to the identity. An unresolved solver count remains unknown
# rather than being converted to a false positive.
@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("solver", ("gpmc", "ganak"))
@pytest.mark.parametrize("angle", (0.00010, 0.00020, 2.5e-8))
def test_qcec_scale_distance_never_accepts_known_outside_rotation(
    backend, solver, angle, record_property,
):
    # For U=I, V=Rz(theta), D_proj=abs(sin(theta/2)), all cases
    # are strictly outside 1e-8.
    distance = abs(math.sin(angle / 2))
    assert distance > 1e-8
    a, b = QASM, QASM + f"rz({angle:.17g}) q[0];\n"
    result = check_equivalence(
        a, b, backend=backend, method="wmc_only",
        strategy="Naive", tool_name=solver, timeout=45,
        approximate_distance_tolerance=1e-8,
    )
    for key, value in (
        ("qcec_scale_angle", angle),
        ("qcec_scale_distance", distance),
        ("qcec_scale_solver", solver),
        ("qcec_scale_backend", backend),
        ("qcec_scale_verdict", result.equivalent),
        ("qcec_scale_reason", result.wmc_precision_reason),
    ):
        record_property(key, str(value))
    assert result.wmc_solver_invoked is True
    assert result.equivalent in ("not_equivalent", "unknown"), (
        backend, solver, angle, distance, result.equivalent,
        result.wmc_precision_reason,
    )


def test_ganak_mpfr_mode6_print_precision_probe(tmp_path, record_property):
    """Research-only: determine whether the bundled Ganak prints enough digits.

    This does NOT change the production CLI or rerun production WMC.
    A forced one-variable complex weight has true magnitude 1-5e-17.
    The difference is at the scale required for projective D≈1e-8.
    """
    from QuPRS.utils import WMC
    from QuPRS.utils.solver_process import run
    from QuPRS.utils.precision_count import parse_printed_solver_output
    from fractions import Fraction

    cnf = tmp_path / "precision-probe.cnf"
    cnf.write_text(
        "p cnf 1 1\nc t wmc\n"
        "c p weight 1 0.99999999999999995 + 0.0i 0\n"
        "c p weight -1 1.0 + 0.0i 0\n"
        "1 0\n"
    )
    with WMC("ganak") as exe:
        observed = run(
            [str(exe), "--mode=6", "--mpfrprec", "256", str(cnf)],
            timeout=25,
        )
    record_property("ganak_probe_returncode", str(observed.returncode))
    record_property("ganak_probe_count_line", "|".join(
        line for line in observed.stdout.splitlines()
        if line.startswith("c s exact ")
    )[:1000])
    if observed.returncode:
        pytest.skip("Bundled Ganak did not accept --mpfrprec 256: "
                    + observed.stderr[-220:])
    count = parse_printed_solver_output(observed.stdout)
    # No asserted minimum precision: the purpose is to measure how
    # much of the configured MPFR internal precision reaches stdout.
    record_property("ganak_probe_real_count", str(count.real))
    record_property("ganak_probe_real_print_half_unit",
                    str(count.real_print_half_unit))
    record_property("ganak_probe_can_resolve_5e-17",
                    str(count.real_print_half_unit < Fraction(5, 10**17)))
    assert count.real > 0

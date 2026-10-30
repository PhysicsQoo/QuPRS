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


# Targeted positive-side feasibility gate for QCEC-scale projective distance.
# This is evidence gathering, not a release-default change or solver patch.
# Run one GPMC solve per verification; RR-first can resolve without WMC.
@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("case", ("h60", "h80", "graphstate16", "qft16"))
def test_gpmc_qcec_scale_positive_controls(backend, case, record_property, monkeypatch, tmp_path):
    left, right, truth, oracle_distance, method, strategy = circuit_pair(case)
    epsilon = 1e-8
    # Experimental observation: the public Rust bridge resolves the solver
    # through QuPRS.utils.WMC and overwrites QUPRS_GPMC_PATH. Patch that
    # RESOURCE RESOLVER instead of setting an environment variable that
    # the public bridge immediately overwrites.
    native_cnf_capture = None
    if backend == "rust" and case in ("graphstate16", "qft16"):
        import os
        if os.name == "posix":
            from contextlib import contextmanager
            from QuPRS.utils import WMC as packaged_wmc

            with packaged_wmc("gpmc") as executable:
                original_executable = str(Path(executable).resolve())
                assert Path(original_executable).is_file()
            native_cnf_capture = tmp_path / "native-source-weights.cnf"
            wrapper = tmp_path / "gpmc-cnf-observer.sh"
            wrapper.write_text(
                '#!/bin/sh\n'
                'for last do :; done\n'
                'cp "$last" "$QUPRS_EXPERIMENT_CNF"\n'
                'exec "$QUPRS_EXPERIMENT_GPMC" "$@"\n'
            )
            wrapper.chmod(0o700)
            monkeypatch.setenv("QUPRS_EXPERIMENT_CNF", str(native_cnf_capture))
            monkeypatch.setenv("QUPRS_EXPERIMENT_GPMC", original_executable)

            @contextmanager
            def instrumented_wmc(name):
                assert name == "gpmc"
                yield wrapper

            monkeypatch.setattr("QuPRS.utils.WMC", instrumented_wmc)
    # Capture the *same* external solver count from the public Python path.
    # Do not invoke GPMC again to produce diagnostic evidence.
    captured = []
    if backend == "python":
        import QuPRS.interface.ps2wmc as ps2wmc
        real_run_wmc = ps2wmc.run_wmc

        def capturing_run_wmc(*args, **kwargs):
            answer = real_run_wmc(*args, **kwargs)
            if kwargs.get("preserve_count"):
                captured.append(answer)
            return answer

        monkeypatch.setattr(ps2wmc, "run_wmc", capturing_run_wmc)
    result = check_equivalence(
        left, right,
        backend=backend,
        method=method,
        strategy=strategy,
        tool_name="gpmc",
        timeout=75,
        approximate_distance_tolerance=epsilon,
    )
    for key, value in (
        ("gpmc_qcec_positive_case", case),
        ("gpmc_qcec_positive_backend", backend),
        ("gpmc_qcec_positive_source_label", truth),
        ("gpmc_qcec_positive_oracle_distance", oracle_distance),
        ("gpmc_qcec_positive_result", result.equivalent),
        ("gpmc_qcec_positive_reason", result.wmc_precision_reason),
        ("gpmc_qcec_positive_printed", result.wmc_printed_verdict),
        ("gpmc_qcec_positive_invoked", result.wmc_solver_invoked),
        ("gpmc_qcec_positive_wmc_time", result.wmc_time),
    ):
        record_property(key, str(value))
    if native_cnf_capture is not None:
        assert result.wmc_solver_invoked is True, "WMC must run for this evidence"
        assert native_cnf_capture.is_file(), (
            "Native WMC resource override did not preserve CNF input"
        )
        from decimal import Decimal, localcontext

        positive_weights = []
        with localcontext() as ctx:
            ctx.prec = 90
            for line in native_cnf_capture.read_text().splitlines():
                fields = line.split()
                if (len(fields) == 7 and fields[:3] == ["c", "p", "weight"]
                    and int(fields[3]) > 0):
                    real = Decimal(fields[4])
                    imag = Decimal(fields[5])
                    positive_weights.append(real * real + imag * imag - 1)
        assert positive_weights, "Source phase weights were not captured"
        for key, value in (
            ("native_gpmc_weight_count", len(positive_weights)),
            ("native_gpmc_positive_unit_drift_count", sum(x > 0 for x in positive_weights)),
            ("native_gpmc_negative_unit_drift_count", sum(x < 0 for x in positive_weights)),
            ("native_gpmc_max_unit_drift", format(max(abs(x) for x in positive_weights), ".18e")),
            ("native_gpmc_sum_unit_drift", format(sum(positive_weights), ".18e")),
        ):
            record_property(key, str(value))
    if captured:
        from fractions import Fraction

        assert len(captured) == 1, "single-solver production path invariant"
        raw = captured[0]
        norm_squared = Fraction(2) ** int(round(2 * result.expect))
        normalized_defect = Fraction(1) - (
            raw.real * raw.real + raw.imag * raw.imag
        ) / norm_squared
        scale = max(abs(raw.real), abs(raw.imag))
        relative_print_half_unit = (
            max(raw.real_print_half_unit, raw.imag_print_half_unit) / scale
            if scale else Fraction(0)
        )
        for key, value in (
            ("gpmc_qcec_print_format", raw.format_name),
            ("gpmc_qcec_normalized_defect", format(float(normalized_defect), ".18g")),
            ("gpmc_qcec_relative_print_half_unit",
             format(float(relative_print_half_unit), ".18g")),
            ("gpmc_qcec_real_sign", 0 if raw.real == 0 else (1 if raw.real > 0 else -1)),
            ("gpmc_qcec_imag_sign", 0 if raw.imag == 0 else (1 if raw.imag > 0 else -1)),
        ):
            record_property(key, str(value))
    # Exact identities and the source-pinned Graphstate16 pair are
    # independently within epsilon. QFT16 is a paper-intended positive,
    # not an independent exact-distance certificate.
    # Inconclusive numerical evidence is explicitly retained rather than
    # accepting an unjustified positive at this very tight threshold.
    assert result.equivalent in ("equivalent", "equivalent*", "unknown"), (
        case, backend, result.equivalent, result.wmc_precision_reason,
    )
    if oracle_distance is not None:
        assert oracle_distance < epsilon

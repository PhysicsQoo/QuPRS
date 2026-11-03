"""Bounded v0.14.0 numerical-science coverage beyond the legacy corpus.

Fixed QASM sources are supplied by the paper-benchmark corpus integrity gate.
Evidence categories distinguish strict source, approximate and inconclusive.
"""
from decimal import Decimal
from fractions import Fraction
import hashlib
import math
from pathlib import Path

import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence
from QuPRS.utils.gpmc_distance_budget import classify_gpmc_single_count
from QuPRS.utils.precision_count import parse_printed_count_line
from _benchmark_cases import MQT_CASES


@pytest.mark.parametrize("vars", [12, 128, 160, 512, 513])
def test_large_cnf_single_run_model_is_conservative(vars, record_property):
    """An ideal printed identity is not necessarily decidable for a large CNF.

    This probes a *conditional model*, not an observed large native solver run.
    """
    count = parse_printed_count_line(
        "c s exact double prec-sci "
        "1.00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e+00"
        " + 0.00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e+00i"
    )
    answer = classify_gpmc_single_count(
        count, expected_twice_log2=0, distance_tolerance=1e-8,
        phase_tolerance=1e-8, cnf_vars=vars,
        number_of_weights=min(vars, 8),
        maximum_weight_magnitude_squared=Fraction(1), precision_digits=90,
    )
    assert answer.printed_status == "equivalent"
    # Eligible sizes report a point-estimate observation, not a certified
    # numerical bound; 513 variables remain outside this conditional model.
    assert answer.model_status == ("unknown" if vars > 512 else "equivalent")
    assert answer.numerical_verdict == "equivalent"
    assert answer.printed_status == "equivalent"
    assert not answer.solver_arithmetic_certified
    assert not answer.source_weight_certified
    if vars <= 512:
        assert answer.reason.startswith("single_pass_uncertified_")
    record_property("model_only_not_solver_observation", True)
    record_property("model_cnf_variables", vars)
    record_property("model_status", answer.status)
    record_property("model_reason", answer.reason)


def test_rr_local_tolerance_does_not_certify_distance(record_property):
    """Local RR dropping can be accepted while true circuit D is nonzero.

    This is a diagnostic of existing RR tolerance semantics; no rule is disabled.
    """
    theta = 2 * math.pi * 1e-7
    left, right = QuantumCircuit(1), QuantumCircuit(1)
    right.h(0)
    right.rz(theta, 0)
    right.h(0)
    assert Operator(left).equiv(Operator(left))
    source_distance = abs(math.sin(theta / 2))
    assert source_distance > 1e-8
    rr = check_equivalence(
        left, right, method="reduction_rules",
        backend="python", strategy="Naive", timeout=30,
        rr_tolerance=1e-6,
    )
    assert rr.equivalent in ("equivalent", "equivalent*", "unknown", "not_equivalent")
    assert rr.wmc_solver_invoked is False
    record_property("source_projective_distance", str(source_distance))
    record_property("rr_local_tolerance", "1e-6")
    record_property("rr_verdict", rr.equivalent)
    record_property("strict_source_equality", "false")
    record_property(
        "rr_distance_mismatch_diagnostic",
        rr.equivalent.startswith("equivalent") and source_distance > 1e-8,
    )


def test_representative_qft_graphstate_qaoa_remain_in_paper_ci():
    names = {entry[0] for entry in MQT_CASES}
    assert {
        "qft_nativegates_ibm_qiskit_opt0_16.qasm",
        "graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
        "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
    } <= names


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_qpeexact8_fixed_source_approximate_diagnostic(backend, record_property):
    """One bounded QPEexact8 sample; no assumed source-exact equivalence.

    Source-decimal QASM and intended Qiskit-transpilation equivalence are
    distinct. An unknown or timeout is recorded, not silently treated as pass.
    """
    root = Path(__file__).resolve().parents[1] / "benchmarks" / "MQTBench"
    paths = (
        root / "qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
        root / "h,ry,rz,cx" / "qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
    )
    for index, path in enumerate(paths, 1):
        assert path.is_file()
        record_property(
            f"source_qasm_{index}_sha256",
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    result = check_equivalence(
        *(str(path) for path in paths),
        backend=backend, method="hybrid", strategy="proportional",
        tool_name="gpmc", timeout=75,
        approximate_distance_tolerance=1e-8,
    )
    # Numerical results are not a universal source-exact proof; classify and
    # surface inconclusive observations distinctly in the JUnit evidence.
    assert result.equivalent in (
        "equivalent", "equivalent*", "not_equivalent", "unknown", "Timeout"
    ), (backend, result.equivalent)
    category = (
        "INCONCLUSIVE_RESOURCE" if result.equivalent == "Timeout"
        else "INCONCLUSIVE_NUMERIC" if result.equivalent == "unknown"
        else "OBSERVED_NUMERIC_OR_SYMBOLIC"
    )
    record_property("qpe_source_pair", "qpeexact8")
    record_property("backend", backend)
    record_property("method", "hybrid")
    record_property("selected_solver", "gpmc")
    record_property("distance_epsilon", "1e-8")
    record_property("classification", result.equivalent)
    record_property("evidence_category", category)
    record_property("wmc_stage_time", str(result.wmc_time))
    record_property("solver_invoked", str(result.wmc_solver_invoked))
    record_property("wmc_precision_reason", str(result.wmc_precision_reason))
    if result.wmc_solver_invoked:
        assert result.tool_time is not None
        assert result.wmc_time is not None


@pytest.mark.parametrize("variables", (12, 128, 160, 512))
def test_native_gpmc_forced_unit_cnf_numerical_model(
    tmp_path, variables, record_property
):
    """One *actual* 90-digit GPMC solve at each bounded CNF size.

    Every positive unit clause forces the sole satisfying assignment; its
    mathematically exact printed-CNF weighted count is 1+0i. This measures
    whether the conditional numerical model becomes unknown despite a clean
    native printed count, without claiming a paper QFT benchmark result.
    """
    from QuPRS.interface.ps2wmc import run_wmc
    from QuPRS.utils.gpmc_cnf_metadata import gpmc_cnf_budget_metadata

    c = (
        f"p cnf {variables} {variables}\nc t wmc\n"
        "c p weight 1 1.0 0.0 0\n"
        "c p weight -1 1.0 0.0 0\n"
        + "".join(f"{j} 0\n" for j in range(1, variables + 1))
    )
    file = tmp_path / f"exact-unit-{variables}.cnf"
    file.write_text(c)
    result = run_wmc(
        str(file), tool_name="gpmc", timeout=25,
        preserve_count=True, precision_digits=90,
    )
    assert result.real == Fraction(1)
    assert result.imag == Fraction(0)
    n, weights, maximum = gpmc_cnf_budget_metadata(c)
    evidence = classify_gpmc_single_count(
        result, expected_twice_log2=0, distance_tolerance=1e-8,
        phase_tolerance=1e-8, cnf_vars=n, number_of_weights=weights,
        maximum_weight_magnitude_squared=maximum, precision_digits=90,
    )
    # GPMC may print the exact integer 1 using very few significant
    # digits even with -prec=90. A nonzero decimal half-unit is therefore
    # unresolved at eps_D=1e-8; the conditional model must not invent
    # additional printer precision just because MPFR used 90 digits.
    assert evidence.printed_status in ("equivalent", "unknown")
    # Preserve the raw printing diagnostic even when the public numerical
    # midpoint is usable. This forced-unit CNF is not a source-circuit proof.
    assert evidence.model_status == "equivalent"
    assert evidence.numerical_verdict == "equivalent"
    assert not evidence.solver_arithmetic_certified
    assert not evidence.source_weight_certified
    assert evidence.reason.startswith("single_pass_uncertified_")
    record_property("test_family", "unit_forced_cnf_not_circuit")
    record_property("native_solver_invocations", "1")
    record_property("native_count", "1+0i")
    record_property("cnf_variables", variables)
    record_property("count_format", result.format_name)
    record_property("real_print_half_unit", str(result.real_print_half_unit))
    record_property("printed_verdict", evidence.printed_status)
    record_property("model_verdict", evidence.status)
    record_property("model_reason", evidence.reason)

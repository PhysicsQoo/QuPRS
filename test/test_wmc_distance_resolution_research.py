"""Bounded native WMC projective-distance resolution characterization.

The printed-value interval is not a solver arithmetic certificate. Preserve
original RR tolerance and the final-PathSum Hybrid handoff while inspecting
both the binary64 public classifier and lossless printed-count transport.
"""
from contextlib import contextmanager
from decimal import Decimal
from fractions import Fraction
import json
import math
import os
from pathlib import Path
from unittest.mock import patch

from mpmath import mp
from qiskit import QuantumCircuit

from QuPRS import check_equivalence, config
from QuPRS.interface import ps2wmc
from QuPRS.utils.precision_count import PrintedCount, classify_printed_distance
from QuPRS.utils.wmc_solvers import APPROXIMATE_MAGNITUDE_GUARD

OUT = Path("focused-tolerance-evidence")


@contextmanager
def rr_tolerance(value):
    previous = config.get_tolerance()
    config.set_tolerance(value)
    try:
        yield
    finally:
        config.set_tolerance(previous)


def hsh(extra_rz=0.0):
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.s(0)
    if extra_rz:
        circuit.rz(extra_rz, 0)
    circuit.h(0)
    return circuit


def exact_normalized_ratio_and_defect(theta):
    """Reference the actual binary64 Qiskit gate parameter, not an invented literal."""
    with mp.workdps(110):
        x = mp.mpf(repr(float(theta)))
        ratio = abs(mp.cos(x / 2))
        return {
            "ratio": mp.nstr(ratio, 105),
            "magnitude_defect": mp.nstr(1 - ratio, 105),
            "distance": mp.nstr(abs(mp.sin(x / 2)), 105),
        }


def analyze_native_wmc():
    theta = 2 * math.pi * 1e-7
    left, right = hsh(), hsh(theta)
    rows = []
    errors = []
    exact = exact_normalized_ratio_and_defect(theta)
    for solver in ("gpmc", "ganak"):
        for method in ("hybrid", "wmc_only"):
            raw = []
            incoming = []
            original_run = ps2wmc.run_wmc
            original_dimacs = ps2wmc.to_DIMACS

            def observe_run(file="wmc.cnf", tool_name="gpmc", timeout=600.0, **kwargs):
                value = original_run(
                    file, tool_name, timeout, preserve_count=True,
                    precision_digits=kwargs.get("precision_digits"),
                )
                assert isinstance(value, PrintedCount)
                raw.append(value)
                return value if kwargs.get("preserve_count") else (
                    float(value.real), float(value.imag)
                )

            def observe_dimacs(pathsum, filename="wmc.cnf", tool_name="gpmc"):
                incoming.append(pathsum)
                return original_dimacs(pathsum, filename, tool_name)

            row = {
                "group": "full_circuit_printed_wmc_resolution",
                "method": method,
                "solver": solver,
                "rr_tolerance": 1e-10,
                "distance_tolerance": 1e-8,
                "native_source_sha": os.getenv("GITHUB_SHA"),
                "independent_reference_for_qiskit_f64_source": exact,
                "heuristic_magnitude_guard": APPROXIMATE_MAGNITUDE_GUARD,
                "printed_only_no_solver_arithmetic_certificate": True,
            }
            try:
                with rr_tolerance(1e-10), patch.object(
                    ps2wmc, "run_wmc", side_effect=observe_run
                ), patch.object(
                    ps2wmc, "to_DIMACS", side_effect=observe_dimacs
                ):
                    result = check_equivalence(
                        left, right, backend="python", method=method,
                        strategy="Naive", tool_name=solver, timeout=20,
                        approximate_distance_tolerance=1e-8,
                    )
                assert result.wmc_solver_invoked
                assert len(raw) == (2 if solver == "gpmc" else 1) and len(incoming) == 1
                # The actual final PathSum is the one provided to WMC.
                assert incoming[0] is result.final_pathsum
                assert result.expect is not None
                exponent = int(2 * result.expect)
                assert exponent == 2 * result.expect
                value = raw[-1]
                printed = classify_printed_distance(value, exponent, 1e-8)
                with mp.workdps(110):
                    norm = mp.power(2, mp.mpf(exponent) / 2)
                    rr = mp.mpf(value.real.numerator) / value.real.denominator
                    ii = mp.mpf(value.imag.numerator) / value.imag.denominator
                    magnitude = mp.sqrt(rr * rr + ii * ii) / norm
                    expected = mp.mpf(exact["ratio"])
                    row["printed_normalized_magnitude"] = mp.nstr(magnitude, 105)
                    row["printed_normalized_magnitude_vs_oracle_error"] = mp.nstr(
                        abs(magnitude - expected), 100,
                    )
                row.update({
                    "status": "observed",
                    "public_equivalent": result.equivalent,
                    "public_decision_basis": result.decision_basis,
                    "printed_only_status": printed.status,
                    "printed_only_reason": printed.reason,
                    "printed_only_certified_solver_bound": printed.certified_solver_bound,
                    "printed_count_real": str(value.real),
                    "printed_count_imag": str(value.imag),
                    "printed_real_half_unit": str(value.real_print_half_unit),
                    "printed_imag_half_unit": str(value.imag_print_half_unit),
                    "printed_count_format": value.format_name,
                    "wmc_input_is_final_rr_pathsum": True,
                    "precision_replay_runs": len(raw),
                    "precision_reason": result.wmc_precision_reason,
                    "precision_model_component_bound": result.wmc_numeric_model_bound,
                    "final_pathvars": result.final_pathsum.num_pathvar,
                })
                expected_public = "not_equivalent" if solver == "gpmc" else "unknown"
                assert result.equivalent == expected_public, (
                    solver,method,result.equivalent,result.wmc_precision_reason
                )
            except Exception as exc:
                row["status"] = "error"
                row["error"] = type(exc).__name__ + ": " + str(exc)[:650]
                errors.append(row["error"])
            rows.append(row)
            print("WMC_PRINTED_RESOLUTION " + json.dumps(row,sort_keys=True),flush=True)
    return rows,errors


def test_native_printed_distance_resolution_at_hybrid_boundary():
    rows, errors = analyze_native_wmc()
    OUT.mkdir(exist_ok=True)
    output = {
        "source": os.getenv("GITHUB_SHA"),
        "scope": "real native GPMC/Ganak printed counts; no arithmetic certificate",
        "rows": rows,
        "errors": errors,
    }
    (OUT / "wmc-distance-resolution.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n"
    )
    assert len(rows) == 4
    assert not errors
    assert all(
        r["public_equivalent"] == ("not_equivalent" if r["solver"]=="gpmc" else "unknown")
        for r in rows
    )
    assert all(r["wmc_input_is_final_rr_pathsum"] for r in rows)
    assert all(not r["printed_only_certified_solver_bound"] for r in rows)

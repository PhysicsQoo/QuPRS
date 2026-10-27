#!/usr/bin/env python3
"""Compare actual Python QuPRS emitted CNFs with a bounded rational reference.

The independent reference counts the exact printed decimal weights. Its
interval is NOT a proof of source-angle preservation or native solver
rounding correctness. Native count agreement is observational only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import traceback

from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator

from QuPRS.interface.gate_library import gate_map
from QuPRS.interface.load_qiskit import get_gates, initialize
from QuPRS.interface.ps2wmc import run_wmc, to_DIMACS
from QuPRS.utils import solver_process

from import_dimacs import (
    normalized_for_pathsum, parse_emitted_dimacs, serialized_count_verdict,
)
from interval_wmc import serialize_complex, serialize_interval


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def cases():
    for name in ("identity", "hh", "x", "rz_near", "rz_far"):
        qc = QuantumCircuit(1)
        if name == "hh":
            qc.h(0)
            qc.h(0)
        elif name == "x":
            qc.x(0)
        elif name == "rz_near":
            qc.rz(0.001, 0)
        elif name == "rz_far":
            qc.rz(0.01, 0)
        yield name, qc


def source_pathsum(qc):
    """Mirror QuPRS's Qiskit gate mapping with reduction disabled for WMC."""
    ps = initialize(qc)
    ps.set_reduction_switch(False)
    for gate, targets, angles in get_gates(qc):
        ps = gate_map(ps, gate, targets, angles)
    return ps


def one(name, qc, solver, folder):
    from QuPRS.utils.wmc_solvers import SOLVER_ARGUMENTS
    ps = source_pathsum(qc)
    dimacs_path = folder / f"{name}-{solver}.cnf"
    dimacs = to_DIMACS(ps, str(dimacs_path), tool_name=solver)
    if dimacs.strip().encode() != dimacs_path.read_bytes():
        raise AssertionError("Returned CNF differs from actual emitted bytes")
    imported = parse_emitted_dimacs(dimacs, solver=solver)
    count = imported.count()
    norm = normalized_for_pathsum(
        count, num_qubits=ps.num_qubits, num_pathvar=ps.num_pathvar
    )
    oracle_mag = abs(complex(Operator(qc).data.trace())) / (1 << qc.num_qubits)
    # Read the QASM source bytes for reproducible angle provenance. Their
    # binary64 interpretation is NOT promoted to an exact-radian certificate.
    qasm_bytes = qasm2.dumps(qc).encode()
    (folder / f"{name}.qasm").write_bytes(qasm_bytes)

    captures = []
    original_run = solver_process.run

    def observed_run(command, **kwargs):
        result = original_run(command, **kwargs)
        last_is_target = str(command[-1]) == str(dimacs_path)
        captures.append({
            "solver_args": list(command[1:-1]),
            "binary_sha256": sha256(Path(command[0]).read_bytes()),
            "target_generated_cnf": last_is_target,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })
        return result

    solver_process.run = observed_run
    try:
        real, imag = run_wmc(str(dimacs_path), solver, timeout=60.0)
    finally:
        solver_process.run = original_run

    expected_args = list(SOLVER_ARGUMENTS[solver])
    actual = [entry for entry in captures if entry["target_generated_cnf"]]
    if len(actual) != 1 or actual[0]["solver_args"] != expected_args:
        raise AssertionError("Native selected solver and CNF invocation not confirmed")
    if actual[0]["exit_code"] != 0:
        raise AssertionError("Selected WMC solver returned nonzero exit")

    solver_count = complex(real, imag)
    # This uses floats ONLY as a non-certified empirical comparison of
    # externally returned solver values and printed-CNF exact rational values.
    reference_center = complex(
        float((count.real.lower + count.real.upper) / 2),
        float((count.imag.lower + count.imag.upper) / 2),
    )
    observed_difference = abs(solver_count - reference_center)
    observational_budget = 2e-6 * max(1.0, abs(reference_center))
    normalized_ref_center = float((norm.lower + norm.upper) / 2)
    physics_difference = abs(normalized_ref_center - oracle_mag)
    physics_budget = 2e-6
    # A printed-weights interval upper bound <1 can be proved, but this
    # cannot automatically certify the native solver or a QASM real angle.
    record = {
        "case": name,
        "solver": solver,
        "encoding_provenance": "Python QuPRS.to_DIMACS after Qiskit gate mapping",
        "qasm_sha256": sha256(qasm_bytes),
        "cnf_sha256": sha256(dimacs_path.read_bytes()),
        "source_gate_names": [gate.operation.name for gate in qc.data],
        "num_qubits": ps.num_qubits,
        "num_pathvar": ps.num_pathvar,
        "expected_log2_times_two": 2 * ps.num_qubits + ps.num_pathvar,
        "declared_cnf_variables": len(imported.weights),
        "declared_cnf_clauses": len(imported.clauses),
        "raw_native_call_count": len(captures),
        "real_solver_mode_verified": True,
        "native_stdout": actual[0]["stdout"],
        "native_stderr": actual[0]["stderr"],
        "selected_solver_executable_sha256": actual[0]["binary_sha256"],
        "solver_count_float": {"real": real, "imag": imag},
        "printed_weight_reference_count": serialize_complex(count),
        "printed_weight_reference_normalized_interval": serialize_interval(norm),
        "printed_weight_reference_status": serialized_count_verdict(norm),
        "qiskit_operator_normalized_trace_float": oracle_mag,
        "native_minus_printed_reference_abs_float": observed_difference,
        "native_observational_tolerance": observational_budget,
        "printed_reference_vs_qiskit_trace_abs_float": physics_difference,
        "oracle_observational_tolerance": physics_budget,
        "agreement_is_a_certificate": False,
    }
    record["observational_cross_checks_pass"] = (
        math.isfinite(observed_difference)
        and observed_difference <= observational_budget
        and math.isfinite(physics_difference)
        and physics_difference <= physics_budget
    )
    if name == "rz_near":
        record["printed_reference_strict_below_one"] = norm.upper < 1
        record["observational_cross_checks_pass"] &= norm.upper < 1
    return record


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path("wmc-encoded-bridge-results"))
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, qc in cases():
        for solver in ("gpmc", "ganak"):
            print(f"CHECK {name} {solver}", flush=True)
            try:
                r = one(name, qc, solver, args.output)
            except Exception as exc:
                r = {"case": name, "solver": solver, "observational_cross_checks_pass": False,
                     "error": repr(exc), "traceback": traceback.format_exc()}
            filename = args.output / f"{name}-{solver}.json"
            filename.write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
            entries.append(r)
            print(f"RESULT {name} {solver} {r.get('observational_cross_checks_pass')}", flush=True)
    overall = "PASS" if len(entries) == 10 and all(
        e.get("observational_cross_checks_pass") for e in entries
    ) else "FAIL"
    (args.output / "summary.json").write_text(
        json.dumps({
            "status": overall,
            "case_count": len(entries),
            "python": sys.version,
            "platform": platform.platform(),
            "semantic_limit": "Printed weight rational evaluation only; NOT a source-to-solver certified interval",
            "results": entries,
        }, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({"status": overall, "cases": len(entries)}), flush=True)
    return 0 if overall == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

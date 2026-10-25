#!/usr/bin/env python3
"""Source-tagged Rust WmcManager-generated CNF reference and phase audit.

A rigorous phase enclosure here refers to the *rational coefficient stored
in the Rust PhasePolynomial*. It is not an enclosure for the original QASM
decimal radians or for the native solver's arithmetic.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback

# The bridge is kept research-only next to other replay studies; reuse the
# existing reference modules from their original scoped directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "wmc_interval_reference"))

from qiskit import qasm2
from qiskit.quantum_info import Operator

from QuPRS.interface.ps2wmc import run_wmc
from QuPRS.utils import solver_process

from import_dimacs import (
    normalized_for_pathsum, parse_emitted_dimacs, serialized_count_verdict,
)
from interval_wmc import ComplexInterval, WeightedCNF, serialize_complex, serialize_interval
from qasm_rz_source_reference import audit_single_rz_bra_source
from rz_sequence_oracle import CASES as SOURCE_CASES, make_qasm, compare_sources
from phase_coeff_reference import (
    ideal_rational_pi_phase, max_printed_ideal_component_gap,
    union_printed_and_ideal,
)

CASES = ("positive_rotation", "negative_rotation", "accumulated_rotation",
         "exact_cancellation", "identical_paths", "nearly_cancelled")
SOLVERS = ("gpmc", "ganak")
SUMMARY_PATTERN = re.compile(
    r"^RUST_RZ_SIX case=(\w+) solver=(gpmc|ganak) "
    r"qubits=(\d+) pathvars=(\d+) phase_terms=(\d+)$"
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def exported_metadata(stdout):
    data = {}
    for line in stdout.splitlines():
        match = SUMMARY_PATTERN.fullmatch(line)
        if match:
            case, solver, qubits, pathvars, phases = match.groups()
            key = (case, solver)
            if key in data:
                raise ValueError("Repeated Rust case metadata")
            data[key] = dict(n=int(qubits), p=int(pathvars), phases=int(phases))
    expected = {(case, solver) for case in CASES for solver in SOLVERS}
    if set(data) != expected:
        raise ValueError(f"Missing or extra Rust-generated CNF metadata: {set(data) ^ expected}")
    return data


def parse_phase_metadata(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "weight_lit\tphase_numerator\tphase_denominator\tmonomial":
        raise ValueError("Malformed Rust phase provenance header")
    phases = {}
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) != 4:
            raise ValueError("Malformed Rust rational phase record")
        literal, numer, denom = (int(v) for v in fields[:3])
        if literal <= 0 or literal in phases or denom <= 0 or not 0 <= numer < denom:
            raise ValueError("Invalid Rust rational phase variable")
        phases[literal] = (numer, denom, fields[3])
    return phases


def normalize_reference(cnf, phase_lookup, n, p):
    printed_weights = {}
    # Each annotated Rust phase variable MUST have an explicit positive
    # weight and a unit negative weight, as in WmcManager::to_dimacs_string.
    for i, (positive, negative) in enumerate(cnf.weights, 1):
        if i in phase_lookup:
            if negative != ComplexInterval.exact(1):
                raise ValueError("Rust phase variable has unexpected negative weight")
            printed_weights[i] = positive
        elif positive != ComplexInterval.exact(1) or negative != ComplexInterval.exact(1):
            raise ValueError("Unattributed weighted Rust DIMACS variable")
    if set(printed_weights) != set(phase_lookup):
        raise ValueError("Rust rational coefficient / printed weight mapping mismatch")
    widened = []
    phase_rows = []
    for i, (positive, negative) in enumerate(cnf.weights, 1):
        if i in phase_lookup:
            numer, denom, monomial = phase_lookup[i]
            reference = ideal_rational_pi_phase(numer, denom)
            hull = union_printed_and_ideal(positive, reference)
            bound = max_printed_ideal_component_gap(positive, reference)
            widened.append((hull, negative))
            phase_rows.append({
                "positive_literal": i, "coefficient_numerator": numer,
                "coefficient_denominator": denom, "monomial": monomial,
                "ideal_coefficient_phase_interval": serialize_complex(reference),
                "actual_printed_decimal_weight": serialize_complex(positive),
                "conservative_componentwise_printed_vs_ideal_gap": str(bound),
            })
        else:
            widened.append((positive, negative))
    printed_count = cnf.count()
    phase_enclosed_count = WeightedCNF(cnf.clauses, tuple(widened)).count()
    return (
        printed_count,
        normalized_for_pathsum(printed_count, num_qubits=n, num_pathvar=p),
        phase_enclosed_count,
        normalized_for_pathsum(phase_enclosed_count, num_qubits=n, num_pathvar=p),
        phase_rows,
    )


def observe_solver(filename, solver):
    """Capture actual selected solver binary, args, output and CNF digest."""
    original = solver_process.run
    captures = []
    def observed_run(command, **kwargs):
        output = original(command, **kwargs)
        matches = Path(command[-1]).resolve() == filename.resolve()
        captures.append({
            "target_cnf": matches,
            "command_args": list(command[1:-1]),
            "binary_sha256": digest(Path(command[0]).read_bytes()),
            "exit": output.returncode,
            "stdout": output.stdout,
            "stderr": output.stderr,
        })
        return output
    solver_process.run = observed_run
    try:
        real, imag = run_wmc(str(filename), solver, timeout=45)
    finally:
        solver_process.run = original
    targets = [entry for entry in captures if entry["target_cnf"]]
    if len(targets) != 1 or targets[0]["exit"] != 0:
        raise ValueError("Exactly one successful selected solver CNF call required")
    return complex(real, imag), targets[0], len(captures)


def run_case(folder, name, solver, meta):
    from QuPRS.utils.wmc_solvers import SOLVER_ARGUMENTS
    cnf_file = folder / f"{name}-{solver}.cnf"
    raw = cnf_file.read_bytes()
    cnf = parse_emitted_dimacs(raw.decode("utf-8"), solver=solver)
    phase_map = parse_phase_metadata(folder / f"{name}-{solver}-phases.tsv")
    if len(phase_map) != meta["phases"]:
        raise ValueError("Phase term count differs from native Rust metadata")
    printed, printed_norm, phase_widened, widened_norm, phases = normalize_reference(
        cnf, phase_map, meta["n"], meta["p"]
    )
    qasm_file = folder / f"{name}.qasm"
    qasm_raw = qasm_file.read_bytes()
    original = next((pair for pair in SOURCE_CASES if pair[0] == name), None)
    if original is None:
        raise ValueError("Unrecognized source pair")
    _, left, right, expected_source = original
    def inverse_angle(angle):
        return angle[1:] if angle.startswith("-") else "-" + angle
    relative_angles = tuple(inverse_angle(a) for a in reversed(left)) + tuple(right)
    expected_qasm = make_qasm(relative_angles).encode("utf-8")
    if qasm_raw != expected_qasm:
        raise ValueError("Rust exporter QASM diverges from exact relative source")
    source_proof = compare_sources(make_qasm(left), make_qasm(right))
    if source_proof["source_global_phase_verdict"] != expected_source:
        raise ValueError("Exact rational source relative-angle theorem mismatch")
    quantum_circuit = qasm2.loads(qasm_raw.decode("utf-8"))
    oracle = Operator(quantum_circuit).data
    if quantum_circuit.num_qubits != meta["n"]:
        raise ValueError("Source QASM and Rust qubit metadata mismatch")
    source_rz_audit = None
    source_rz_audit_error = None
    if name in ("rz_near", "rz_far", "rz_below_tolerance"):
        try:
            source_rz_audit = audit_single_rz_bra_source(
                qasm_raw.decode("utf-8"), cnf, phase_map,
                num_qubits=meta["n"], num_pathvar=meta["p"]
            )
        except (ValueError, TypeError, ArithmeticError) as exc:
            # Preserve the real CNF and native observations. A failed scoped
            # proof on the tiny case must be INCONCLUSIVE, never a theorem.
            if name != "rz_below_tolerance":
                raise
            source_rz_audit_error = f"{type(exc).__name__}: {exc}"
    physical_mag_float = abs(complex(oracle.trace())) / (1 << meta["n"])
    native, capture, capture_count = observe_solver(cnf_file, solver)
    if capture["command_args"] != list(SOLVER_ARGUMENTS[solver]):
        raise ValueError("Requested selected solver mode not used")
    baseline = complex(
        float((printed.real.lower + printed.real.upper) / 2),
        float((printed.imag.lower + printed.imag.upper) / 2)
    )
    deviation = abs(native - baseline)
    observed_budget = max(2e-6, 2e-6 * abs(baseline))
    # This is a comparison to a FLOAT operator oracle, not formal evidence.
    model_to_operator = abs(
        float((widened_norm.lower + widened_norm.upper) / 2) - physical_mag_float
    )
    report = {
        "case": name, "solver": solver, "source": "Rust WmcManager::encode_trace/to_dimacs_string",
        "source_qasm_sha256": digest(qasm_raw), "cnf_sha256": digest(raw),
        "num_qubits": meta["n"], "num_pathvar": meta["p"],
        "declared_cnf_variables": len(cnf.weights),
        "declared_cnf_clauses": len(cnf.clauses),
        "native_raw_process_calls": capture_count,
        "native_solver_binary_sha256": capture["binary_sha256"],
        "native_solver_args": capture["command_args"],
        "native_solver_stdout": capture["stdout"],
        "native_solver_stderr": capture["stderr"],
        "native_solver_float_count": {"real": native.real, "imag": native.imag},
        "printed_weight_exact_rational_count": serialize_complex(printed),
        "printed_weight_normalized_magnitude": serialize_interval(printed_norm),
        "represented_rust_phase_coefficient_enclosed_count": serialize_complex(phase_widened),
        "represented_rust_phase_coefficient_normalized_magnitude": serialize_interval(widened_norm),
        "represented_rust_phase_source_records": phases,
        "source_decimal_radian_rz_audit": source_rz_audit,
        "source_rz_audit_error": source_rz_audit_error,
        "phase_coefficient_reference_is_certified_for_original_qasm": False,
        "exact_source_pair_theorem": source_proof,
        "source_cnf_formal_certificate": "NOT_AVAILABLE",
        "source_to_rust_phase_polynomial_certified": False,
        "compiled_circuit_exact_equivalence_certified": False,
        "native_solver_result_is_interval_certified": False,
        "printed_reference_classification": serialized_count_verdict(printed_norm),
        "represented_coefficient_reference_classification": serialized_count_verdict(widened_norm),
        "operator_oracle_magnitude_float": physical_mag_float,
        "native_vs_printed_weight_count_abs_float": deviation,
        "observational_budget": observed_budget,
        "model_to_qiskit_operator_abs_float": model_to_operator,
        "observational_cross_check": (
            math.isfinite(deviation) and deviation <= observed_budget
            and math.isfinite(model_to_operator) and model_to_operator <= 2e-6
        ),
    }
    if name == "rz_below_tolerance":
        valid = bool(
            source_rz_audit
            and source_rz_audit["source_reference_strictly_below_one"]
            and source_rz_audit["source_represented_printed_hull_strictly_below_one"]
            and source_rz_audit["source_boolean_encoding_proof"]["weighted_literal_activation_verified"]
        )
        report["rust_small_rz_source_model_status"] = (
            "PROVED_NON_EQUIVALENT" if valid else "INCONCLUSIVE"
        )
        report["rust_small_rz_source_model_is_conditional"] = True
        report["native_solver_result_is_interval_certified"] = False
    if name == "rz_near":
        report["printed_weight_strictly_below_one"] = printed_norm.upper < 1
        report["represented_phase_coefficient_strictly_below_one"] = widened_norm.upper < 1
        report["observational_cross_check"] &= (
            printed_norm.upper < 1 and widened_norm.upper < 1
            and source_rz_audit["source_reference_strictly_below_one"]
            and source_rz_audit["source_represented_printed_hull_strictly_below_one"]
        )
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("rust-wmc-phase-results"))
    opts = parser.parse_args()
    output = opts.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cmd = [
        "cargo", "run", "--locked", "--release",
        "--manifest-path", "rust/Cargo.toml", "-p", "pathsum",
        "--example", "rz_sequence_cnf_reference", "--", str(output),
    ]
    exported = subprocess.run(cmd, capture_output=True, text=True, timeout=360)
    (output / "rust-example-stdout.txt").write_text(exported.stdout, encoding="utf-8")
    (output / "rust-example-stderr.txt").write_text(exported.stderr, encoding="utf-8")
    if exported.returncode:
        print(f"RUST_EXPORT_FAILURE exit={exported.returncode}")
        return 2
    metadata = exported_metadata(exported.stdout)
    reports = []
    for case in CASES:
        for solver in SOLVERS:
            try:
                data = run_case(output, case, solver, metadata[(case, solver)])
            except Exception as exc:
                data = {"case": case, "solver": solver, "observational_cross_check": False,
                        "error": repr(exc), "traceback": traceback.format_exc()}
            (output / f"{case}-{solver}.json").write_text(
                json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            reports.append(data)
            print("RUST_REFERENCE", case, solver,
                  data.get("observational_cross_check"), flush=True)
    status = "PASS" if len(reports) == len(CASES) * len(SOLVERS) and all(
        record.get("observational_cross_check") for record in reports
    ) else "FAIL"
    summary = {
        "schema": "rust-rz-sequence-six-case-native-observation-v1",
        "source_head": os.environ.get("GITHUB_SHA"),
        "status": status, "count": len(reports),
        "scope": (
            "Actual Rust-emitted GPMC/Ganak CNF, selected native solver stdout "
            "and represented Rust phase coefficient to printed weight interval "
            "observations only. The exact rational RZ pair theorem is source-only; "
            "the general source->Rust PhasePolynomial compiler correspondence "
            "and native solver arithmetic are NOT certified."
        ),
        "rust_source_to_cnf_formal_certificate": False,
        "cases": reports,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("RUST_REFERENCE_SUMMARY", json.dumps({"status": status, "count": len(reports)}))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())

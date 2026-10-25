#!/usr/bin/env python3
"""Audit independent Python-source solver fixtures with the bounded source CNF oracle.

This research-only bridge joins the *actual* Python-emitted CNFs and their
source/solver provenance to the existing one-qubit diagonal certificate. It
never converts a solver's approximate count into a proof or changes API verdicts.
"""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import re
import sys

from qiskit import qasm2

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = ROOT / ".diagnostics" / "wmc_interval_reference"
sys.path.insert(0, str(DIAGNOSTICS))

from import_dimacs import parse_emitted_dimacs  # noqa: E402
from python_diagonal_source_certificate import (  # noqa: E402
    audit_diagonal_source_to_emitted_cnf,
    parse_diagonal_qasm,
)
from QuPRS.interface.ps2wmc import P_to_wlogi  # noqa: E402
from run_python_source_conformance import unreduced_python_pathsum  # noqa: E402

SOLVERS = ("gpmc", "ganak")
GATES = {
    "hh": "h q[0];\nh q[0];\n",
    "x": "x q[0];\n",
    "t": "t q[0];\n",
}
HEADER = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_valid(condition, message):
    if not condition:
        raise ValueError(message)


def check_observation(folder, case, solver):
    """Validate exact artifact identity before interpreting any weight."""
    record_path = folder / f"{case}-python-{solver}.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    source_path = folder / f"{case}.qasm"
    python_cnf = folder / f"{case}-python-{solver}.cnf"
    rust_cnf = folder / f"{case}-{solver}.cnf"

    assert_valid(record.get("case") == case and record.get("solver") == solver,
                 "Conformance case/solver identity mismatch")
    assert_valid(record.get("observational_pass") is True
                 and record.get("formal_equivalence_certificate") is False,
                 "Source conformance diagnostic lacks a successful observation")
    assert_valid(record.get("exit_code") == 0
                 and isinstance(record.get("native_stdout"), str)
                 and isinstance(record.get("native_stderr"), str),
                 "Missing successful native solver provenance")
    assert_valid(record.get("source_qasm_sha256") == file_hash(source_path),
                 "Source QASM fingerprint mismatch")
    assert_valid(record.get("python_emitted_cnf_sha256") == file_hash(python_cnf),
                 "Python-emitted CNF fingerprint mismatch")
    assert_valid(record.get("rust_emitted_cnf_sha256") == file_hash(rust_cnf),
                 "Rust-emitted CNF fingerprint mismatch")
    assert_valid(record.get("cnf_bytes_equal")
                 == (python_cnf.read_bytes() == rust_cnf.read_bytes()),
                 "Reported CNF byte comparison mismatch")
    assert_valid(bool(SHA256.fullmatch(record.get("selected_binary_sha256", ""))),
                 "Missing native solver executable fingerprint")
    source = source_path.read_text(encoding="utf-8")
    assert_valid(source == HEADER + GATES[case],
                 "Source text differs from the exact supported fixture")
    return record, source, python_cnf


def audit(folder):
    summary_path = folder / "python-source-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert_valid(summary.get("status") == "PASS"
                 and summary.get("count") == len(GATES) * len(SOLVERS)
                 and summary.get("formal_certificate") is False,
                 "Source conformance evidence is incomplete or misclassified")

    results = []
    for case in GATES:
        for solver in SOLVERS:
            observation, source, cnf_path = check_observation(folder, case, solver)
            entry = {
                "case": case, "solver": solver,
                "source_qasm_sha256": observation["source_qasm_sha256"],
                "python_emitted_cnf_sha256": observation["python_emitted_cnf_sha256"],
                "rust_emitted_cnf_sha256": observation["rust_emitted_cnf_sha256"],
                "selected_solver_binary_sha256": observation["selected_binary_sha256"],
                "native_solver_observational_only": True,
                "native_solver_arithmetic_certified": False,
                "general_qasm_compiler_certified": False,
            }
            try:
                parsed_source = parse_diagonal_qasm(source)
            except ValueError:
                assert_valid(case in ("hh", "x"), "Supported diagonal fixture rejected")
                entry["certificate_outcome"] = "UNSUPPORTED_SOURCE_GRAMMAR"
                entry["strict_non_equivalence_certified"] = False
            else:
                assert_valid(case == "t" and parsed_source == (("t", None),),
                             "Unexpected accepted source certificate scope")
                circuit = qasm2.loads(source)
                pathsum = unreduced_python_pathsum(circuit)
                assert_valid(pathsum.num_qubits == 1 and pathsum.num_pathvar == 0,
                             "Unsupported PathSum normalization")
                assert_valid(observation.get("unreduced_path_variables") == 0
                             and observation.get("trace_normalizer") == 2.0,
                             "Observed trace normalization differs from certified one")
                emitted = parse_emitted_dimacs(cnf_path.read_text(encoding="utf-8"),
                                               solver=solver)
                certificate = audit_diagonal_source_to_emitted_cnf(
                    source, pathsum, emitted, p_to_wlogi=P_to_wlogi
                )
                bound = certificate["inclusive_source_printed_normalized_magnitude"]
                upper = Fraction(bound["upper"])
                assert_valid(certificate["formal_source_wmc_non_equivalence_supported"]
                             and certificate["source_non_equivalent_up_to_global_phase_proved"]
                             and certificate["source_printed_hull_strictly_below_one"]
                             and upper < 1,
                             "Expected bounded source and printed-weight negative proof")
                proof = certificate["source_boolean_encoding_proof"]
                assert_valid(proof["weighted_literal_activation_verified"]
                             and proof["input_bit_zero_unique_extension"]
                             and proof["input_bit_one_unique_extension"],
                             "Missing unique Boolean extension proof")
                entry["certificate_outcome"] = "BOUNDED_SOURCE_NON_EQUIVALENT"
                entry["strict_non_equivalence_certified"] = True
                entry["source_printed_hull_upper"] = str(upper)
                entry["source_certificate"] = certificate
            results.append(entry)
            print(f"SOURCE_INTERVAL {case} {solver} {entry['certificate_outcome']}",
                  flush=True)

    assert_valid(len(results) == 6, "Incomplete conformance certificate audit")
    assert_valid(sum(row["strict_non_equivalence_certified"] for row in results) == 2,
                 "Expected exactly two supported diagonal certificates")
    assert_valid(sum(row["certificate_outcome"] == "UNSUPPORTED_SOURCE_GRAMMAR"
                     for row in results) == 4,
                 "Unsupported nondiagnostic gates must not be certified")
    payload = {
        "schema": "source-cnf-interval-cross-conformance-v1",
        "status": "PASS",
        "source_fixtures": 3,
        "native_solver_observations": 6,
        "bounded_negative_source_certificates": 2,
        "explicitly_unsupported_certificates": 4,
        "certification_scope": "only one-qubit canonical T and actual Python-emitted CNF",
        "provenance": ("Source QASM and Python/Rust CNF hashes, selected solver binary "
                       "fingerprint, unique Boolean activation, source/printed hull"),
        "native_solver_arithmetic_certified": False,
        "general_source_compiler_certified": False,
        "public_equivalence_policy_changed": False,
        "records": results,
    }
    (folder / "source-interval-bridge-summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("SOURCE_INTERVAL_SUMMARY PASS supported=2 unsupported=4", flush=True)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    options = parser.parse_args()
    audit(options.out.resolve())


if __name__ == "__main__":
    main()

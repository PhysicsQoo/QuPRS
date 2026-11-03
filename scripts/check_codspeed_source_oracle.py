#!/usr/bin/env python3
"""Independent Qiskit operator check OUTSIDE CodSpeed timed regions.

Complex128 reference on vqe4/grover4/qnn4/vqe8 source pairs supports
unitary consistency up to a global phase, NOT a rigorous 1e-8 certificate
or a bound on the GPMC printed-count arithmetic error.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

SOURCES = {
    "vqe4": "vqe_nativegates_ibm_qiskit_opt0_4.qasm",
    "grover4": "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
    "qnn4": "qnn_nativegates_ibm_qiskit_opt0_4.qasm",
    "vqe8": "vqe_nativegates_ibm_qiskit_opt0_8.qasm",
    "qpeexact8": "qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
    "wstate4": "wstate_nativegates_ibm_qiskit_opt0_4.qasm",
}


DEFAULT_CASES = ("vqe4", "grover4", "qnn4", "vqe8")


def evaluate(root: Path, sha: str, cases=None) -> dict:
    report = {"schema": "source-qasm-global-phase-double-v1", "fixture_sha": sha,
              "certified_epsilon_distance": False, "cases": {}}
    selected = DEFAULT_CASES if cases is None else tuple(cases)
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("source-oracle case selection must be nonempty and unique")
    for case in selected:
        filename = SOURCES[case]
        paths = [root / "benchmarks/MQTBench" / filename,
                 root / "benchmarks/MQTBench/h,ry,rz,cx" / filename]
        original = [p.read_bytes() for p in paths]
        matrices = [np.asarray(Operator(QuantumCircuit.from_qasm_str(
                    source.decode("utf-8"))).data, dtype=np.complex128)
                    for source in original]
        a, b = matrices
        qubits = 8 if case in {"vqe8", "qpeexact8"} else 4
        dimension = 1 << qubits
        if a.shape != (dimension, dimension) or b.shape != (dimension, dimension):
            raise ValueError(f"{case}: expected {qubits}-qubit unitary operators")
        overlap = np.vdot(a, b) / dimension
        phase = overlap / abs(overlap) if abs(overlap) else 0j
        # Stable near true equivalence; avoid catastrophic cancellation in
        # sqrt(1 - abs(overlap)**2) using complex128 trace arithmetic.
        residual = float(np.linalg.norm(b - phase * a, ord="fro")
                         / np.sqrt(dimension))
        unitary_errors = [float(np.linalg.norm(
            u.conj().T @ u - np.eye(dimension), ord="fro")) for u in matrices]
        # Independent double-precision sanity check, not a second QuPRS
        # distance classifier or an assertion of exact symbolic identity.
        consistent = residual < 1e-10 and max(unitary_errors) < 1e-10
        report["cases"][case] = {
            "qubits": qubits,
            "matrix_dimension": dimension,
            "qasm_sha256": [hashlib.sha256(x).hexdigest() for x in original],
            "phase_corrected_frobenius_normalized": residual,
            "normalized_trace_magnitude": float(abs(overlap)),
            "relative_global_phase_rad": float(np.angle(overlap)),
            "unitarity_residuals": unitary_errors,
            "numerically_consistent_up_to_global_phase": bool(consistent),
        }
        if not consistent:
            raise ValueError(f"{case}: source-pair numerical oracle failed")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", nargs="+", choices=tuple(SOURCES))
    args = parser.parse_args()
    result = evaluate(args.fixture_root, args.head_sha, args.cases)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({k: v["phase_corrected_frobenius_normalized"]
                      for k, v in result["cases"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()

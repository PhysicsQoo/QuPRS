#!/usr/bin/env python3
"""Independent small-QASM operator check OUTSIDE CodSpeed timed regions.

Complex128 evidence supports source equivalence up to phase but never
certifies a rigorous 1e-8 projective-distance bound.
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
}


def evaluate(root: Path, sha: str) -> dict:
    report = {"schema": "source-qasm-global-phase-double-v1", "fixture_sha": sha,
              "certified_epsilon_distance": False, "cases": {}}
    for case, filename in SOURCES.items():
        paths = [root / "benchmarks/MQTBench" / filename,
                 root / "benchmarks/MQTBench/h,ry,rz,cx" / filename]
        original = [p.read_bytes() for p in paths]
        matrices = [np.asarray(Operator(QuantumCircuit.from_qasm_str(
                    source.decode("utf-8"))).data, dtype=np.complex128)
                    for source in original]
        a, b = matrices
        if a.shape != (16, 16) or b.shape != (16, 16):
            raise ValueError(f"{case}: expected 4-qubit unitary operators")
        overlap = np.vdot(a, b) / 16
        phase = overlap / abs(overlap) if abs(overlap) else 0j
        residual = float(np.linalg.norm(b - phase * a, ord="fro") / 4)
        unitary_errors = [float(np.linalg.norm(
            u.conj().T @ u - np.eye(16), ord="fro")) for u in matrices]
        # Independent double-precision sanity check, not a second QuPRS
        # distance classifier or an assertion of exact symbolic identity.
        consistent = residual < 1e-10 and max(unitary_errors) < 1e-10
        report["cases"][case] = {
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
    args = parser.parse_args()
    result = evaluate(args.fixture_root, args.head_sha)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({k: v["phase_corrected_frobenius_normalized"]
                      for k, v in result["cases"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()

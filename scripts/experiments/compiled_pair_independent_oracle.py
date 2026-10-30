"""Independent physical-oracle controls for the MQTBench compiled pairs.

Qiskit small-N matrix Frobenius residual avoids cancellation in 1-|trace/d|^2.
QCEC is an independent heuristic/proof engine; do not interpret "probably" as exact.
This is entirely experimental and never changes QuPRS dependencies or WMC.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from time import perf_counter
import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Operator

CASES = {
    "grover4": "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
    "qaoa7": "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
    "graphstate16": "graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
    "qft16": "qft_nativegates_ibm_qiskit_opt0_16.qasm",
}

def sanitized(path: Path):
    source = path.read_text()
    contents = "\n".join(
        l for l in source.splitlines()
        if not l.strip().startswith(("measure ", "barrier ", "reset ", "creg "))
    ) + "\n"
    return qasm2.loads(contents)

def stable_projective_distance(a, b):
    d = a.shape[0]
    overlap = np.vdot(a, b) / d
    phase = overlap / abs(overlap) if abs(overlap) else 1
    residual = b - phase * a
    loss = float(np.vdot(residual, residual).real / (2*d))
    return float(math.sqrt(max(0.0, 2.0 * loss - loss*loss)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2] / "benchmarks/MQTBench"
    name = CASES[args.case]
    source = sanitized(root / name)
    compiled = sanitized(root / "h,ry,rz,cx" / name)
    result = {
        "case": args.case,
        "n_qubits": source.num_qubits,
        "source_gates": source.size(),
        "compiled_gates": compiled.size(),
        "projective_threshold": 1e-8,
        "qcec_version": None,
        "qcec_equivalence": None,
        "qcec_time_s": None,
        "matrix_distance": None,
        "oracle_type": None,
    }
    if source.num_qubits <= 7:
        start = perf_counter()
        a, b = Operator(source).data, Operator(compiled).data
        distance = stable_projective_distance(a, b)
        result["matrix_distance"] = distance
        result["oracle_type"] = "complete_Qiskit_Operator_unitary_Frobenius"
        result["matrix_time_s"] = perf_counter() - start
        print(f"EXPERIMENT_INDEPENDENT_MATRIX case={args.case} n={source.num_qubits} D_proj={distance:.14e} eps_D=1e-8", flush=True)
    else:
        # Avoid constructing 2**n x 2**n dense unitaries for 16q cases.
        result["oracle_type"] = "QCEC_non_dense_crosscheck"
    from mqt import qcec
    import importlib.metadata
    result["qcec_version"] = importlib.metadata.version("mqt.qcec")
    start = perf_counter()
    qcec_result = qcec.verify(source, compiled)
    result["qcec_time_s"] = perf_counter() - start
    result["qcec_equivalence"] = str(qcec_result.equivalence)
    print(f"EXPERIMENT_INDEPENDENT_QCEC case={args.case} result={result['qcec_equivalence']} elapsed={result['qcec_time_s']:.3f}s",flush=True)
    args.out.write_text(json.dumps(result, indent=2)+"\n")

if __name__ == "__main__":
    main()

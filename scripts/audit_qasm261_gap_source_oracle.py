#!/usr/bin/env python3
"""Independent, bounded QASM261 source oracle (no QuPRS Solver or CodSpeed).

QAOA7 negative/positive and VQE8 positive: dense 7-8q complex128 operators.
QFT16 negative: source-pinned 16q input-state witnesses, no 2^16 square matrix.
The output deliberately does NOT claim rigorous floating-point error bounds,
GPMC arithmetic certification, or evidence of performance improvements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "benchmarks" / "MQTBench"
AUDIT = ROOT / "benchmarks" / "codspeed" / "qasm_variant_audit.json"
CASES = {
    "qaoa7": ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", 7),
    "vqe8": ("vqe_nativegates_ibm_qiskit_opt0_8.qasm", 8),
    "qft16": ("qft_nativegates_ibm_qiskit_opt0_16.qasm", 16),
}
POS = "qiskit-2.6.1-opt0/h,ry,rz,cx"
NEG = "qiskit-2.6.1-opt0/Random_Rotation"


def exact_git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\\x00" + data).hexdigest()


def load_circuits():
    registry = json.loads(AUDIT.read_text(encoding="utf-8"))
    entries = {row["file"]: row for row in registry["mqt"]}
    result = {}
    for name, (filename, qubits) in CASES.items():
        record = entries[filename]
        variants = {
            "source": CORPUS / filename,
            "positive": CORPUS / POS / filename,
            "negative": CORPUS / NEG / filename,
        }
        circuits, sha = {}, {}
        for kind, path in variants.items():
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            sha[kind] = digest
            if kind == "source":
                assert exact_git_blob_sha1(raw) == record["source"]["git_blob_sha1"], name
            else:
                assert digest == record["qiskit261_" + kind]["sha256"], (name, kind)
            qc = QuantumCircuit.from_qasm_str(raw.decode("utf-8"))
            if qc.num_qubits != qubits or qc.num_clbits != 0:
                raise AssertionError(f"{name}/{kind}: unexpected register dimensions")
            circuits[kind] = qc
        result[name] = (circuits, sha, qubits)
    return result


def phase_aligned_residual(a: np.ndarray, b: np.ndarray, normalizer: float) -> float:
    overlap = np.vdot(a, b)
    if abs(overlap) < 1e-30:
        return float(np.linalg.norm(a - b) / normalizer)
    phase = overlap / abs(overlap)
    return float(np.linalg.norm(b - phase * a) / normalizer)


def dense_oracle(circuits, hashes, qubits, expected_negative: bool) -> dict:
    d = 1 << qubits
    ops = {name: np.asarray(Operator(qc).data, dtype=np.complex128)
           for name, qc in circuits.items() if name != "negative" or expected_negative}
    assert all(x.shape == (d, d) for x in ops.values())
    pos = phase_aligned_residual(ops["source"], ops["positive"], math.sqrt(d))
    if not pos < 1e-9:
        raise AssertionError(f"positive source mismatch: {pos}")
    ret = {"qubits": qubits, "source_hashes": hashes,
           "positive_relative_frobenius_residual": pos,
           "positive_class": "EQ complex128 witness; not a certified 1e-8 bound",
           "negative_class": "not requested"}
    if expected_negative:
        neg = phase_aligned_residual(ops["source"], ops["negative"], math.sqrt(d))
        if not neg > 1e-3:
            raise AssertionError(f"negative source did not separate: {neg}")
        ret.update(negative_relative_frobenius_residual=neg,
                   negative_class="NEQ strong complex128 source-operator witness")
    return ret


def state_oracle(circuits, hashes, qubits) -> dict:
    d = 1 << qubits
    # Distinct basis inputs catch a spuriously same-looking single output.
    test_indices = (0, 1 << (qubits // 2), d - 1)
    observations = []
    for idx in test_indices:
        initial = Statevector.from_int(idx, d)
        outputs = {name: np.asarray(initial.evolve(qc).data, dtype=np.complex128)
                   for name, qc in circuits.items()}
        eq = phase_aligned_residual(outputs["source"], outputs["positive"], 1.0)
        neq = phase_aligned_residual(outputs["source"], outputs["negative"], 1.0)
        # For exact unitaries and ANY global phase, a single input state's
        # min-phase vector separation s gives D_proj >= s / sqrt(2d).
        # Floating evaluations are witnesses, not certified interval bounds.
        conservative_distance_lower_witness = neq / math.sqrt(2 * d)
        if not eq < 1e-9 or not conservative_distance_lower_witness > 1e-5:
            raise AssertionError(f"basis {idx}: pos {eq}, neg {neq}")
        observations.append({
            "basis_index": idx, "positive_state_phase_residual": eq,
            "negative_state_phase_residual": neq,
            "projective_distance_lower_witness": conservative_distance_lower_witness
        })
    return {"qubits": qubits, "source_hashes": hashes,
            "basis_state_witnesses": observations,
            "negative_class": "NEQ finite-precision source-state witnesses",
            "operator_matrix_built": False,
            "high_precision_error_certificate": False}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    cases = load_circuits()
    qaoa, vqe, qft = cases["qaoa7"], cases["vqe8"], cases["qft16"]
    out = {"schema": "quprs-qasm261-independent-source-oracle-v1",
           "method": "Qiskit QuantumCircuit+Operator/Statevector, complex128",
           "solver_invoked": False, "codspeed_performance": False,
           "rigorous_arithmetic_certification": False,
           "cases": {
               "qaoa7": dense_oracle(*qaoa, expected_negative=True),
               "vqe8": dense_oracle(*vqe, expected_negative=False),
               "qft16": state_oracle(*qft),
           }}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, sort_keys=True, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps({name: {"class": row["negative_class"],
                             "positive_residual": row.get("positive_relative_frobenius_residual"),
                             "state_witness_count": len(row.get("basis_state_witnesses", []))}
                      for name, row in out["cases"].items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

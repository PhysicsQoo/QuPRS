#!/usr/bin/env python3
"""Science-only numerical check of original TACAS26 Qiskit 1.4.2 QASM pairs.

No solver calls, walltime measurements, QASM regeneration, or performance claims.
The original saved QASM pair, not a fresh transpile, is the object of analysis.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
from collections import defaultdict
from pathlib import Path

import numpy as np
import qiskit
from qiskit import qasm2
from qiskit.quantum_info import Operator, Statevector

from scripts.tacas26_paper_matrix import matrix

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/development/tacas26-ganak101-permanent/ganak20-eq-to-neq.csv"
SOURCE_SHA = "e928abc47dd15926364ec77905eb0d5dc92ce8cc"
QISKIT_VERSION = "1.4.2"
FULL_OPERATOR_MAX_QUBITS = 8
SAMPLE_MAX_QUBITS = 22


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure_pair(first, second, seed):
    src = qasm2.loads(first.read_text(encoding="utf8"))
    dst = qasm2.loads(second.read_text(encoding="utf8"))
    if src.num_qubits != dst.num_qubits or src.num_clbits != dst.num_clbits:
        return {"status": "REGISTER_MISMATCH"}
    n = src.num_qubits
    result = {
        "status": "NOT_MEASURED",
        "qubits": n,
        "source_ops": src.size(),
        "transpiled_ops": dst.size(),
        "source_global_phase": float(src.global_phase),
        "transpiled_global_phase": float(dst.global_phase),
        "numeric_type": "numpy.complex128_qiskit_operator",
        "interpretation": "FLOAT_OBSERVATION_NOT_CERTIFIED",
    }
    if any(src.count_ops().get(x) or dst.count_ops().get(x)
           for x in ("measure", "reset", "if_else", "while_loop")):
        result["status"] = "NONUNITARY_SKIPPED"
        return result
    if n <= FULL_OPERATOR_MAX_QUBITS:
        u = Operator(src).data
        v = Operator(dst).data
        dim = 2 ** n
        normalized_inner = complex(np.vdot(u, v) / dim)
        magnitude = min(1.0, abs(normalized_inner))
        projective_d = math.sqrt(max(0.0, (1 - magnitude) * (1 + magnitude)))
        phase = normalized_inner / abs(normalized_inner) if normalized_inner else 1
        result.update({
            "status": "FULL_FLOAT_OPERATOR",
            "projective_distance_float": projective_d,
            "phase_aligned_frobenius_normalized_float":
                float(np.linalg.norm(u - v / phase) / math.sqrt(dim)),
            "trace_normalized_overlap_abs_float": abs(normalized_inner),
        })
    elif n <= SAMPLE_MAX_QUBITS:
        # These are independent input-state observations. Not the trace-based
        # projective metric and not a universal operator norm upper bound.
        rng = np.random.default_rng(seed)
        count = 4 if n <= 11 else 2
        sample = []
        for i in range(count):
            if i == 0:
                psi = np.zeros(2 ** n, dtype=np.complex128)
                psi[0] = 1
            elif i == 1:
                psi = np.ones(2 ** n, dtype=np.complex128) / math.sqrt(2 ** n)
            else:
                psi = (rng.standard_normal(2 ** n)
                       + 1j * rng.standard_normal(2 ** n))
                psi = psi / np.linalg.norm(psi)
            a = Statevector(psi).evolve(src).data
            b = Statevector(psi).evolve(dst).data
            inner = complex(np.vdot(a, b))
            local_phase = inner / abs(inner) if inner else 1
            sample.append({
                "input": ("zero" if i == 0 else "uniform_plus" if i == 1
                          else "random_complex_" + str(i)),
                "state_distance_up_to_individual_phase_float":
                    float(np.linalg.norm(a - b / local_phase)),
                "state_overlap_abs_float": abs(inner),
                "relative_global_phase_radians_float": math.atan2(
                    inner.imag, inner.real),
            })
        result.update({
            "status": "SAMPLED_FLOAT_STATEVECTORS",
            "samples": sample,
            "max_sample_state_distance_float":
                max(x["state_distance_up_to_individual_phase_float"] for x in sample),
            "max_sample_state_infidelity_float":
                max(max(0.0, 1 - x["state_overlap_abs_float"] ** 2)
                    for x in sample),
        })
    else:
        result["status"] = "NOT_MEASURED_RESOURCE_BOUND"
        result["reason"] = "Only up to 22 qubits for deterministic science probe"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if qiskit.__version__ != QISKIT_VERSION:
        raise RuntimeError("Exact paper Qiskit version required")
    cases = {row["id"]: row for row in matrix(ROOT)}
    with INPUT.open(encoding="utf8", newline="") as f:
        archive = list(csv.DictReader(f))
    if len(archive) != 20 or len({r["id"] for r in archive}) != 20:
        raise ValueError("Expected precisely the original 20 false-NEQ cases")
    measured = {}
    rows = []
    for rec in archive:
        key = rec["id"]
        source = cases[key]
        if source["suite"] != "table2" or source["kind"] != "positive":
            raise ValueError("Only Table 2 original/transpiled positives permitted")
        a, b = ROOT / source["a"], ROOT / source["b"]
        if (sha(a) != rec["original_qasm_sha256"]
                or sha(b) != rec["counterpart_qasm_sha256"]):
            raise ValueError("Original source-pinned QASM SHA differs: " + key)
        pair_key = (source["a"], source["b"])
        if pair_key not in measured:
            measured[pair_key] = measure_pair(a, b, seed=20260415)
        rows.append({
            "case_id": key,
            "method": rec["method"],
            "ganak_point_distance": float(rec["printed_point_distance"]),
            "ganak_print_resolution_distance":
                float(rec["print_resolution_distance"]),
            "original_path": source["a"], "transpiled_path": source["b"],
            "original_sha256": rec["original_qasm_sha256"],
            "transpiled_sha256": rec["counterpart_qasm_sha256"],
            "independent_qiskit_audit": measured[pair_key],
        })
    if len(rows) != 20:
        raise ValueError("Incorrect audit cardinality")
    out = {
        "schema": "tacas26-qiskit142-original-transpiled-20-science-v1",
        "original_quprs_sha": SOURCE_SHA,
        "replay_qiskit": qiskit.__version__,
        "replay_numpy": np.__version__,
        "python_version": platform.python_version(),
        "no_retranspilation": True,
        "basis_from_paper": ["h", "ry", "rz", "cx"],
        "measurement_limits": {
            "full_operator_max_qubits": FULL_OPERATOR_MAX_QUBITS,
            "statevector_samples_max_qubits": SAMPLE_MAX_QUBITS,
            "number_of_independent_unique_pairs": len(measured),
        },
        "numeric_certified": False,
        "numeric_limitations": [
            "Float64 Operator/Statevector observations are not rigorous mathematical certificates",
            "Sampled statevector error is not the trace-based projective distance",
            "The 64-qubit graph state remains resource bounded and unmeasured",
            "Frozen QASM comparison does not prove original transpiler emitted exact gates",
            "No source-to-QASM generator metadata or fixed transpiler seed is inferred",
        ],
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2,
                                      sort_keys=True) + "\n", encoding="utf8")
    by_id = {}
    for r in rows:
        by_id.setdefault(r["case_id"].split(":")[1], r)
    report = [
        "# TACAS 2026 Qiskit 1.4.2 original QASM numerical check",
        "",
        "Paper Table 2 used Qiskit 1.4.2 for H/Ry/Rz/CX transpilation.",
        "The Feynman appendix was separately transpiled with Qiskit 1.2.4.",
        "This experiment imports exact archived Table 2 original and transpiled",
        "QASM files with Qiskit 1.4.2. It DOES NOT re-transpile them.",
        "Every pair is matched against the existing Ganak source-pinned SHA256.",
        "",
        "| Circuit | Qubits | Numerical check | Floating distance or maximum sample state difference | Ganak printed-point D |",
        "|---|---:|---|---:|---:|",
    ]
    for k, r in sorted(by_id.items()):
        d = r["independent_qiskit_audit"]
        metric = (d.get("projective_distance_float") if
                  d["status"] == "FULL_FLOAT_OPERATOR" else
                  d.get("max_sample_state_distance_float"))
        report.append("| " + k + " | " + str(d.get("qubits", "?")) + " | " +
                      d["status"] + " | " +
                      (format(metric, ".8g") if metric is not None else "not measured") +
                      " | " + format(r["ganak_point_distance"], ".8g") + " |")
    report += [
        "", "The float-only Qiskit matrix comparison does not certify exact",
        "semantic equivalence, nor does it prove transpiler or solver fault.",
        "The sample-state differences for n>8 cannot be substituted into",
        "the QuPRS trace-based projective distance decision.",
        "See qiskit142-20.json for pinned QASM SHA256 and sample overlap details.",
        "Science-only: no CodSpeed performance data and no Solver runs.",
    ]
    (args.output.parent / "README.md").write_text(
        "\n".join(report) + "\n", encoding="utf8")
    summary = {
        "status_counts": dict(sorted((s, sum(
            r["independent_qiskit_audit"]["status"] == s for r in by_id.values()))
            for s in {r["independent_qiskit_audit"]["status"] for r in by_id.values()})),
        "unique_pairs": len(by_id),
    }
    print("TACAS_QISKIT_142_AUDIT", json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

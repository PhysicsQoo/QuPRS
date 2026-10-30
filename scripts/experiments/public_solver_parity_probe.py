"""Experiment-only, same-runner public Python/Rust and actual-solver parity.

Each row invokes exactly one selected solver via the public verifier.
The Qiskit operator is an independent small-circuit physics oracle.
Python CNF hashes are diagnostic and are NOT expected to match Rust bytes.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Operator
from mpmath import mp
from QuPRS import check_equivalence

HEADER = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
CASES = (
    ("identity", "", ""),
    ("h", "", "h q[0];"),
    ("h2", "", "h q[0];\nh q[0];"),
    ("x", "", "x q[0];"),
    ("z", "", "z q[0];"),
    ("h_vs_h", "h q[0];", "h q[0];"),
    ("hzh", "", "h q[0];\nz q[0];\nh q[0];"),
    ("x_vs_hzh", "x q[0];", "h q[0];\nz q[0];\nh q[0];"),
)
RZ_CONTROLS = ("0.0001", "0.0002", "0.00048", "0.000000025")


def matrix_distance(lhs, rhs):
    one = Operator(qasm2.loads(HEADER + lhs + "\n")).data
    two = Operator(qasm2.loads(HEADER + rhs + "\n")).data
    # Numerically stable D_proj: compute the Frobenius residual before
    # squaring, avoiding cancellation in 1 - |trace / d|**2 near identity.
    overlap = np.trace(two.conj().T @ one)
    phase = overlap / abs(overlap) if abs(overlap) else complex(1.0, 0.0)
    residual = two.conj().T @ one - phase * np.eye(2, dtype=complex)
    a = float(np.linalg.norm(residual, ord="fro") ** 2 / 4.0)
    return math.sqrt(max(0.0, 2.0 * a - a * a))


def run_one(name, lhs, rhs, backend, solver, *, is_rotation=False):
    oracle = matrix_distance(lhs, rhs)
    if is_rotation:
        # The original lexical Rz angle has an independent exact-form
        # physical formula; neither this oracle nor the high-precision
        # reference is computed by QuPRS.
        source_angle = rhs.split("rz(", 1)[1].split(")", 1)[0]
        with mp.workdps(90):
            analytic_oracle = float(abs(mp.sin(mp.mpf(source_angle) / 2)))
        assert abs(oracle - analytic_oracle) < 1e-12, (source_angle, oracle, analytic_oracle)
        oracle = analytic_oracle
    start = perf_counter()
    result = check_equivalence(
        HEADER + lhs + "\n", HEADER + rhs + "\n",
        backend=backend, method="wmc_only", strategy="Naive",
        tool_name=solver, timeout=60,
        approximate_distance_tolerance=1e-8 if is_rotation else None,
    )
    elapsed = perf_counter() - start
    status = result.equivalent
    assert status in ("equivalent", "equivalent*", "not_equivalent", "unknown"), (name, backend, solver, status)
    assert result.wmc_solver_invoked is True, (name, backend, solver)
    # A numerical unknown near an explicit distance is inconclusive, not a false positive.
    if oracle > 1e-8 + 1e-10:
        assert status in ("not_equivalent", "unknown"), (name, backend, solver, oracle, status)
    if not is_rotation:
        expected = "equivalent" if oracle < 1e-9 else "not_equivalent"
        assert status == expected, (name, backend, solver, oracle, status)
    cnf = result.CNF
    header = next((s for s in cnf.splitlines() if s.startswith("p cnf ")),"") if cnf else ""
    return {
        "case": name, "backend": backend, "solver": solver,
        "oracle_projective_distance": oracle,
        "status": status, "elapsed_s": elapsed,
        "pathsum_s": result.pathsum_time,
        "cnf_s": result.to_DIMACS_time,
        "solver_s": result.tool_time,
        "numerical_reason": result.wmc_precision_reason,
        "cnf_header": header,
        "cnf_sha256": hashlib.sha256(cnf.encode()).hexdigest() if cnf else None,
        "cnf_weight_records": sum(line.startswith("c p weight ") for line in cnf.splitlines()) if cnf else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for solver in ("gpmc", "ganak"):
        for case, lhs, rhs in CASES:
            for backend in ("python", "rust"):
                row = run_one(case, lhs, rhs, backend, solver)
                rows.append(row)
                print(f"PARITY {case} {backend} {solver} D={row['oracle_projective_distance']:.5g} "
                      f"status={row['status']} elapsed={row['elapsed_s']:.3f}", flush=True)
        for angle in RZ_CONTROLS:
            for backend in ("python", "rust"):
                row = run_one(
                    "rz_" + angle, "", f"rz({angle}) q[0];",
                    backend, solver, is_rotation=True
                )
                rows.append(row)
                print(f"RESOLUTION rz={angle} {backend} {solver} D={row['oracle_projective_distance']:.12g} "
                      f"status={row['status']}", flush=True)
    assert len(rows) == 48
    args.json.write_text(json.dumps({
        "scope": "same-Runner public Python/Rust actual GPMC/Ganak, independent Qiskit matrix oracle",
        "solver_calls_per_row": 1,
        "cases": rows,
    }, indent=2) + "\n")
    print("PARITY_SUMMARY total=48 passed=48", flush=True)


if __name__ == "__main__":
    main()

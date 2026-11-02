"""QPE-inexact20 scientific diagnosis, never a benchmark or timing result.

Qiskit statevectors independently check two normalized input states; this is
not a full 20-qubit operator proof. QuPRS invocations are separate, bounded,
and labelled diagnostic. No clock or ad-hoc performance measurements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Statevector

NAME = "qpeinexact_nativegates_ibm_qiskit_opt0_20.qasm"
PAIRS = {"transpiled": "h,ry,rz,cx", "random_rotation": "Random_Rotation"}
MARKER = "QUPRS_WALLTIME_RESULT "  # Legacy name; this script does not time.

def input_state(qubits: int, seed: str) -> Statevector:
    circuit = QuantumCircuit(qubits)
    if seed == "product":
        for i in range(qubits):
            circuit.ry((i % 5 + 1) * 0.23, i)
            circuit.rz((i % 7 - 3) * 0.17, i)
    elif seed != "zero":
        raise ValueError(f"Unknown deterministic seed: {seed}")
    return Statevector.from_instruction(circuit)

def phase_corrected_residual(a: Statevector, b: Statevector) -> dict:
    av, bv = np.asarray(a.data), np.asarray(b.data)
    an, bn = np.linalg.norm(av), np.linalg.norm(bv)
    if not (np.isfinite(an) and np.isfinite(bn)) or not an or not bn:
        raise ValueError("Invalid independent statevector norm")
    av, bv = av / an, bv / bn
    overlap = np.vdot(av, bv)
    phase = overlap / abs(overlap) if abs(overlap) else 1 + 0j
    residual = float(np.linalg.norm(bv - phase * av))
    if not math.isfinite(residual):
        raise ValueError("Non-finite statevector residual")
    return {"relative_phase_rad": float(np.angle(overlap)),
            "phase_corrected_state_residual": residual,
            "normalized_overlap_magnitude": float(abs(overlap)),
            "source_norm": float(an), "counterpart_norm": float(bn)}

def qiskit_probe(root: Path) -> dict:
    folder = root / "benchmarks" / "MQTBench"
    paths = {"original": folder / NAME}
    paths.update({name: folder / directory / NAME
                  for name, directory in PAIRS.items()})
    circuits = {key: qasm2.load(str(path)) for key, path in paths.items()}
    sizes = {key: circuit.num_qubits for key, circuit in circuits.items()}
    if set(sizes.values()) != {20}:
        raise ValueError(f"QPE20 fixture qubit-count mismatch: {sizes}")
    output = {
        "type": "statevector_source_sampling_not_full_unitary_proof",
        "qasm_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest()
                        for name, path in paths.items()},
        "qasm_gate_counts": {name: circuit.size()
                             for name, circuit in circuits.items()},
        "qubits": sizes, "input_probes": {},
        "screening_residual_threshold": 1e-7,
        "certifies_full_unitary_equivalence": False,
        "certifies_approximate_distance_1e_8": False,
    }
    for seed in ("zero", "product"):
        inp = input_state(20, seed)
        original = inp.evolve(circuits["original"])
        output["input_probes"][seed] = {
            variant: phase_corrected_residual(
                original, inp.evolve(circuits[variant]))
            for variant in PAIRS
        }
    output["transpiled_near_on_sampled_states"] = all(
        row["transpiled"]["phase_corrected_state_residual"] <= 1e-7
        for row in output["input_probes"].values()
    )
    output["rotation_detectable_on_sampled_states"] = any(
        row["random_rotation"]["phase_corrected_state_residual"] > 1e-7
        for row in output["input_probes"].values()
    )
    return output

def quprs_probe(root: Path, *, solver_timeout: int = 15, watchdog: int = 35) -> dict:
    harness = root / "benchmarks" / "codspeed" / "solver_case.py"
    probes = {}
    for variant in PAIRS:
        for backend in ("python", "rust"):
            for method in ("hybrid", "wmc_only"):
                name = f"{variant}_{backend}_{method}"
                args = [sys.executable, str(harness), str(root), NAME,
                        "proportional", "gpmc", backend, "0", variant, method]
                env = dict(os.environ, QUPRS_CROSS_METHOD_SOLVER_TIMEOUT=str(solver_timeout))
                try:
                    proc = subprocess.run(
                        args, cwd=root, env=env, text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        timeout=watchdog, check=False, start_new_session=True,
                    )
                except subprocess.TimeoutExpired:
                    probes[name] = {"status": "WATCHDOG_TIMEOUT",
                                    "exit_code": None}
                    continue
                extracted = [line[len(MARKER):] for line in proc.stdout.splitlines()
                             if line.startswith(MARKER)]
                if proc.returncode or len(extracted) != 1:
                    probes[name] = {"status": "PROCESS_ERROR", "exit_code": proc.returncode,
                                    "diagnostic": proc.stderr[-1200:]}
                    continue
                try:
                    observed = json.loads(extracted[0])
                except json.JSONDecodeError:
                    probes[name] = {"status": "UNPARSEABLE_RESULT"}
                    continue
                probes[name] = {"status": "COMPLETED", "exit_code": proc.returncode,
                                **observed}
    return probes

def diagnose(root: Path, sha: str) -> dict:
    oracle = qiskit_probe(root)
    checks = quprs_probe(root)
    findings = {
        "schema": "quprs-qpe20-science-diagnostic-v1",
        "sha": sha, "fixture_source_sha": sha,
        "scientific_certification": "NOT_CERTIFIED_SAMPLED_STATES_ONLY",
        "qiskit_source_screen": oracle,
        "quprs_cross_checks": checks,
        "timing": "NONE_SCIENCE_ONLY_NOT_A_CODSPEED_BENCHMARK",
        "expected_positive_verdict": "equivalent_or_phase",
        "expected_negative_verdict": "not_equivalent",
    }
    positive = [value for key, value in checks.items()
                if key.startswith("transpiled_") and value.get("status") == "COMPLETED"]
    findings["positive_method_agreement"] = (
        len(positive) == 4
        and len({row.get("verdict") for row in positive}) == 1
    )
    findings["science_hold"] = (
        not oracle["transpiled_near_on_sampled_states"]
        or not findings["positive_method_agreement"]
        or any(row.get("verdict") == "not_equivalent" for row in positive)
        or len(positive) != 4
    )
    return findings

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fixture-root", required=True, type=Path)
    p.add_argument("--sha", required=True)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    result = diagnose(a.fixture_root, a.sha)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "science_hold": result["science_hold"],
        "source_near": result["qiskit_source_screen"]["transpiled_near_on_sampled_states"],
        "positive_method_agreement": result["positive_method_agreement"],
        "diagnostic_status": result["scientific_certification"],
    }, sort_keys=True))

if __name__ == "__main__":
    main()

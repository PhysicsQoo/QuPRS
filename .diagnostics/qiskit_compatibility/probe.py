"""Reproducible, non-mutating Qiskit 1.4.6 versus 2.6.1 compatibility audit.

This intentionally does NOT equate small floating operator distance with
mathematically proven equivalence. Each matrix run is an isolated Actions job.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

import numpy as np
import qiskit
from qiskit import QuantumCircuit, QuantumRegister, qasm2, qasm3, transpile
from qiskit.circuit import Parameter
from qiskit.quantum_info import Operator

SEED = 42
LEVELS = (0, 1, 2, 3)
BASIS = ["rz", "sx", "x", "cx"]


def digest(contents):
    return hashlib.sha256(contents).hexdigest()


def make_circuit(name):
    if name == "identity":
        return QuantumCircuit(1)
    if name == "near_rz":
        c = QuantumCircuit(1)
        c.rz(1e-12, 0)
        return c
    if name == "rz_001":
        c = QuantumCircuit(1)
        c.rz(0.001, 0)
        return c
    if name == "phase_u1":
        c = QuantumCircuit(1)
        c.p(0.1, 0)
        c.s(0)
        c.t(0)
        return c
    if name == "h_h":
        c = QuantumCircuit(1)
        c.h(0)
        c.h(0)
        return c
    if name == "registers":
        a, b = QuantumRegister(2, "alpha"), QuantumRegister(1, "beta")
        c = QuantumCircuit(a, b)
        c.h(a[0])
        c.cx(a[0], b[0])
        c.rz(0.1, a[1])
        c.cx(b[0], a[1])
        return c
    if name == "bell":
        c = QuantumCircuit(2)
        c.h(0)
        c.cx(0, 1)
        return c
    if name == "qft4":
        c = QuantumCircuit(4)
        for target in range(4):
            c.h(target)
            for control in range(target + 1, 4):
                c.cp(math.pi / (2 ** (control - target)), control, target)
        return c
    if name == "graph4":
        c = QuantumCircuit(4)
        for qubit in range(4):
            c.h(qubit)
        for i, j in ((0, 1), (1, 2), (2, 3), (3, 0)):
            c.cz(i, j)
        return c
    if name == "global_phase":
        c = QuantumCircuit(1)
        c.rz(0.1, 0)
        c.global_phase = 0.05
        return c
    raise ValueError("Unknown source circuit " + name)


CASES = (
    "identity", "near_rz", "rz_001", "phase_u1", "h_h",
    "registers", "bell", "qft4", "graph4", "global_phase",
)


def matrix_comparison(source, transformed):
    """Float diagnostics; cannot certify near-unitary mathematical equality."""
    left = Operator(source).data
    right = Operator(transformed).data
    if left.shape != right.shape:
        raise ValueError("Transpiler changed number of qubits")
    difference = float(np.linalg.norm(left - right, ord="fro"))
    inner = np.trace(left.conj().T @ right)
    unit = complex(inner / left.shape[0])
    return {
        "matrix_frobenius_difference_float": difference,
        "trace_normalized_real_float": unit.real,
        "trace_normalized_imag_float": unit.imag,
        "up_to_global_phase_trace_magnitude_float": abs(unit),
        "floating_semantics_only": True,
    }


def safe_qasm(source, codec):
    try:
        raw = codec.dumps(source)
        reloaded = codec.loads(raw)
        value = matrix_comparison(source, reloaded)
        return {
            "status": "OK",
            "qasm_sha256": digest(raw.encode("utf-8")),
            "byte_length": len(raw.encode("utf-8")),
            "source_qregs": [(q.name, q.size) for q in source.qregs],
            "imported_qregs": [(q.name, q.size) for q in reloaded.qregs],
            "qreg_partition_preserved": (
                [(q.name, q.size) for q in source.qregs]
                == [(q.name, q.size) for q in reloaded.qregs]
            ),
            "original_global_phase_float": float(source.global_phase),
            "imported_global_phase_float": float(reloaded.global_phase),
            **value,
        }
    except Exception as error:
        return {
            "status": "UNSUPPORTED_OR_ERROR",
            "error_type": type(error).__name__,
            "message": str(error)[:900],
        }


def symbolic_probe():
    p = Parameter("theta")
    c = QuantumCircuit(1)
    c.rz(p, 0)
    c.rz(-p, 0)
    out = {}
    for n, v in (("zero", 0.0), ("small", 1e-12), ("pi_half", math.pi / 2)):
        bound = c.assign_parameters({p: v})
        out[n] = {
            "gate_count": len(bound.data),
            "parameter_count": bound.num_parameters,
            "qasm2": safe_qasm(bound, qasm2),
            "qasm3": safe_qasm(bound, qasm3),
        }
    return out


def source_exact_oracle():
    """Tiny RZ cannot equal Identity up to global phase, without floats."""
    result = {}
    for token in ("0.001", "0.000001", "0.000000001", "0.000000000001"):
        radians = Fraction(token)
        x = radians / 2
        hi = 1 - x * x / 2 + x ** 4 / 24
        assert hi < 1
        result[token] = {
            "exact_decimal_radians": str(radians),
            "normalized_trace_upper_rational": str(hi),
            "mathematically_inequivalent_up_to_global_phase": True,
            "float_trace_magnitude_is_not_a_proof": True,
        }
    return result


def quprs_import_probe():
    """Record direct entrypoint status, not a Solver-based equivalence claim."""
    result = {}
    try:
        import QuPRS
        from QuPRS import check_equivalence
        from QuPRS.utils.util import div_pi
        result["package_path"] = str(Path(QuPRS.__file__).resolve())
        result["api_imports"] = True
        a = QuantumCircuit(1)
        b = QuantumCircuit(1)
        b.h(0)
        b.h(0)
        res = check_equivalence(a, b, method="reduction_rules",
                                backend="python", strategy="Naive", timeout=30)
        result["rr_hh_identity"] = {
            "status": "RETURNED",
            "verdict": res.equivalent,
            "solver_not_required": res.tool_time is None,
        }
        for theta in (1e-3, 1e-9, 1e-12):
            v = div_pi(float(theta))
            result[f"div_pi_{theta}"] = {
                "result": str(v),
                "equals_zero": str(v) == "0",
                "source_nonzero": theta != 0,
                "provenance": "QuPRS float-to-phase conversion, not transpiler",
            }
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__,
                           "message": str(exc)[:1100],
                           "traceback": traceback.format_exc()[-2800:]}
    return result


def test_transpile():
    observations = []
    for name in CASES:
        c = make_circuit(name)
        base = {
            "name": name,
            "num_qubits": c.num_qubits,
            "source_depth": c.depth(),
            "source_ops": dict(c.count_ops()),
            "source_global_phase_float": float(c.global_phase),
            "qasm2": safe_qasm(c, qasm2),
            "qasm3": safe_qasm(c, qasm3),
            "transpiled": [],
        }
        for level in LEVELS:
            started = time.perf_counter()
            try:
                out = transpile(c, basis_gates=BASIS, optimization_level=level,
                                approximation_degree=1.0, seed_transpiler=SEED)
                elapsed = time.perf_counter() - started
                measured = matrix_comparison(c, out)
                base["transpiled"].append({
                    "level": level, "status": "OK",
                    "gates": dict(out.count_ops()),
                    "depth": out.depth(), "gate_count": len(out.data),
                    "global_phase_float": float(out.global_phase),
                    "compilation_wall_seconds_observational": elapsed,
                    "transpiled_qasm2": safe_qasm(out, qasm2),
                    **measured,
                })
            except Exception as exc:
                base["transpiled"].append({
                    "level": level, "status": "ERROR",
                    "error_type": type(exc).__name__,
                    "message": str(exc)[:1400],
                })
        observations.append(base)
        print(json.dumps({"case":name, "qasm2":base["qasm2"]["status"],
                          "qasm3":base["qasm3"]["status"],
                          "levels":[x["status"] for x in base["transpiled"]]}), flush=True)
    return observations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    actual = importlib.metadata.version("qiskit")
    if actual != args.version:
        raise RuntimeError(f"Unexpected Qiskit version: installed={actual} expected={args.version}")
    circuit_results = test_transpile()
    summary = {
        "schema": "qiskit-1x-2x-transpiler-compatibility-observation-v1",
        "qiskit_expected": args.version,
        "qiskit_actual": actual,
        "python": sys.version,
        "platform": platform.platform(),
        "seeds": {"transpile": SEED, "basis_gates": BASIS},
        "matrix_semantics_warning": "Floating operator norm/fidelity cannot prove exact near-identity preservation",
        "native_compiler_semantics_certified": False,
        "cases": circuit_results,
        "exact_radian_oracle": source_exact_oracle(),
        "parameter_expressions": symbolic_probe(),
        "quprs": quprs_import_probe(),
    }
    (out/"observations.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n")
    failures = []
    if not summary["quprs"].get("api_imports"):
        failures.append("QuPRS public API import failed")
    rr = summary["quprs"].get("rr_hh_identity", {})
    if rr.get("verdict") != "equivalent" or not rr.get("solver_not_required"):
        failures.append("RR-only identity control failed")
    for case in circuit_results:
        if any(x["status"] != "OK" for x in case["transpiled"]):
            failures.append("Transpile failure "+case["name"])
        if case["name"] not in ("near_rz", "global_phase"):
            if case["qasm2"]["status"] != "OK" or case["qasm3"]["status"] != "OK":
                failures.append("QASM codec unsupported "+case["name"])
            for x in case["transpiled"]:
                if x["status"] == "OK" and x["matrix_frobenius_difference_float"] > 1e-8:
                    failures.append("Coarse circuit semantic deviation "+case["name"]+"/L"+str(x["level"]))
    summary["blocking_failures"] = failures
    (out/"summary.json").write_text(json.dumps({
        "version":actual, "cases":len(circuit_results),
        "transpiler_levels": len(circuit_results)*len(LEVELS),
        "blocking_failures":failures,
        "status":"PASS" if not failures else "FAIL",
    },sort_keys=True,indent=2)+"\n")
    print("QISKIT_MATRIX", json.dumps({"version":actual,"cases":len(circuit_results),
                                       "blocking_failures":failures}),flush=True)
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())

"""Bounded native Rz source-provenance and reduction-event experiment.

Runs against real QuPRS backends and real GPMC/Ganak subprocesses. Does not
modify solver binaries, production code, approximation thresholds, or RR.
The raw Python CNF weight capture is not a Rust weight observation.
"""
from __future__ import annotations

from contextlib import ExitStack
from decimal import Decimal
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

from mpmath import mp
from qiskit import QuantumCircuit

from QuPRS import check_equivalence, config

OUT = Path("focused-tolerance-evidence")
OUT.mkdir(exist_ok=True)
DEST = OUT / "native-rz-source-rr-observations.jsonl"
API = importlib.import_module("QuPRS.interface.ps2wmc")
RED = importlib.import_module("QuPRS.pathsum.reduction")
MATCH = importlib.import_module("QuPRS.pathsum.pattern_match")

ANGLES = (
    ("sub_f64_defect", "0.00000002", "1e-8"),
    ("resolved_control", "0.0002", "1e-8"),
)
EVIDENCE = []


def emit(row):
    EVIDENCE.append(row)
    with DEST.open("a", encoding="utf8") as dest:
        dest.write(json.dumps(row, default=str, sort_keys=True) + "\n")
    print("NATIVE_RZ_RR " + json.dumps({
        key: row.get(key) for key in
        ("group", "angle_label", "input_kind", "backend", "solver",
         "status", "error", "rr_events")
    }, sort_keys=True), flush=True)


def source_pair(kind, literal):
    empty = QuantumCircuit(1)
    rotated = QuantumCircuit(1)
    rotated.rz(float(Decimal(literal)), 0)
    if kind == "qiskit_object":
        return empty, rotated
    preamble = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    return preamble, preamble + f"rz({literal}) q[0];\n"


def independent_distance(theta_text):
    with mp.workdps(100):
        theta = mp.mpf(theta_text)
        trace_magnitude = abs(mp.cos(theta / 2))
        return {
            "distance": mp.nstr(abs(mp.sin(theta / 2)), 94),
            "trace_magnitude": mp.nstr(trace_magnitude, 94),
            "magnitude_defect": mp.nstr(1 - trace_magnitude, 94),
        }


def inspect_python_weights(left, right, *, solver, distance):
    """Collect Python source phase and exact CNF weight bytes without rerunning Solver."""
    original = API.to_DIMACS
    observed = {}
    def spy(pathsum, filename="wmc.cnf", tool_name="gpmc"):
        observed["phase_repr"] = str(pathsum.P)[:3200]
        observed["phase_sha256"] = hashlib.sha256(str(pathsum.P).encode()).hexdigest()
        result = original(pathsum, filename, tool_name)
        weight_lines = [line for line in result.splitlines()
                        if line.startswith("c p weight ")]
        observed["weight_lines"] = weight_lines[:32]
        observed["weight_lines_total"] = len(weight_lines)
        observed["cnf_sha256"] = hashlib.sha256(result.encode()).hexdigest()
        observed["normalization_log2"] = (
            pathsum.num_qubits + pathsum.num_pathvar / 2
        )
        return result
    with patch.object(API, "to_DIMACS", side_effect=spy):
        result = check_equivalence(
            left, right, method="wmc_only", strategy="Naive",
            tool_name=solver, backend="python", timeout=20,
            approximate_distance_tolerance=float(distance),
        )
    return result, observed


def native_rz():
    errors = []
    for label, angle, epsilon in ANGLES:
        oracle = independent_distance(angle)
        for kind in ("qasm_literal", "qiskit_object"):
            left, right = source_pair(kind, angle)
            source_repr = right if isinstance(right, str) else repr(right.data)
            for backend in ("python", "rust"):
                for solver in ("gpmc", "ganak"):
                    row = {
                        "group": "rz_source_transport",
                        "angle_label": label,
                        "source_angle_decimal": angle,
                        "input_kind": kind, "backend": backend, "solver": solver,
                        "projective_distance_tolerance": epsilon,
                        "oracle": oracle,
                        "source_sha256": hashlib.sha256(source_repr.encode()).hexdigest(),
                        "qiskit_f64_hex": float(Decimal(angle)).hex(),
                        "evidence_scope": "native numeric observations, no solver error certificate",
                        "source_commit": os.getenv("GITHUB_SHA"),
                    }
                    try:
                        begin = time.monotonic()
                        if backend == "python":
                            result, trace = inspect_python_weights(
                                left, right, solver=solver, distance=epsilon
                            )
                            row.update(trace)
                        else:
                            result = check_equivalence(
                                left, right, backend="rust", tool_name=solver,
                                method="wmc_only", strategy="Naive",
                                approximate_distance_tolerance=float(epsilon),
                                timeout=20,
                            )
                            row["rust_raw_weight_trace"] = "NOT_CAPTURED"
                        row.update({
                            "status": result.equivalent,
                            "decision_basis": result.decision_basis,
                            "wmc_numerical_verdict": result.wmc_numerical_verdict,
                            "solver_invoked": result.wmc_solver_invoked,
                            "duration_seconds": time.monotonic() - begin,
                        })
                        if result.equivalent not in {
                            "equivalent", "equivalent*", "not_equivalent",
                            "unknown", "Timeout",
                        }:
                            raise AssertionError("Unsupported outcome " + result.equivalent)
                        if result.equivalent == "Timeout":
                            raise AssertionError("Native Rz timed out inside 20-second budget")
                    except Exception as exc:
                        row["error"] = type(exc).__name__ + ": " + str(exc)[:700]
                        errors.append(row)
                    emit(row)
    return errors


def rr_observation():
    """Record actual matcher firings and normalized phase differences.

    The difference of two expressions is NOT a norm error bound: mod-one phase
    identities are exact, while tolerance-based coefficient deletion is not.
    """
    events = []
    actual_reduce = RED.reduce_expression
    actual_omega = RED.match_omega
    actual_hh = RED.match_HH
    def traced_reduce(expr, *args, **kwargs):
        after = actual_reduce(expr, *args, **kwargs)
        if str(expr) != str(after):
            before_text, after_text = str(expr), str(after)
            events.append({
                "stage": "rr_reduction_normalizer",
                "before_hash": hashlib.sha256(before_text.encode()).hexdigest(),
                "after_hash": hashlib.sha256(after_text.encode()).hexdigest(),
                "before_excerpt": before_text[:180],
                "after_excerpt": after_text[:180],
                "drop_small_requested": kwargs.get("drop_small", True),
                "delta_certified": False,
            })
        return after
    def traced_omega(*args, **kwargs):
        ret = actual_omega(*args, **kwargs)
        if ret[0] is not None:
            events.append({
                "stage": "omega_match", "candidate": str(ret[0]),
                "current_rr_tolerance": str(config.get_tolerance()),
                "error_bound_certified": False,
            })
        return ret
    def traced_hh(*args, **kwargs):
        ret = actual_hh(*args, **kwargs)
        if ret[0] is not None:
            events.append({
                "stage": "HH_match", "candidate": str(ret[0]),
                "current_rr_tolerance": str(config.get_tolerance()),
                "error_bound_certified": False,
            })
        return ret

    left = QuantumCircuit(1)
    repeated = QuantumCircuit(1)
    combined = QuantumCircuit(1)
    for _ in range(20):
        repeated.rz(3e-6, 0)
    combined.rz(0.00006, 0)
    for tolerance in (1e-6, 1e-10):
        for case, right in (("repeated_20", repeated), ("combined", combined)):
            row = {
                "group": "rr_local_approximation",
                "angle_label": case,
                "backend": "python", "solver": "none",
                "rr_tolerance": tolerance,
                "oracle": independent_distance("0.00006"),
                "event_error_model": "unbounded; event trace is not a proof",
                "source_commit": os.getenv("GITHUB_SHA"),
            }
            old = config.get_tolerance()
            events.clear()
            try:
                config.set_tolerance(tolerance)
                with ExitStack() as stack:
                    stack.enter_context(patch.object(RED, "reduce_expression", traced_reduce))
                    stack.enter_context(patch.object(RED, "match_omega", traced_omega))
                    stack.enter_context(patch.object(RED, "match_HH", traced_hh))
                    res = check_equivalence(
                        left, right, backend="python", tool_name="gpmc",
                        method="reduction_rules", strategy="Naive",
                        timeout=20, approximate_distance_tolerance=1e-8,
                    )
                row.update({
                    "status": res.equivalent,
                    "rr_events": len(events),
                    "rr_event_kinds": {kind: sum(e["stage"] == kind for e in events)
                                       for kind in {e["stage"] for e in events}},
                    "rr_events_sample": events[:100],
                    "rr_events_truncated": len(events) > 100,
                    "residual_phase_sha256": hashlib.sha256(
                        str(res.final_pathsum.P).encode()).hexdigest(),
                })
            except Exception as exc:
                row["error"] = type(exc).__name__ + ": " + str(exc)[:700]
            finally:
                config.set_tolerance(old)
            emit(row)
    return [r for r in EVIDENCE if r.get("group") == "rr_local_approximation" and r.get("error")]


def main():
    if DEST.exists():
        DEST.unlink()
    errors = native_rz()
    errors.extend(rr_observation())
    summary = {
        "source_commit": os.environ.get("GITHUB_SHA"),
        "total": len(EVIDENCE), "native_rz": sum(r["group"]=="rz_source_transport" for r in EVIDENCE),
        "rr": sum(r["group"]=="rr_local_approximation" for r in EVIDENCE),
        "errors": len(errors),
        "unknown": sum(r.get("status")=="unknown" for r in EVIDENCE),
        "solver_binaries": ["gpmc", "ganak"],
        "scope": "bounded native observations; no certified arithmetic/RR error interval",
        "limitations": [
            "Python CNF weights captured; Rust source-to-CNF weight trace not yet captured",
            "Qiskit QuantumCircuit float angles do not restore source-literal provenance",
            "RR event records do not estimate a global accumulated numerical error",
            "Stock Ganak's nine-digit stdout resolution remains unchanged",
        ],
    }
    (OUT / "native-rz-source-rr-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print("NATIVE_RZ_RR_SUMMARY "+json.dumps(summary,sort_keys=True),flush=True)
    assert summary["native_rz"] == 16 and summary["rr"] == 4
    if errors:
        raise SystemExit("NATIVE_RZ_RR_EXPERIMENT_HAS_ERRORS: " + str(len(errors)))


if __name__ == "__main__":
    main()

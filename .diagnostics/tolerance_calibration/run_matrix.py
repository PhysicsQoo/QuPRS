"""Source-pinned, read-only numerical tolerance observation matrix.

Does not modify QuPRS defaults or assert an approximate-equivalence policy.
All observations are recorded, including contradictory method verdicts.
"""
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

import qiskit
from qiskit import QuantumCircuit
from QuPRS import check_equivalence, config

OUT = Path("tolerance-calibration-results")
OUT.mkdir(exist_ok=True)
CASES = {
    "rz_0p0002": (0.0002,),
    "rz_0p001": (0.001,),
    "rz_2e_m8": (2e-8,),
    "rz_1e_m12": (1e-12,),
    "rz_100_x_5e_m10": (5e-10,) * 100,
    "rz_100_x_0p0002": (0.0002,) * 100,
    "inverse_cancel": (0.001, -0.001),
}
RECORDS = []


def make_circuits(angles, source_kind):
    if source_kind == "qiskit":
        a, b = QuantumCircuit(1), QuantumCircuit(1)
        for angle in angles:
            b.rz(angle, 0)
        return a, b

    def qasm(sequence):
        return ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
                + ''.join(f'rz({angle!r}) q[0];\n' for angle in sequence))
    return qasm(()), qasm(angles)


def emit(rec):
    RECORDS.append(rec)
    with (OUT / "raw-observations.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
    print("OBSERVATION", json.dumps({
        key: rec.get(key) for key in (
            "case", "source_kind", "backend", "method", "solver",
            "rr_tolerance", "wmc_magnitude_tolerance", "verdict", "error"
        )
    }), flush=True)


def observe(case, *, source_kind="qiskit", backend="python",
            method="reduction_rules", solver="gpmc",
            rr_tolerance=1e-10, wmc_magnitude_tolerance=1e-8):
    angles = CASES[case]
    total_angle = math.fsum(angles)
    # Stable small-angle formula: avoids subtracting a float rounded to 1.
    distance = abs(math.sin(total_angle / 2))
    defect = 2 * math.sin(total_angle / 4)**2
    rec = {
        "case": case,
        "source_kind": source_kind,
        "backend": backend,
        "method": method,
        "solver": solver,
        "strategy": "Naive",
        "rr_tolerance": rr_tolerance,
        "wmc_magnitude_tolerance": wmc_magnitude_tolerance,
        "wmc_phase_tolerance": 1e-8,
        "net_rz_angle_rad": total_angle,
        "ideal_projective_hs_distance": distance,
        "ideal_trace_magnitude_defect": defect,
        "single_gate_max_x_phase_cycle_coefficient": (
            max((abs(angle) for angle in angles), default=0)
            / (2 * math.pi)
        ),
        "qcec_distance_1e_m8_accepts": distance <= 1e-8,
        "current_wmc_defect_1e_m8_accepts": defect < 1e-8,
    }
    previous = config.get_tolerance()
    try:
        config.set_tolerance(rr_tolerance)
        left, right = make_circuits(angles, source_kind)
        start = time.monotonic()
        answer = check_equivalence(
            left, right, backend=backend, method=method,
            strategy="Naive", tool_name=solver,
            timeout=30, wmc_policy="legacy",
            wmc_magnitude_tolerance=wmc_magnitude_tolerance,
            wmc_phase_tolerance=1e-8,
        )
        rec["wall_seconds"] = time.monotonic() - start
        rec["verdict"] = answer.equivalent
        rec["solver_time"] = answer.tool_time
        rec["pathsum_time"] = answer.pathsum_time
        rec["log_wmc"] = answer.log_wmc
        rec["wmc_solver_invoked"] = answer.tool_time is not None
        final = getattr(answer, "final_pathsum", None)
        if final is not None:
            rec["residual_pathsum_excerpt"] = str(final)[:850]
            getter = getattr(final, "get_reduction_counts", None)
            if callable(getter):
                rec["reduction_counts"] = getter()
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        config.set_tolerance(previous)
    emit(rec)


def main():
    (OUT / "environment.json").write_text(
        json.dumps({
            "python": sys.version,
            "qiskit": qiskit.__version__,
            "platform": platform.platform(),
            "source_ref": os.environ.get("GITHUB_SHA"),
            "base_rr_tolerance": config.get_tolerance(),
            "base_wmc_magnitude_tolerance": config.WMC_MAGNITUDE_TOLERANCE,
            "base_wmc_phase_tolerance": config.WMC_PHASE_TOLERANCE,
        }, indent=2) + "\n", encoding="utf-8"
    )

    # 1. Small, source-independent mode × backend comparison.
    for case in ("rz_0p0002", "rz_0p001", "rz_2e_m8",
                 "rz_100_x_5e_m10", "rz_100_x_0p0002",
                 "inverse_cancel"):
        for backend in ("python", "rust"):
            for method in ("reduction_rules", "hybrid", "wmc_only"):
                observe(case, backend=backend, method=method)

    # 2. Isolate whether 'wmc_only' still depends on Python RR coefficient tau.
    for case in ("rz_1e_m12", "rz_100_x_5e_m10"):
        for rr_tau in (1e-12, 1e-10, 1e-9):
            for method in ("reduction_rules", "hybrid", "wmc_only"):
                observe(case, backend="python", method=method,
                        rr_tolerance=rr_tau)

    # 3. Same WMC problem: magnitude threshold versus independent solver.
    for case in ("rz_0p0002", "rz_0p001"):
        for backend in ("python", "rust"):
            for solver in ("gpmc", "ganak"):
                for threshold in (1e-10, 1e-8, 1e-6):
                    observe(case, backend=backend, method="wmc_only",
                            solver=solver, wmc_magnitude_tolerance=threshold)

    # 4. One raw QASM text comparison to separate serialized float ingress.
    for backend in ("python", "rust"):
        for method in ("reduction_rules", "hybrid", "wmc_only"):
            observe("rz_0p0002", source_kind="qasm",
                    backend=backend, method=method)

    summary = {
        "records": len(RECORDS),
        "errors": sum(bool(x.get("error")) for x in RECORDS),
        "observed_definite_mode_disagreements": [],
    }
    by_case = {}
    for item in RECORDS[:36]:
        by_case.setdefault(item["case"], []).append(item)
    for case, records in by_case.items():
        decisions = {
            rec.get("verdict") for rec in records
            if rec.get("verdict") in ("equivalent", "equivalent*", "not_equivalent")
        }
        if "not_equivalent" in decisions and ("equivalent" in decisions or "equivalent*" in decisions):
            summary["observed_definite_mode_disagreements"].append(case)
    (OUT / "summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print("SUMMARY", json.dumps(summary), flush=True)
    # An experiment may observe contradictions, but an entirely failed run is invalid.
    return 0 if len(RECORDS) >= 80 and summary["errors"] < len(RECORDS) // 4 else 1


if __name__ == "__main__":
    raise SystemExit(main())

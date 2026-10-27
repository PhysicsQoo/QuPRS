"""Experiment-only: strict-source legacy vs opt-in numeric distance.

A small source-pinned, non-production prototype of an optional distance policy.
"""
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
from contextlib import contextmanager

from qiskit import QuantumCircuit
from QuPRS import check_equivalence, config, _pathsum_rust
from QuPRS.utils import WMC

OUT = Path("tolerance-calibration-results")
OUT.mkdir(exist_ok=True)
LOG = OUT / "followup-observations.jsonl"
ROWS = []
PREFIX = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'


def emit(**row):
    ROWS.append(row)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    print("FOLLOWUP", json.dumps(row, sort_keys=True, default=str), flush=True)


@contextmanager
def solver_environment(solver):
    key = "QUPRS_" + solver.upper() + "_PATH"
    before = os.environ.get(key)
    with WMC(solver) as executable:
        os.environ[key] = str(executable)
        try:
            yield
        finally:
            if before is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = before


def as_status(result):
    if isinstance(result, dict):
        return {
            "Equivalent": "equivalent",
            "Equivalent (Up to Global Phase)": "equivalent*",
            "Not Equivalent": "not_equivalent",
            "Unknown": "unknown",
        }.get(result.get("status"), result.get("status"))
    return result.equivalent


def query_public(left, right, backend, method, tool, rr_tau=None, mag_tau=1e-8):
    before = config.get_tolerance()
    try:
        if rr_tau is not None:
            config.set_tolerance(rr_tau)
        res = check_equivalence(
            left, right, backend=backend, method=method, strategy="Naive",
            tool_name=tool, timeout=45, wmc_policy="legacy",
            wmc_magnitude_tolerance=mag_tau, wmc_phase_tolerance=1e-8,
        )
        return {
            "verdict": res.equivalent,
            "wmc_called": res.tool_time is not None,
            "log_wmc": res.log_wmc,
            "final_ps": str(res.final_pathsum)[:600] if res.final_pathsum is not None else None,
        }
    finally:
        config.set_tolerance(before)


def strict_and_optin():
    all_cases = (
        ("rz_inside", "rz(0.0002) q[0];", "not_equivalent",
         ((2e-4, "equivalent"), (8e-5, "not_equivalent"))),
        ("rz_outside", "rz(0.001) q[0];", "not_equivalent",
         ((2e-4, "not_equivalent"),)),
        ("boolean_negative", "x q[0];", "not_equivalent",
         ((2e-4, "not_equivalent"),)),
        ("exact_cancel", "rz(0.0002) q[0];\nrz(-0.0002) q[0];", "equivalent",
         ((2e-4, "equivalent"),)),
    )
    for name, gates, strict_expected, approximate_choices in all_cases:
        left, right = PREFIX, PREFIX + gates + "\n"
        strict = query_public(left, right, "rust", "reduction_rules", "gpmc")
        emit(group="strict_regression", case=name, mode="RR", **strict)
        assert strict["verdict"] == strict_expected, (name, strict)
        assert not strict["wmc_called"]
        for eps, expected in approximate_choices:
            for solver in ("gpmc", "ganak"):
                with solver_environment(solver):
                    rr = _pathsum_rust.check_equivalence(
                        left, right, method="reduction_rules",
                        strategy="Naive", tool_name=solver, timeout=45,
                        approximate_distance_tolerance=eps,
                    )
                    hybrid = _pathsum_rust.check_equivalence(
                        left, right, method="hybrid", strategy="Naive",
                        tool_name=solver, timeout=45,
                        approximate_distance_tolerance=eps,
                    )
                    wmc = _pathsum_rust.check_equivalence(
                        left, right, method="wmc_only", strategy="Naive",
                        tool_name=solver, timeout=45,
                        approximate_distance_tolerance=eps,
                    )
                rr_status, h_status, w_status = map(as_status, (rr, hybrid, wmc))
                # RR-only is permitted unknown on phase-only approximate cases.
                rr_expected = strict_expected if name in ("boolean_negative", "exact_cancel") else "unknown"
                emit(
                    group="optin_distance", case=name, solver=solver,
                    distance_tolerance=eps,
                    derived_magnitude_tolerance=eps*eps/(1+math.sqrt(1-eps*eps)),
                    RR=rr_status, Hybrid=h_status, WMC=w_status,
                    hybrid_tool_time=hybrid.get("wmc_solver_time_sec"),
                    expected=expected,
                )
                assert rr_status == rr_expected, (name, eps, rr_status)
                assert h_status == expected and w_status == expected, (name, eps, h_status, w_status)
                if name in ("rz_inside", "rz_outside"):
                    assert hybrid.get("wmc_solver_time_sec") is not None
                if name in ("boolean_negative", "exact_cancel"):
                    assert hybrid.get("wmc_solver_time_sec") is None


def python_coefficient_budget():
    # Each tiny local Rz has x coefficient ~4.77e-7 cycles, < τ_RR=1e-6.
    # But 200 of them create 0.0006 rad: D_HS≈3e-4, defect≈4.5e-8.
    # That is far outside current WMC magnitude τ=1e-8.
    one, many, total = QuantumCircuit(1), QuantumCircuit(1), QuantumCircuit(1)
    for _ in range(200):
        many.rz(3e-6, 0)
    total.rz(0.0006, 0)
    results = {}
    for tau in (1e-10, 1e-6):
        for name, circuit in (("many", many), ("total", total)):
            for method in ("reduction_rules", "wmc_only"):
                v = query_public(one, circuit, "python", method, "gpmc", rr_tau=tau)
                results[(tau, name, method)] = v
                emit(group="python_phase_budget", rr_tolerance=tau,
                     circuit=name, method=method, oracle_distance=math.sin(0.0003),
                     **v)
    # With phase-preserving gate ingestion the RR result is incomplete,
    # not a false proof of equivalence; Hybrid may defer to WMC.
    assert results[(1e-6, "many", "reduction_rules")]["verdict"] == "unknown"
    # WMC-only must preserve cumulative phase independently of RR local tau.
    assert results[(1e-6, "many", "wmc_only")]["verdict"] == "not_equivalent"
    assert results[(1e-6, "total", "wmc_only")]["verdict"] == "not_equivalent"
    assert results[(1e-10, "many", "wmc_only")]["verdict"] == "not_equivalent"
    assert results[(1e-6, "many", "wmc_only")]["log_wmc"] == results[
        (1e-6, "total", "wmc_only")
    ]["log_wmc"]


def solver_precision():
    left, right = QuantumCircuit(1), QuantumCircuit(1)
    for _ in range(60):
        right.h(0)
    for solver in ("gpmc", "ganak"):
        for mag_tau in (1e-10, 5e-10, 1e-9, 2e-9, 1e-8):
            r = query_public(left, right, "python", "wmc_only",
                             solver, rr_tau=1e-10, mag_tau=mag_tau)
            emit(group="solver_precision", solver=solver,
                 mag_tolerance=mag_tau, ideal_trace_norm=1.0, **r)
            if solver == "ganak" and mag_tau in (1e-10, 1e-8):
                assert r["verdict"] == ("not_equivalent" if mag_tau == 1e-10 else "equivalent")


def main():
    (OUT/"followup-environment.json").write_text(json.dumps({
        "GITHUB_SHA": os.getenv("GITHUB_SHA"),
        "python": sys.version, "platform": platform.platform(),
        "baseline_rr": config.get_tolerance(),
    }, indent=2) + "\n")
    strict_and_optin()
    python_coefficient_budget()
    solver_precision()
    out = {
        "records": len(ROWS),
        "groups": {group: sum(r["group"] == group for r in ROWS)
                   for group in sorted(set(r["group"] for r in ROWS))},
        "focused_contract_gate": "PASS",
    }
    (OUT/"followup-summary.json").write_text(json.dumps(out, indent=2) + "\n")
    print("FOLLOWUP_SUMMARY",json.dumps(out),flush=True)


if __name__ == "__main__":
    main()

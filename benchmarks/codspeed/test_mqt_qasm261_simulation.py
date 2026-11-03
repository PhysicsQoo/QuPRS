"""Original 32 Simulation cases PLUS 12 separately identified Qiskit261 CPU cases.

This module only runs as part of CodSpeed. The 12 retired Ganak aliases from pre-release dev were not Solver-inclusive CPU
measurements; remaining cases use GPMC as the deterministic representative.
Real GPMC versus Ganak Solver costs belong in CodSpeed WallTime.

The original MQTBench input QASM
remains unchanged; only the corresponding target is re-transpiled with pinned
Qiskit 2.6.1 Level-0 settings. Ganak near-boundary print limitations are
tracked separately and NEVER reported as a scientific equivalence PASS.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from QuPRS import check_equivalence

from benchmarks.codspeed.simulation_addon import (
    BACKENDS, CORPUS_VERSION, QASM261_CASES, QASM261_COUNT, QASM261_SUITE_ID, SOLVERS,
)

ROOT = Path(__file__).resolve().parents[2] / "benchmarks" / "MQTBench"


def verify_additive_pair(filename, strategy, reverse, solver, backend):
    original = ROOT / filename
    target = ROOT / CORPUS_VERSION / "h,ry,rz,cx" / filename
    if not original.is_file() or not target.is_file():
        raise FileNotFoundError(f"Unpinned QASM261 pair: {original}, {target}")
    left, right = (target, original) if reverse else (original, target)
    return check_equivalence(
        str(left), str(right), method="hybrid", strategy=strategy,
        tool_name=solver, backend=backend,
        timeout=999999 if os.environ.get("CODSPEED_ENV") else 60,
    )


_CASE_PARAMS = [
    pytest.param(case_id, filename, strategy, reverse, solver, backend,
                 id=f"q261_{case_id}_{solver}_{backend}")
    for case_id, filename, strategy, reverse in QASM261_CASES
    for solver in SOLVERS
    for backend in BACKENDS
]
assert len(_CASE_PARAMS) == QASM261_COUNT


@pytest.mark.parametrize(
    "case_id,filename,strategy,reverse,solver,backend", _CASE_PARAMS
)
def test_versioned_mqt_simulation(
    benchmark, case_id, filename, strategy, reverse, solver, backend,
):
    if not os.environ.get("CODSPEED_ENV") and not os.environ.get("QUPRS_QASM261_SIMULATION_SMOKE"):
        pytest.skip("Additive QASM261 Simulation runs under CodSpeed, not general pytest")

    result = benchmark(
        verify_additive_pair, filename, strategy, reverse, solver, backend,
    )
    verdict = str(result.equivalent)
    metadata = {
        "benchmark_suite": QASM261_SUITE_ID,
        "source_corpus": CORPUS_VERSION,
        "case_id": case_id, "solver": solver, "backend": backend,
        "method": "hybrid", "strategy": strategy, "reverse": reverse,
        "observed_verdict": verdict,
        "solver_invoked": str(getattr(result, "wmc_solver_invoked", None)),
        "wmc_precision_reason": str(getattr(result, "wmc_precision_reason", None)),
        "wmc_print_resolution_distance": str(
            getattr(result, "wmc_print_resolution_distance", None)),
    }
    if verdict in {"equivalent", "equivalent*"}:
        metadata["verification_status"] = "EQ_OBSERVED"
    elif verdict == "not_equivalent" and solver == "ganak":
        resolution = getattr(result, "wmc_print_resolution_distance", None)
        tolerance = getattr(result, "approximate_distance_tolerance", 1e-8)
        # Source-matched GPMC positives were independently established in
        # experiment/tacas26-paper-reproduction, 48/48 for these six source
        # circuits. This condition records Ganak output resolution limits,
        # never converts Ganak's actual NEQ to EQ.
        assert getattr(result, "wmc_solver_invoked", False) is True
        assert resolution is not None and resolution > tolerance, (
            "Unexpected Ganak negative without a demonstrated precision limit",
            case_id, backend, verdict, resolution, tolerance,
        )
        metadata["verification_status"] = "CONDITIONAL_GANAK_PRINT_LIMIT"
    else:
        pytest.fail(
            f"Unexpected QASM261 verdict for {case_id}/{backend}/{solver}: "
            f"{verdict} (not a comparable successful Simulation case)"
        )
    benchmark.extra_info.update(metadata)

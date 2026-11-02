"""One EXACT-SHA CodSpeed WallTime repeatability lane, not a daily gate.

The timer comes only from CodSpeed, not from Python or child-tool timestamps.
Every benchmark invocation is captured for scientific stage consistency. The
small in-memory append is part of the measured call; the dominant scoped
workload is a fresh verifier subprocess, and the instrument remains WallTime.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from benchmarks.codspeed.case_registry import (
    REPEATABILITY_CASES, REPEATABILITY_EXPECTATIONS,
)
from benchmarks.codspeed.test_codspeed_candidate_pilot import sample_candidate

SOURCE = "benchmarks/codspeed/test_codspeed_repeatability.py"


@pytest.mark.parametrize(
    "case", REPEATABILITY_CASES,
    ids=[case.id for case in REPEATABILITY_CASES],
)
def test_bounded_same_sha_repeatability(benchmark, case):
    root = Path(os.environ["GITHUB_WORKSPACE"])
    originals = [
        root / "benchmarks" / "MQTBench" / case.qasm,
        root / "benchmarks" / "MQTBench" / "h,ry,rz,cx" / case.qasm,
    ]
    original_hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in originals]
    seen = []

    def one_verification():
        result = sample_candidate(case)
        seen.append({
            key: result.get(key)
            for key in ("status", "verdict", "solver_invoked",
                        "rr_approximate", "wmc_printed_verdict",
                        "wmc_precision_reason", "exit_code")
        })
        return result

    benchmark(one_verification)
    expected_verdict, expected_solver = REPEATABILITY_EXPECTATIONS[case.id]
    consistent = bool(seen) and all(
        row["status"] == "COMPLETED"
        and row["verdict"] == expected_verdict
        and row["solver_invoked"] is expected_solver
        and row["exit_code"] == 0
        for row in seen
    )
    # Do not treat normal solver arithmetic precision diagnostics as a
    # certified proof; their provenance must be preserved per invocation.
    precision_reasons = sorted({
        row["wmc_precision_reason"] for row in seen
        if row["wmc_precision_reason"] is not None
    })
    record = {
        "case": case.id, "qasm_sha256": original_hashes, "sha": os.environ["HEAD_SHA"],
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "method": case.method, "strategy": case.strategy, "backend": case.backend,
        "solver": case.solver, "reverse": case.reverse,
        "expected_verdict": expected_verdict, "expected_solver_invoked": expected_solver,
        "solver_timeout_s": case.solver_timeout_s,
        "process_group_watchdog_s": case.watchdog_s,
        "instrument": "CodSpeed WallTime",
        "observed_invocations_including_instrument_warmup": len(seen),
        "all_invocations_scientifically_consistent": consistent,
        "observations": seen,
        "precision_reasons": precision_reasons,
        "science_status": ("SOURCE_ORACLE_PASSED_AND_STAGE_CONSISTENT"
                           if consistent else "STAGE_OR_VERDICT_INCONSISTENT"),
        "performance_status": "REPEATABILITY_DIAGNOSTIC_NOT_RELEASE_GATE",
    }
    benchmark.extra_info.update({
        "source_sha": record["sha"], "case": case.id, "qasm_sha256": original_hashes,
        "observed_invocations": len(seen),
        "science_status": record["science_status"],
        "precision_reasons": precision_reasons,
        "measurement_scope": "fresh_subprocess_full_request_walltime",
    })
    artifact = Path(os.environ["RUNNER_TEMP"]) / "repeatability-science.jsonl"
    with artifact.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, sort_keys=True) + "\n")
    assert consistent, (
        f"Source-pinned {case.id} changed expected verdict/Solver stage or "
        f"did not complete within watchdog bounds; inspect {artifact}"
    )

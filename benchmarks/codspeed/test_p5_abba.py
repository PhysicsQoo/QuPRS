"""Opt-in, exact-source P5 ABBA counterbalanced CodSpeed WallTime protocol.

Four unique benchmark identities for each case and block: A1 (dev), B1 (PR),
B2 (PR), A2 (dev). Three blocks per case provide independent A/A drift
witnesses on the SAME runner. Uses the official CodSpeed clock exclusively.
No Stopwatch/time.time/perf_counter measurement, no new verifier wrapper.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from benchmarks.codspeed.case_registry import WALLTIME_CASES
from benchmarks.codspeed.test_pr_solver_walltime import execute_source_pinned_case

P5_CASES = frozenset({
    "vqe4_gpmc", "qaoa7_gpmc", "qft16_gpmc", "vqe4_gpmc_python"
})
P5_CASE_ROWS = tuple(case for case in WALLTIME_CASES if case[0] in P5_CASES)
assert len(P5_CASE_ROWS) == 4
POSITIONS = (("A1", "base"), ("B1", "head"), ("B2", "head"), ("A2", "base"))
BLOCKS = (0, 1, 2)
PARAMS = [
    pytest.param(case, block, pos, revision,
                 id=f"{case[0]}-block{block}-{pos}")
    for case in P5_CASE_ROWS
    for block in BLOCKS
    for pos, revision in POSITIONS
]


@pytest.mark.parametrize("case,block,position,revision", PARAMS)
def test_codspeed_p5_abba(benchmark, case, block, position, revision):
    seen = []

    def one_request():
        # Only the real verification is timed by CodSpeed. Capturing a tiny
        # result dictionary is needed to audit ALL invocations incl. warmup.
        result = execute_source_pinned_case(revision, case)
        seen.append({
            "verdict": result.get("verdict"),
            "solver_invoked": result.get("solver_invoked"),
            "wmc_precision_reason": result.get("wmc_precision_reason"),
            "approximate_distance_tolerance": result.get(
                "approximate_distance_tolerance"),
        })
        return result

    benchmark(one_request)
    if not seen or any(
        obs.get("solver_invoked") is not True
        or obs.get("verdict") not in {"equivalent", "equivalent*"}
        for obs in seen
    ):
        raise AssertionError(f"invalid Solver stage/verdict: {case[0]} {position}")

    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    qasm_paths = [
        workspace / "benchmarks" / "MQTBench" / case[1],
        workspace / "benchmarks" / "MQTBench" / "h,ry,rz,cx" / case[1],
    ]
    qasm_hashes = [hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in qasm_paths]
    witness = {
        "qasm_sha256": qasm_hashes,
        "case": case[0], "block": block, "position": position,
        "revision": revision,
        "sha": os.environ["BASE_SHA" if revision == "base" else "HEAD_SHA"],
        "fixture_sha": os.environ["HEAD_SHA"],
        "method": "hybrid", "backend": case[5], "solver": case[3],
        "strategy": case[2], "reverse": case[4],
        "invocations": len(seen),
        "observations": seen,
        "science_status": "CONSISTENT_WITHIN_POSITION",
    }
    benchmark.extra_info.update({
        "case": case[0], "block": block, "position": position,
        "source_sha": witness["sha"],
        "fixture_sha": witness["fixture_sha"],
        "solver_invoked": True,
        "verdict": seen[-1]["verdict"],
        "invocations": len(seen),
        "scope": "entire_verifier_plus_solver_fresh_subprocess",
    })
    with (Path(os.environ["RUNNER_TEMP"]) / "p5-abba-provenance.jsonl").open(
        "a", encoding="utf-8"
    ) as file:
        file.write(json.dumps(witness, sort_keys=True) + "\n")

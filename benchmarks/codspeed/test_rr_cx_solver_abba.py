"""Isolated Bra-CX exact-specialization Solver-inclusive CodSpeed ABBA.

Same QASM, same Hybrid, GPMC and solver settings for prior guarded-XOR
Base versus direct Bra-CX HEAD. The Rust QFT16/VQE4 cases exercise the new
code; the VQE4 Python case is a same-host non-Rust drift control.

This test deliberately does not replace any existing protected benchmark ID.
The native QPE-exact8 RR-terminating case belongs to the independent native
RR CodSpeed and science gate, NOT to a forced Solver-inclusive workload.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from benchmarks.codspeed.case_registry import WALLTIME_CASES
from benchmarks.codspeed.test_pr_solver_walltime import execute_source_pinned_case

CASE_IDS = frozenset({"qft16_gpmc", "vqe4_gpmc", "vqe4_gpmc_python"})
CASES = tuple(row for row in WALLTIME_CASES if row[0] in CASE_IDS)
assert {row[0] for row in CASES} == CASE_IDS
POSITIONS = (("A1", "base"), ("B1", "head"), ("B2", "head"), ("A2", "base"))
BLOCKS = (0, 1, 2)
PARAMS = [
    pytest.param(case, block, position, revision,
                 id=f"{case[0]}-block{block}-{position}")
    for case in CASES
    for block in BLOCKS
    for position, revision in POSITIONS
]


@pytest.mark.parametrize("case,block,position,revision", PARAMS)
def test_codspeed_rr_cx_solver_abba(benchmark, case, block, position, revision):
    seen = []

    def request():
        # Existing source-pinned harness runs one complete verifier with
        # fresh subprocess + GPMC; CodSpeed alone owns the timer.
        result = execute_source_pinned_case(revision, case)
        seen.append({
            "verdict": result.get("verdict"),
            "solver_invoked": result.get("solver_invoked"),
            "rr_approximate": result.get("rr_approximate"),
            "wmc_precision_reason": result.get("wmc_precision_reason"),
            "wmc_numerical_verdict": result.get("wmc_numerical_verdict"),
            "wmc_printed_verdict": result.get("wmc_printed_verdict"),
            "wmc_log_wmc": result.get("wmc_log_wmc"),
            "wmc_expected_log2": result.get("wmc_expected_log2"),
            "effective_rr_tolerance": result.get("effective_rr_tolerance"),
            "effective_distance_tolerance": result.get("effective_distance_tolerance"),
            "effective_phase_tolerance": result.get("effective_phase_tolerance"),
            "effective_gpmc_digits": result.get("effective_gpmc_digits"),
        })
        return result

    benchmark(request)
    if not seen or any(
        obs["solver_invoked"] is not True
        or obs["verdict"] not in {"equivalent", "equivalent*"}
        for obs in seen
    ):
        raise AssertionError(f"Solver-stage/verdict mismatch: {case[0]} {position}")

    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    qasm_paths = [
        workspace / "benchmarks" / "MQTBench" / case[1],
        workspace / "benchmarks" / "MQTBench" / "h,ry,rz,cx" / case[1],
    ]
    qasm_sha256 = [hashlib.sha256(f.read_bytes()).hexdigest() for f in qasm_paths]
    provenance = {
        "qasm_sha256": qasm_sha256,
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
        "source_sha": provenance["sha"], "fixture_sha": provenance["fixture_sha"],
        "solver_invoked": True, "verdict": seen[-1]["verdict"],
        "invocations": len(seen),
        "scope": "full_verifier_and_real_solver_in_fresh_subprocess",
        "experimental_family": "bra_cx_direct_vs_guarded_xor",
    })
    with (Path(os.environ["RUNNER_TEMP"]) / "rr-cx-solver-abba-provenance.jsonl").open(
        "a", encoding="utf-8"
    ) as output:
        output.write(json.dumps(provenance, sort_keys=True) + "\n")

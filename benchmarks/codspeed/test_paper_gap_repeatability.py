"""P1 same-SHA CodSpeed WallTime, five distinct literature-grounded cases.

No independent timers: subprocess startup, RR and Solver are all included in
the CodSpeed WallTime region. 5 measured rounds and all per-call stages/verdicts
are audited independently of a full 20q unitary proof.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

from benchmarks.codspeed.case_registry import PAPER_GAP_PILOT_CASES
from benchmarks.codspeed.test_codspeed_candidate_pilot import sample_candidate

EXPECT = {
    "graphstate64_positive": ("equivalent*", False),
    "qaoa11_positive": ("equivalent*", True),
    "qwalk4_positive": ("equivalent*", False),
    "qwalk4_negative": ("not_equivalent", True),
    "qpeinexact20_negative": ("not_equivalent", True),
}
CASES = tuple(case for case in PAPER_GAP_PILOT_CASES if case.id in EXPECT)
assert len(CASES) == len(EXPECT) == 5

@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_paper_gap_repeatability(benchmark, case):
    root = Path(os.environ["GITHUB_WORKSPACE"])
    counterpart = ("Random_Rotation" if case.pair_variant == "random_rotation"
                   else "h,ry,rz,cx")
    paths = [root / "benchmarks" / "MQTBench" / case.qasm,
             root / "benchmarks" / "MQTBench" / counterpart / case.qasm]
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    seen = []
    def one():
        value = sample_candidate(case)
        seen.append({key: value.get(key) for key in (
            "status", "exit_code", "verdict", "solver_invoked", "rr_approximate",
            "wmc_precision_reason", "wmc_printed_verdict",
            "wmc_numerical_verdict", "wmc_print_resolution_distance",
            "approximate_distance_tolerance")})
        return value
    benchmark(one)
    verdict, invoked = EXPECT[case.id]
    stable = bool(seen) and all(
        row["status"] == "COMPLETED" and row["exit_code"] == 0
        and row["verdict"] == verdict
        and row["solver_invoked"] is invoked
        for row in seen
    )
    record = {
        "schema": "quprs-paper-gap-repeatability-provenance-v1",
        "case": case.id, "sha": os.environ["HEAD_SHA"],
        "source_sha256": hashes, "pair_variant": case.pair_variant,
        "backend": case.backend, "solver": case.solver, "method": case.method,
        "expected_verdict": verdict, "expected_solver_invoked": invoked,
        "observed_invocations": len(seen), "observations": seen,
        "stage_and_verdict_stable": stable,
        "scientific_status": "SOURCE_ORACLE_NOT_FULLY_CERTIFIED",
        "performance_certified": False,
    }
    benchmark.extra_info.update({
        "source_sha": record["sha"], "case": case.id,
        "observed_invocations": len(seen),
        "solver_invoked": invoked, "verdict": verdict,
        "scientific_status": record["scientific_status"],
    })
    with (Path(os.environ["RUNNER_TEMP"]) / "paper-gap-repeatability-science.jsonl").open(
            "a", encoding="utf-8") as file:
        file.write(json.dumps(record, sort_keys=True) + "\n")
    assert stable, f"{case.id}: unexpected Solver stage, verdict or timeout"

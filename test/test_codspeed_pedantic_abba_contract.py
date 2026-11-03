"""Research-only light contract for pytest-codspeed 5.0.4 WallTime pedantic.

No QuPRS import, Rust build, GPMC or Ganak. Mock solver invocations are counted
separately from CodSpeed target invocations; measurements are officially timed.
A distinct pytest identity per position establishes the exact ABBA/BAAB order.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

CASES = ("hybrid", "wmc_only")
BLOCKS = (
    ("abba", ("A1", "B1", "B2", "A2")),
    ("baab", ("B1", "A1", "A2", "B2")),
)
PARAMS = [
    pytest.param(case, block, position, id=f"{case}-{block}-{position}")
    for case in CASES
    for block, positions in BLOCKS
    for position in positions
]


def test_counterbalanced_schedule_is_valid():
    # Pure source guard: each block has two A and two B, with balance at edges.
    assert len(PARAMS) == len(CASES) * len(BLOCKS) * 4 == 16
    for _, positions in BLOCKS:
        assert len(positions) == 4
        assert sum(p.startswith("A") for p in positions) == 2
        assert sum(p.startswith("B") for p in positions) == 2
    assert BLOCKS[0][1] == ("A1", "B1", "B2", "A2")
    assert BLOCKS[1][1] == ("B1", "A1", "A2", "B2")


@pytest.mark.parametrize("case,block,position", PARAMS)
def test_codspeed_single_position(benchmark, case, block, position):
    """One officially timed call; plugin's unmeasured return call uses cache."""
    assert os.environ.get("QUPRS_CONTRACT_TRACE"), "Run the dedicated light CI"
    trace_path = Path(os.environ["QUPRS_CONTRACT_TRACE"])
    revision = "base" if position.startswith("A") else "head"
    counter = {"target": 0, "solver": 0}
    cache = []

    def synthetic_verifier():
        counter["target"] += 1
        if cache:
            return cache[0]
        counter["solver"] += 1
        # A tiny deterministic stand-in; never imports or executes QuPRS.
        value = sum(n * n for n in range(512))
        result = {
            "verdict": "equivalent",
            "solver_invoked": True,
            "case": case,
            "revision": revision,
            "value": value,
        }
        cache.append(result)
        return result

    result = benchmark.pedantic(
        synthetic_verifier, rounds=1, iterations=1, warmup_rounds=0
    )
    # In v5.0.4 measure_pedantic runs the target once inside CodSpeed timing,
    # then once outside timing to obtain the result. Fail closed if it changes.
    assert result is cache[0]
    assert counter == {"target": 2, "solver": 1}
    record = {
        "case": case,
        "block": block,
        "position": position,
        "revision": revision,
        "target_calls": counter["target"],
        "synthetic_solver_calls": counter["solver"],
        "verdict": result["verdict"],
        "value": result["value"],
        "source": "pytest-codspeed==5.0.4 pedantic/walltime",
    }
    with trace_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")

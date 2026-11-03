#!/usr/bin/env python3
"""Audit the lightweight official pytest-codspeed single-position ABBA API test.

Only validates execution counts and instrumentation metadata. Never interprets
the synthetic timing as a QuPRS or Solver performance benchmark.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

CASES = ("hybrid", "wmc_only")
BLOCKS = (
    ("abba", ("A1", "B1", "B2", "A2")),
    ("baab", ("B1", "A1", "A2", "B2")),
)


def validate(measurement: dict, observations: list[dict]) -> dict:
    expected = [(case, block, position)
                for case in CASES for block, positions in BLOCKS
                for position in positions]
    actual = [(row["case"], row["block"], row["position"]) for row in observations]
    if actual != expected:
        raise AssertionError(f"wrong actual pytest execution order: {actual}")
    if measurement.get("instrument", {}).get("type") != "walltime":
        raise AssertionError("actual CodSpeed WallTime instrument required")
    rows = measurement.get("benchmarks", [])
    if len(rows) != len(expected):
        raise AssertionError(f"wanted exactly {len(expected)} measured URIs, got {len(rows)}")
    measured = []
    for item in rows:
        uri = item["uri"]
        prefix = "test_codspeed_single_position["
        if prefix not in uri or not uri.endswith("]"):
            raise AssertionError(f"unexpected CodSpeed measured URI: {uri}")
        name = uri.rsplit(prefix, 1)[1][:-1]
        matches = [(case, block, position)
                   for case, block, position in expected
                   if name == f"{case}-{block}-{position}"]
        if len(matches) != 1:
            raise AssertionError(f"invalid position identity: {name}")
        stats = item["stats"]
        if (stats["rounds"], stats["iter_per_round"], stats["warmup_iters"]) != (1, 1, 0):
            raise AssertionError(f"not one measured, un-warmed official round: {name}: {stats}")
        if not math.isfinite(stats["median_ns"]) or stats["median_ns"] <= 0:
            raise AssertionError(f"invalid official WallTime: {name}")
        measured.append(matches[0])
    if measured != expected:
        raise AssertionError(f"official measurement order mismatch: {measured}")
    for event in observations:
        if event["revision"] != ("base" if event["position"].startswith("A") else "head"):
            raise AssertionError(f"revision mapping corrupt: {event}")
        if (event["target_calls"], event["synthetic_solver_calls"]) != (2, 1):
            raise AssertionError(f"incorrect pedantic extra return call guard: {event}")
        if event["verdict"] != "equivalent" or event["value"] != 44608256:
            # Calculated expected sum of squares for range(512).
            raise AssertionError(f"incorrect deterministic fake return: {event}")
    return {
        "schema": "quprs-pedantic-abba-light-api-contract-v1",
        "status": "PASS",
        "pytest_codspeed_version": "5.0.4",
        "actual_walltime_instrument": True,
        "official_position_measurements": len(rows),
        "official_measured_rounds_per_position": 1,
        "official_warmup_rounds_per_position": 0,
        "synthetic_solver_calls_per_position": 1,
        "plugin_target_calls_per_position": 2,
        "expected_schedule": [
            {"case": case, "block": block, "position": pos}
            for case, block, pos in expected
        ],
        "sciencedata_or_real_solver": False,
        "performance_certified": False,
        "note": "No QuPRS, no native solver, no actual dev/HEAD benchmark; synthetic contract only",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--measurements-dir", type=Path, required=True)
    p.add_argument("--trace", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    files = list((a.measurements_dir / "results").glob("*.json"))
    if len(files) != 1:
        raise AssertionError(f"need exactly one CodSpeed result JSON, got {files}")
    data = json.loads(files[0].read_text(encoding="utf-8"))
    events = [
        json.loads(line) for line in a.trace.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    result = validate(data, events)
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("QOO170_PEDANTIC_ABBA_LIGHT_CONTRACT_PASS")
    print(json.dumps({key: value for key, value in result.items()
                      if key != "expected_schedule"}, sort_keys=True))


if __name__ == "__main__":
    main()

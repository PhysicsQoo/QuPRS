#!/usr/bin/env python3
"""Read only official CodSpeed WallTime and source-pinned real Solver provenance.

No custom timers and no performance release threshold. The recorded per-position
single official round is the unit of the counterbalanced paired diagnostic.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import statistics
from pathlib import Path

METHODS = ("hybrid", "wmc_only")
BLOCKS = (
    ("ABBA", ("A1", "B1", "B2", "A2")),
    ("BAAB", ("B1", "A1", "A2", "B2")),
    ("BAAB", ("B1", "A1", "A2", "B2")),
    ("ABBA", ("A1", "B1", "B2", "A2")),
)
ID = re.compile(r"test_qoo170_real_single_position\[(hybrid|wmc_only)-block([0-3])-(A1|B1|B2|A2)\]$")


def produce(measurements: dict, provenance: list[dict],
            prewarm: list[dict], base_sha: str, head_sha: str) -> dict:
    if len(base_sha) != 40 or len(head_sha) != 40 or base_sha == head_sha:
        raise ValueError("expected two different, exact 40-hex verifier source SHAs")
    if measurements.get("instrument", {}).get("type") != "walltime":
        raise ValueError("official CodSpeed WallTime instrument required")
    expected = [(m, b, p) for m in METHODS
                for b, (_, positions) in enumerate(BLOCKS) for p in positions]
    observed_order = [(x["method"], x["block"], x["position"]) for x in provenance]
    if observed_order != expected:
        raise ValueError("real Solver provenance execution order differs from planned ABBA/BAAB")

    if len(prewarm) != 4 or sorted((x["method"], x["revision"])
                                  for x in prewarm) != sorted(
                                      (m, v) for m in METHODS for v in ("base", "head")
                                  ):
        raise ValueError("missing or duplicated non-timed prewarm")
    if any(x.get("kind") != "prewarm" or x.get("verdict") != "not_equivalent"
           for x in prewarm):
        raise ValueError("invalid source-checked prewarm verdict")

    measurements_by_key = {}
    for item in measurements.get("benchmarks", []):
        uri = item.get("uri", "")
        match = ID.search(uri)
        if not match:
            raise ValueError(f"unexpected measured benchmark URI {uri}")
        key = (match[1], int(match[2]), match[3])
        if key in measurements_by_key:
            raise ValueError(f"duplicate official CodSpeed benchmark URI {key}")
        stats = item.get("stats", {})
        if (stats.get("rounds"), stats.get("iter_per_round"),
                stats.get("warmup_iters")) != (1, 1, 0):
            raise ValueError(f"not precisely one official measured invocation {key}: {stats}")
        val = stats.get("median_ns")
        if not isinstance(val, (int, float)) or not math.isfinite(val) or val <= 0:
            raise ValueError(f"missing official measured WallTime {key}")
        measurements_by_key[key] = val

    if set(measurements_by_key) != set(expected):
        raise ValueError(f"incomplete actual 32 CodSpeed measurements: "
                         f"missing {set(expected) - set(measurements_by_key)}")

    reference_hashes = None
    for row in provenance:
        if row["revision"] != ("base" if row["position"].startswith("A") else "head"):
            raise ValueError(f"wrong source revision for position {row}")
        if row["revision_sha"] != (base_sha if row["revision"] == "base" else head_sha):
            raise ValueError(f"wrong verifier SHA for {row}")
        if row["fixture_sha"] != head_sha:
            raise ValueError(f"wrong fixture SHA for {row}")
        if row.get("real_solver_calls") != 1 or row.get("target_calls") != 2:
            raise ValueError(f"unmeasured duplicate real Solver call {row}")
        x = row["observation"]
        if (x.get("solver_invoked") is not True or x.get("verdict") != "not_equivalent"
                or x.get("method") != row["method"] or x.get("solver") != "gpmc"
                or x.get("effective_gpmc_digits") != 90):
            raise ValueError(f"wrong science or precision contract {row}")
        signature = row["source_sha256"], row["target_sha256"]
        if reference_hashes is None:
            reference_hashes = signature
        elif signature != reference_hashes:
            raise ValueError("QASM source/target mutated inside ABBA study")

    result = {
        "schema": "quprs-qoo170-real-solver-true-pedantic-abba-v1",
        "instrument": "CodSpeed WallTime",
        "base_sha": base_sha,
        "head_sha": head_sha,
        "qasm_sha256_pair": list(reference_hashes),
        "all_positions_have_one_official_measured_round": True,
        "all_positions_have_one_real_GPMC_solver_call": True,
        "all_positions_have_expected_NEQ_verdict": True,
        "prewarm_real_solver_calls": len(prewarm),
        "official_measured_positions": len(expected),
        "real_measured_solver_calls": len(expected),
        "plugin_extra_return_calls_reuse_cache": True,
        "numeric_policy": {"rr": 1e-10, "distance": 1e-8,
                           "phase": 1e-8, "gpmc_digits": 90},
        "performance_status": "OBSERVATIONAL_NOT_CERTIFIED",
        "science_status": "SOURCE_AND_SOLVER_PROVENANCE_PASS",
        "no_fixed_regression_gate": True,
        "cases": [],
    }
    for method in METHODS:
        block_rows = []
        for block, (sequence, _) in enumerate(BLOCKS):
            n = {p: measurements_by_key[method, block, p] / 1e6
                 for p in ("A1", "A2", "B1", "B2")}
            abase = (n["A1"] + n["A2"]) / 2
            bhead = (n["B1"] + n["B2"]) / 2
            percent_change = 100 * (bhead / abase - 1)
            baseline_drift_pct = 100 * (n["A2"] / n["A1"] - 1)
            head_pair_drift_pct = 100 * (n["B2"] / n["B1"] - 1)
            block_rows.append({
                "block": block, "sequence": sequence, "position_ms": n,
                "base_mean_of_two_positions_ms": abase,
                "head_mean_of_two_positions_ms": bhead,
                "head_vs_base_percent": percent_change,
                "a2_vs_a1_percent": baseline_drift_pct,
                "b2_vs_b1_percent": head_pair_drift_pct,
            })
        effects = [x["head_vs_base_percent"] for x in block_rows]
        drifts = [abs(x["a2_vs_a1_percent"]) for x in block_rows]
        result["cases"].append({
            "case": "qaoa7_negative_" + method, "method": method, "blocks": block_rows,
            "median_block_head_vs_base_percent": statistics.median(effects),
            "min_block_effect_percent": min(effects),
            "max_block_effect_percent": max(effects),
            "max_abs_base_AA_drift_percent": max(drifts),
            "direction_consistent_across_blocks": (
                all(x >= 0 for x in effects) or all(x <= 0 for x in effects)
            ),
            "formal_regression_claim": False,
        })
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--measurements", type=Path, required=True)
    p.add_argument("--provenance", type=Path, required=True)
    p.add_argument("--prewarm", type=Path, required=True)
    p.add_argument("--base-sha", required=True)
    p.add_argument("--head-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    data = json.loads(args.measurements.read_text())
    science = [json.loads(l) for l in args.provenance.read_text().splitlines() if l]
    prewarm = json.loads(args.prewarm.read_text())
    result = produce(data, science, prewarm, args.base_sha, args.head_sha)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("QOO170_REAL_QAOA7_ABBA_SCIENCE_AND_WALLTIME_PASS")
    for case in result["cases"]:
        print(case["case"], case["median_block_head_vs_base_percent"],
              case["max_abs_base_AA_drift_percent"])


if __name__ == "__main__":
    main()

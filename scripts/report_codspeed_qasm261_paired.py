#!/usr/bin/env python3
"""Fail-closed source/stage validation of paired CodSpeed WallTime evidence.

No time() or process subprocess timing. All durations are official
pytest-codspeed's instrumented statistics, in nanoseconds.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from statistics import median
from benchmarks.codspeed.qasm261_paired_cases import GPMC_PAIRS, POSITIONS

PATTERN = re.compile(r"test_qasm261_solver_pair\[([a-z0-9_]+)-(A1|B1|B2|A2)\]$")
EXPECTED = {row[0]: row for row in GPMC_PAIRS}
ORDER = {p: rev for p, rev in POSITIONS}

def produce(data: dict, records: list[dict], *,
            base_sha: str, head_sha: str, fixture_sha: str, audit: dict) -> dict:
    if data.get("instrument", {}).get("type") != "walltime":
        raise ValueError("Official CodSpeed WallTime is required")
    if len(EXPECTED) != 5 or len(ORDER) != 4:
        raise ValueError("changed candidate matrix")
    required = {(case, p) for case in EXPECTED for p in ORDER}
    times = {}
    for entry in data.get("benchmarks", []):
        uri = entry.get("uri", "")
        match = PATTERN.search(uri)
        if not match:
            raise ValueError(f"Unexpected versioned URI: {uri}")
        key = match[1], match[2]
        if key in times:
            raise ValueError(f"Duplicate measured URI: {key}")
        stats = entry["stats"]
        if stats.get("rounds", 0) < 3 or stats.get("iter_per_round", 0) < 1:
            raise ValueError(f"Insufficient CodSpeed measured rounds: {key}, {stats}")
        if any(not isinstance(stats.get(f), (int, float)) or
               not math.isfinite(stats[f]) or stats[f] <= 0
               for f in ("median_ns", "mean_ns", "min_ns")):
            raise ValueError(f"Invalid official CodSpeed duration: {key}")
        if not isinstance(stats.get("stdev_ns"), (int, float)) or stats["stdev_ns"] < 0:
            raise ValueError(f"Invalid sample variance: {key}")
        times[key] = stats
    science = {}
    for row in records:
        key = row.get("case"), row.get("position")
        if key in science:
            raise ValueError(f"Duplicate source/science record: {key}")
        science[key] = row
    if set(times) != required or set(science) != required:
        raise ValueError(f"Incomplete paired matrix: missing times={required-set(times)}, "
                         f"missing science={required-set(science)} "
                         f"extra times={set(times)-required}, extra science={set(science)-required}")

    audit_by_file = {x["file"]: x for x in audit["mqt"]}
    results = []
    for case in EXPECTED:
        name, file, strategy, reverse, variant, expected = EXPECTED[case]
        archived = audit_by_file[file]
        expected_hashes = [
            archived["source"]["sha256"] if "sha256" in archived["source"] else None,
            archived["qiskit261_negative" if variant == "random_rotation"
                     else "qiskit261_positive"]["sha256"],
        ]
        # Archived legacy source is pinned as Git blob SHA1, whereas the
        # verifier uses SHA256. The same SOURCE hash is independently
        # compared across all cells; the generated target is manifest-pinned.
        fingerprints = set()
        status = []
        all_positive = []
        for position, revision in POSITIONS:
            w = science[case, position]
            if (w["revision"] != revision or w["position"] != position
                    or w["sha"] != (base_sha if revision == "base" else head_sha)
                    or w["fixture_sha"] != fixture_sha
                    or w.get("instrument") != "CodSpeed WallTime"
                    or w["method"] != "hybrid" or w["solver"] != "gpmc"
                    or w["backend"] != "rust" or w["strategy"] != strategy
                    or w["reverse"] != reverse or w["variant"] != variant
                    or w["expected_binary"] != expected
                    or len(w.get("fixture_sha256", [])) != 2
                    or w["fixture_sha256"][1] != expected_hashes[1]
                    or w["observed_invocations"] < 3
                    or len(w["observations"]) != w["observed_invocations"]):
                raise ValueError(f"Invalid SHA/source/method metadata: {case}/{position}")
            fingerprints.add(tuple(w["fixture_sha256"]))
            for observation in w["observations"]:
                good = (observation.get("solver_invoked") is True
                        and observation.get("qasm_corpus") == "qiskit-2.6.1-opt0"
                        and observation.get("pair_variant") == variant
                        and observation.get("method") == "hybrid"
                        and observation.get("distance") == 1e-8
                        and observation.get("rr_tolerance") == 1e-10
                        and observation.get("phase_tolerance") == 1e-8
                        and observation.get("gpmc_digits") == 30
                        and (observation.get("verdict") in
                             (("equivalent", "equivalent*") if expected == "equivalent"
                              else ("not_equivalent",))))
                all_positive.append(good)
                if not good:
                    status.append(f"{position}: stage/semantic mismatch: {observation}")
        if len(fingerprints) != 1:
            raise ValueError(f"Mixed QASM source/target hashes: {case}")

        s = {p: times[case,p] for p in ORDER}
        base_median = (s["A1"]["median_ns"] + s["A2"]["median_ns"]) / 2
        head_median = (s["B1"]["median_ns"] + s["B2"]["median_ns"]) / 2
        drift = 100 * (s["A2"]["median_ns"] / s["A1"]["median_ns"] - 1)
        eligible = not status and len({w["verdict"] for p in ORDER
                                      for w in science[case,p]["observations"]}) == 1
        ratios = (100 * (head_median / base_median - 1)) if eligible else None
        cv = {p: s[p]["stdev_ns"] / s[p]["mean_ns"] for p in ORDER}
        results.append({
            "case": case, "expected_binary": expected, "fixture_sha256": list(fingerprints.pop()),
            "method": "hybrid", "backend": "rust", "solver": "gpmc",
            "rounds_per_cell": {p: s[p]["rounds"] for p in ORDER},
            "mean_ms": {p: s[p]["mean_ns"]/1e6 for p in ORDER},
            "median_ms": {p: s[p]["median_ns"]/1e6 for p in ORDER},
            "cv": cv, "base_median_ms": base_median/1e6,
            "head_median_ms": head_median/1e6,
            "median_head_vs_base_percent": ratios,
            "base_A1_A2_drift_percent": drift,
            "performance_comparable": eligible,
            "status": "COMPARABLE_OBSERVATION" if eligible else "BLOCKED_SCIENCE_OR_STAGE",
            "warnings": status,
        })

    return {
        "schema": "quprs-codspeed-qasm261-abba-v1",
        "experiment_fixture_sha": fixture_sha, "base_sha": base_sha,
        "head_sha": head_sha, "instrument": "CodSpeed WallTime",
        "comparison": "same-runner same-new-QASM dev versus PR; 4 positions x up to 5 rounds",
        "runner_class": "GITHUB_HOSTED_NOT_MACRO",
        "scientific_certified": False, "statistically_certified": False,
        "automatic_performance_gate": False,
        "measurement_uris": 20,
        "total_measured_rounds": sum(s["rounds"] for s in times.values()),
        "stage_comparable_cases": sum(x["performance_comparable"] for x in results),
        "cases": results,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--measurements",type=Path,required=True)
    p.add_argument("--provenance",type=Path,required=True)
    p.add_argument("--audit",type=Path,required=True)
    p.add_argument("--base-sha",required=True)
    p.add_argument("--head-sha",required=True)
    p.add_argument("--fixture-sha",required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--summary",type=Path)
    a=p.parse_args()
    result=produce(json.loads(a.measurements.read_text()),
        [json.loads(x) for x in a.provenance.read_text().splitlines() if x],
        base_sha=a.base_sha,head_sha=a.head_sha,fixture_sha=a.fixture_sha,
        audit=json.loads(a.audit.read_text()))
    a.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    lines=[
        "## QASM261 source-pinned CodSpeed WallTime ABBA",
        f"dev/base `{a.base_sha}` vs PR/head `{a.head_sha}`, fixtures `{a.fixture_sha}`",
        "Official CodSpeed WallTime only; same hosted runner, not Macro; "
        "each A1/B1/B2/A2 cell measured repeatedly. Direction only.",
        "",
        "| Case | Base (ms) | PR (ms) | PR vs base | Base A1/A2 drift | Stage/semantic |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for case in result["cases"]:
        v=case["median_head_vs_base_percent"]
        lines.append(
            f"| {case['case']} | {case['base_median_ms']:.2f} | "
            f"{case['head_median_ms']:.2f} | "
            f"{f'{v:+.2f}%' if v is not None else 'INCOMPARABLE'} | "
            f"{case['base_A1_A2_drift_percent']:+.2f}% | {case['status']} |"
        )
    lines.append(f"\nComparable stages: {result['stage_comparable_cases']}/5; "
                 f"actual rounds: {result['total_measured_rounds']}; "
                 "no automatic regression threshold.\n")
    markdown="\n".join(lines)
    print(markdown)
    if a.summary:
        with a.summary.open("a",encoding="utf-8") as stream:
            stream.write(markdown)
if __name__=="__main__":
    main()

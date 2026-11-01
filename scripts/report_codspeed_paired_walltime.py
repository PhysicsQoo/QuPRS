#!/usr/bin/env python3
"""Validate and pair source-pinned CodSpeed WallTime base/HEAD samples.

Input numbers come ONLY from pytest-codspeed's WallTime instrument report.
The test writes semantic provenance AFTER the measured operation.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path

ID = re.compile(r"test_pr_solver_inclusive_walltime\[([^\]]+)-(base|head)\]$")
EXPECTED = {
    "vqe4_gpmc", "qft16_gpmc", "qaoa7_gpmc",
    "vqe4_ganak", "grover4_ganak", "vqe4_gpmc_python",
    "vqe4_ganak_python",
}
EQ = {"equivalent", "equivalent*"}


def classify(verdict: str) -> str:
    return "equivalent" if verdict in EQ else verdict


def produce(measurements: dict, records: list[dict], base_sha: str, head_sha: str):
    if measurements.get("instrument", {}).get("type") != "walltime":
        raise ValueError("Not a CodSpeed WallTime measurement")
    times = {}
    for entry in measurements.get("benchmarks", []):
        match = ID.search(entry.get("uri", ""))
        if match is None:
            raise ValueError(f"Unexpected CodSpeed benchmark identity: {entry.get('uri')}")
        key = (match.group(1), match.group(2))
        if key in times:
            raise ValueError(f"Duplicate CodSpeed measurement: {key}")
        stats = entry["stats"]
        if stats.get("rounds", 0) < 2 or stats.get("iter_per_round", 0) < 1:
            raise ValueError(f"Incomplete CodSpeed rounds: {key}: {stats}")
        if not all(math.isfinite(stats[field]) and stats[field] > 0
                   for field in ("min_ns", "median_ns", "mean_ns")):
            raise ValueError(f"Invalid CodSpeed measured duration: {key}")
        times[key] = stats

    provenance = {}
    for record in records:
        key = record["case"], record["revision"]
        if key in provenance:
            raise ValueError(f"Duplicated semantic record: {key}")
        provenance[key] = record
    keys = {(case, rev) for case in EXPECTED for rev in ("base", "head")}
    if set(times) != keys or set(provenance) != keys:
        raise ValueError(
            f"Incomplete/extra paired coverage: missing_times={keys - set(times)} "
            f"extra_times={set(times) - keys}; missing_provenance={keys - set(provenance)} "
            f"extra_provenance={set(provenance) - keys}"
        )

    outcome = []
    errors = []
    for case in sorted(EXPECTED):
        b, h = provenance[case, "base"], provenance[case, "head"]
        bt, ht = times[case, "base"], times[case, "head"]
        for revision, record, sha in (("base", b, base_sha), ("head", h, head_sha)):
            if record["sha"] != sha or record["fixture_sha"] != head_sha:
                errors.append(f"{case}/{revision}: incorrect source/fixture SHA")
            if not record["solver_invoked"]:
                errors.append(f"{case}/{revision}: Solver was not actually invoked")
            if record["verdict"] not in EQ | {"not_equivalent"}:
                errors.append(f"{case}/{revision}: inconclusive verdict {record['verdict']}")
            if record["method"] != "hybrid":
                errors.append(f"{case}/{revision}: expected Hybrid")
            if (record["verdict"] == "not_equivalent"
                    and record["verification_status"] != "EXTERNAL_GANAK_PRINT_LIMITATION"):
                errors.append(f"{case}/{revision}: negative without known Solver limitation")

        for field in ("method", "backend", "solver", "strategy", "reverse", "fixture_sha"):
            if b[field] != h[field]:
                errors.append(f"{case}: unequal {field}: {b[field]} != {h[field]}")
        if classify(b["verdict"]) != classify(h["verdict"]):
            errors.append(f"{case}: semantic category changed: {b['verdict']} -> {h['verdict']}")
        warning = []
        if b["verdict"] != h["verdict"]:
            warning.append("verdict labeling changed")
        if b["rr_approximate"] != h["rr_approximate"]:
            warning.append("RR approximate provenance changed")
        if classify(b["verdict"]) == "not_equivalent":
            warning.append("known external Ganak precision limitation; NOT a scientific PASS")
        b_ms, h_ms = bt["min_ns"] / 1e6, ht["min_ns"] / 1e6
        delta = 100 * (h_ms / b_ms - 1)
        for kind, s in (("base", bt), ("head", ht)):
            if s["stdev_ns"] / s["mean_ns"] > .05:
                warning.append(f"{kind} relative stdev exceeds 5%")
        outcome.append({
            "case": case, "base_min_ms": b_ms, "head_min_ms": h_ms,
            "change_percent": delta,
            "base_median_ms": bt["median_ns"] / 1e6,
            "head_median_ms": ht["median_ns"] / 1e6,
            "verdict_base": b["verdict"], "verdict_head": h["verdict"],
            "solver_invoked_base": b["solver_invoked"],
            "solver_invoked_head": h["solver_invoked"],
            "warning": warning,
        })

    header = [
        "## Paired Solver-inclusive CodSpeed WallTime",
        f"Base: \x60{base_sha}\x60; HEAD: \x60{head_sha}\x60.",
        "Source: pytest-codspeed WallTime (minimum across instrumented rounds). "
        "Same shared GitHub hosted runner, **not** a qualified CodSpeed Macro runner; "
        "these percent deltas are exploratory, not certified regressions.",
        "",
        "| Case | Base (ms) | HEAD (ms) | Time change | Verdict (base -> HEAD) | Notes |",
        "|---|---:|---:|---:|---|---|",
    ]
    for x in outcome:
        notes = "; ".join(x["warning"]) or "solver invoked in both"
        header.append(
            f"| {x['case']} | {x['base_min_ms']:.2f} | {x['head_min_ms']:.2f} "
            f"| {x['change_percent']:+.2f}% | "
            f"{x['verdict_base']} -> {x['verdict_head']} | {notes} |"
        )
    header += ["", f"Coverage: {len(outcome)} exact case pairs, {len(times)} instrumented samples.",
               "**Semantic/stage matching:** " + ("PASS" if not errors else "FAIL"), ""]
    if errors:
        header.extend(["Errors:"] + [f"- {error}" for error in errors])
    return {"base_sha": base_sha, "head_sha": head_sha, "cases": outcome,
            "errors": errors, "status": "PASS" if not errors else "FAIL"}, "\n".join(header) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--measurements", type=Path, required=True)
    p.add_argument("--provenance", type=Path, required=True)
    p.add_argument("--base-sha", required=True)
    p.add_argument("--head-sha", required=True)
    p.add_argument("--markdown", type=Path, required=True)
    p.add_argument("--json", type=Path, required=True)
    p.add_argument("--summary", type=Path)
    a = p.parse_args()
    report, markdown = produce(
        json.loads(a.measurements.read_text(encoding="utf-8")),
        [json.loads(line) for line in a.provenance.read_text(encoding="utf-8").splitlines() if line.strip()],
        a.base_sha, a.head_sha,
    )
    a.markdown.write_text(markdown, encoding="utf-8")
    a.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if a.summary is not None:
        with a.summary.open("a", encoding="utf-8") as f:
            f.write(markdown)
    print(markdown)
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

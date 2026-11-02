#!/usr/bin/env python3
"""Research-only TACAS parameter experiment: RR@distance=1e-8 vs Ganak@distance=2e-5.

The source-circuit identity, original v0.9.1 binary oracle, backend and actual
solver stage are retained. No non-CodSpeed performance measurements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from scripts.tacas26_modern_calibration import (
    SOURCE_SHA, MARKER, archive_labels, binary, get_pinned_case, matrix,
)

ROOT = Path(__file__).resolve().parents[1]

# Each shard intentionally bounds independent solver invocations.
# (case id, solver, backend, method, distance, rr_tolerance)
RR_QPE20 = "table2:qpeinexact20:positive:hybrid"
RR_QPE24 = "table2:qpeinexact24:positive:hybrid"
RR_QAOA_NEG = "table3_negative:qaoa11:negative:hybrid"
RR_QWALK_NEG = "table3_negative:qwalk4:negative:hybrid"
WMC_QFT20 = "table2:qft20:positive:wmc_only"
WMC_QFT22 = "table2:qft22:positive:wmc_only"
G_QAOA_POS = "table2:qaoa7:positive:hybrid"
G_QPE16_POS = "table2:qpeinexact16:positive:hybrid"
G_QFT16_POS = "table2:qft16:positive:wmc_only"
G_QAOA_WMC_POS = "table2:qaoa11:positive:wmc_only"
G_QAOA_WMC_NEG = "table3_negative:qaoa11:negative:wmc_only"
G_QWALK_WMC_NEG = "table3_negative:qwalk4:negative:wmc_only"
G_QPE20_NEG = "table3_negative:qpeinexact20:negative:hybrid"

RR_LEVELS = ("1e-10", "1e-6", "1e-5", "2e-5", "1e-4")

def _rr(case, levels=RR_LEVELS):
    return [(case, "gpmc", "rust", "hybrid", "1e-8", rr) for rr in levels]

def _ganak(case):
    return [(case, "ganak", backend, case.rsplit(":", 1)[-1], "2e-5", "1e-10")
            for backend in ("rust", "python")]

SHARDS = (
    tuple(_rr(RR_QPE20)) + ((RR_QPE20, "gpmc", "python", "hybrid", "1e-8", "2e-5"),),
    tuple(_rr(RR_QPE24)),
    tuple(_rr(RR_QAOA_NEG, ("1e-10", "2e-5", "1e-4")) +
          _rr(RR_QWALK_NEG, ("1e-10", "2e-5", "1e-4"))),
    tuple((case, "gpmc", "rust", "wmc_only", "1e-8", rr)
          for case in (WMC_QFT20, WMC_QFT22) for rr in ("1e-10", "1e-4")),
    tuple(_ganak(RR_QPE20) + _ganak(RR_QPE24)),
    tuple(_ganak(WMC_QFT20) + _ganak(WMC_QFT22)),
    tuple(_ganak(RR_QAOA_NEG) + _ganak(RR_QWALK_NEG)),
    tuple(_ganak(G_QAOA_WMC_NEG) + _ganak(G_QWALK_WMC_NEG)),
    tuple(_ganak(G_QAOA_POS) + _ganak(G_QPE16_POS)),
    tuple(_ganak(G_QFT16_POS) + _ganak(G_QAOA_WMC_POS)),
    tuple(_ganak(G_QPE20_NEG)),
)

def check_plan(root):
    canonical = {r["id"]: r for r in matrix(root)}
    historic = archive_labels(root)
    seen = set()
    for i, shard in enumerate(SHARDS):
        if not shard or len(shard) > 6:
            raise ValueError(f"Overlong or empty shard {i}")
        for case_id, solver, backend, method, distance, rr in shard:
            key = (case_id, solver, backend, method, distance, rr)
            if key in seen:
                raise ValueError("Duplicated source/parameter probe")
            seen.add(key)
            case = canonical.get(case_id)
            if case is None or case["method"] != method:
                raise ValueError("Source case/method missing or changed: " + case_id)
            if case_id not in historic or binary(historic[case_id]["verdict"]) is None:
                raise ValueError("Historical binary oracle not determinate: " + case_id)
            if solver == "gpmc" and distance != "1e-8":
                raise ValueError("RR experiment must freeze distance=1e-8")
            if solver == "ganak" and (distance, rr) != ("2e-5", "1e-10"):
                raise ValueError("Ganak experiment must freeze eps=2e-5, RR=1e-10")
            if solver not in ("gpmc", "ganak") or backend not in ("rust", "python"):
                raise ValueError("Invalid method or backend")
            get_pinned_case(root, case_id, canonical)
    assert len(seen) == sum(len(s) for s in SHARDS)
    return canonical, historic

def call(root, case, spec, solver_timeout, watchdog):
    case_id, solver, backend, method, distance, rr = spec
    variant = "random_rotation" if case["kind"] == "negative" else "transpiled"
    command = [
        sys.executable, str(root / "benchmarks/codspeed/solver_case.py"),
        str(root), Path(case["a"]).name, "proportional", solver, backend,
        "0", variant, method,
    ]
    environment = dict(os.environ)
    environment.update(
        QUPRS_DIAGNOSTIC_DISTANCE_TOLERANCE=distance,
        QUPRS_DIAGNOSTIC_RR_TOLERANCE=rr,
        QUPRS_DIAGNOSTIC_PHASE_TOLERANCE="1e-8",
        QUPRS_CROSS_METHOD_SOLVER_TIMEOUT=str(solver_timeout),
    )
    try:
        process = subprocess.Popen(
            command, cwd=root, env=environment, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        )
    except OSError as exc:
        return {"run_status": "SPAWN_ERROR", "verdict": None, "error": str(exc)}
    try:
        stdout, stderr = process.communicate(timeout=watchdog)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        return {"run_status": "WATCHDOG_CENSORED", "verdict": None, "exit_code": None}
    output = [s[len(MARKER):] for s in stdout.splitlines() if s.startswith(MARKER)]
    if process.returncode != 0 or len(output) != 1:
        return {"run_status": "PROCESS_OR_PARSE_ERROR", "verdict": None,
                "exit_code": process.returncode,
                "stdout_tail": stdout[-1600:], "stderr_tail": stderr[-2500:]}
    try:
        obj = json.loads(output[0])
        if not isinstance(obj, dict):
            raise ValueError("Not a JSON object")
    except (ValueError, TypeError) as exc:
        return {"run_status": "PROCESS_OR_PARSE_ERROR", "verdict": None,
                "exit_code": process.returncode, "error": str(exc)}
    return {"run_status": "COMPLETED", "exit_code": process.returncode, **obj}

def classification(historical, observation):
    if observation.get("run_status") != "COMPLETED":
        return "CENSORED_OR_INVALID"
    actual, expected = binary(observation.get("verdict")), binary(historical)
    if actual is None or expected is None:
        return "CENSORED_OR_INVALID"
    return "BINARY_MATCH" if actual == expected else "BINARY_MISMATCH"

def run(root, output, sha, shard, solver_timeout=120, watchdog=140):
    root, output = Path(root).resolve(), Path(output).resolve()
    if not (0 < solver_timeout < watchdog <= 220):
        raise ValueError("Unbounded timeout")
    observed_head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if observed_head != sha:
        raise ValueError("Research source SHA mismatch")
    canonical, historical = check_plan(root)
    if not 0 <= shard < len(SHARDS):
        raise ValueError("Invalid shard")
    output.parent.mkdir(parents=True, exist_ok=True)
    items = []
    with output.open("w", encoding="utf8") as handle:
        for index, spec in enumerate(SHARDS[shard]):
            case_id, solver, backend, method, distance, rr = spec
            case, first, second = get_pinned_case(root, case_id, canonical)
            observed = call(root, case, spec, solver_timeout, watchdog)
            verdict = historical[case_id]["verdict"]
            row = {
                "schema": "tacas26-rr-vs-ganak-source-calibration-v1",
                "head_sha": sha, "historical_sha": SOURCE_SHA,
                "id": case_id, "index": index,
                "historical_verdict": verdict,
                "historical_binary": binary(verdict),
                "source_original": first, "source_counterpart": second,
                "solver": solver, "backend": backend,
                "method": method, "rr_tolerance": rr,
                "distance_tolerance": distance, "phase_tolerance": "1e-8",
                "solver_timeout_seconds": solver_timeout,
                "watchdog_seconds": watchdog, "observation": observed,
                "binary_comparison": classification(verdict, observed),
                "no_timing_comparison": True,
            }
            items.append(row)
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            print("TACAS_RR_GANAK_PROBE " + json.dumps({
                "id": case_id, "solver": solver, "backend": backend,
                "rr_tolerance": rr, "distance_tolerance": distance,
                "result": observed.get("verdict"),
                "run_status": observed.get("run_status"),
                "comparison": row["binary_comparison"],
                "solver_invoked": observed.get("solver_invoked"),
                "wmc_print_resolution_distance": observed.get(
                    "wmc_print_resolution_distance"),
                "wmc_precision_reason": observed.get("wmc_precision_reason"),
                "rr_approximate": observed.get("rr_approximate"),
            }, sort_keys=True), flush=True)
    summary = {
        "schema": "tacas26-rr-vs-ganak-science-summary-v1",
        "head_sha": sha, "shard": shard,
        "total": len(items),
        "matched": sum(x["binary_comparison"] == "BINARY_MATCH" for x in items),
        "mismatched": [
            {"id": x["id"], "solver": x["solver"], "rr_tolerance": x["rr_tolerance"],
             "verdict": x["observation"].get("verdict")}
            for x in items if x["binary_comparison"] == "BINARY_MISMATCH"
        ],
        "censored": [
            {"id": x["id"], "solver": x["solver"],
             "status": x["observation"].get("run_status")}
            for x in items if x["binary_comparison"] == "CENSORED_OR_INVALID"
        ],
        "scope": "bounded-science-only-no-codspeed-metrics",
    }
    output.with_suffix(".summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print("TACAS_RR_GANAK_SUMMARY " + json.dumps(summary, sort_keys=True), flush=True)
    return summary

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--solver-timeout", type=int, default=120)
    p.add_argument("--watchdog", type=int, default=140)
    a = p.parse_args()
    run(a.root, a.output, a.sha, a.shard, a.solver_timeout, a.watchdog)

if __name__ == "__main__":
    main()

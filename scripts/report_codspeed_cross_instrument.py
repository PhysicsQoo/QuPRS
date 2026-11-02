#!/usr/bin/env python3
"""One-commit CodSpeed evidence audit; no independent timing or estimated speedup.

This program joins measurements collected IN THIS WORKFLOW RUN only.  Separate
CodSpeed instruments are diagnostic axes, never a combined percentage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

CANONICAL_SHA = "7eb82617bf092c81c6a6bde6e8cd05cec9bab71879f17b2bf315c9c420c7c8ed"
NATIVE_CASES = 11
WALLTIME_CASES = 7


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def collect(folder, pattern):
    return sorted(folder.glob(pattern))


def load_provenance(folder, family, *, expected_sha, mode=None, count=1):
    files = collect(folder, "**/manifest.json")
    matches = [read(path) for path in files if read(path).get("family") == family
               and (mode is None or read(path).get("instrument") == mode)]
    if len(matches) != count:
        raise ValueError(f"{family}/{mode}: expected {count} SHA manifests, got {len(matches)}")
    for row in matches:
        if row.get("schema") != "quprs-codspeed-sha-v2":
            raise ValueError(f"{family}: incompatible manifest schema")
        if row.get("sha") != expected_sha or row.get("fixture_revision_sha") != expected_sha:
            raise ValueError(f"{family}: wrong SHA or fixture identity")
        if row.get("measurement_status") != "uploaded_by_codspeed_action":
            raise ValueError(f"{family}: no confirmed CodSpeed action")
    return matches


def validate_simulation(folder, sha):
    entries = load_provenance(folder, "simulation-shard", expected_sha=sha, count=5)
    found = set()
    measurements = {}
    for entry in entries:
        idx = entry["shard"]
        if idx is None or entry["num_shards"] != 5 or idx in found:
            raise ValueError("five shard IDs must be exactly unique 0..4")
        found.add(idx)
        raw = collect(folder, f"**/simulation-{idx}.json")
        if len(raw) != 1:
            raise ValueError(f"shard {idx}: missing or duplicated instrument export")
        payload = raw[0].read_bytes()
        if hashlib.sha256(payload).hexdigest() != entry["measurement_sha256"]:
            raise ValueError(f"shard {idx}: instrument output does not match manifest")
        decoded = json.loads(payload)
        if not isinstance(decoded.get("benchmarks"), list):
            raise ValueError(f"shard {idx}: missing original instrument benchmarks")
        for result in decoded["benchmarks"]:
            uri = result.get("uri")
            if not isinstance(uri, str) or not uri.startswith(("test/test_Feynman.py::", "test/test_MQT.py::")):
                raise ValueError(f"unexpected original CodSpeed benchmark: {uri}")
            if uri in measurements:
                raise ValueError(f"duplicate benchmark across shards: {uri}")
            measurements[uri] = result
    if found != set(range(5)) or len(measurements) != 32:
        raise ValueError(f"incomplete canonical five-shard suite: {found}, n={len(measurements)}")
    identity = hashlib.sha256("\n".join(sorted(measurements)).encode()).hexdigest()
    if identity != CANONICAL_SHA:
        raise ValueError("original 32 CodSpeed benchmark identities changed")
    return measurements


def validate_walltime(folder, head_sha, base_sha):
    files = collect(folder, "**/paired-walltime-report.json")
    if len(files) != 1:
        raise ValueError(f"paired walltime: expected one report, got {len(files)}")
    report = read(files[0])
    if report.get("head_sha") != head_sha or report.get("base_sha") != base_sha:
        raise ValueError("WallTime source SHA differs from CPU and Rust core")
    cases = report.get("cases", [])
    if len(cases) != WALLTIME_CASES or report.get("errors"):
        raise ValueError("Solver-inclusive paired report incomplete or contains audit errors")
    if len({row["case"] for row in cases}) != WALLTIME_CASES:
        raise ValueError("Solver-inclusive case IDs duplicated")
    for row in cases:
        if not row["solver_invoked_base"] or not row["solver_invoked_head"]:
            raise ValueError(f"{row['case']}: non-solver path in Solver-inclusive benchmark")
    return report



def validate_optional_export(folder, family, mode, sha, suffix, expected):
    metadata = load_provenance(folder, family, expected_sha=sha, mode=mode)[0]
    files = collect(folder, f"**/{suffix}")
    if len(files) != 1:
        raise ValueError(f"{family}/{mode}: expected one instrument export")
    blob = files[0].read_bytes()
    if hashlib.sha256(blob).hexdigest() != metadata.get("measurement_sha256"):
        raise ValueError(f"{family}/{mode}: instrument export SHA mismatch")
    record = json.loads(blob)
    values = record.get("benchmarks")
    if not isinstance(values, list) or len(values) != expected:
        raise ValueError(f"{family}/{mode}: expected {expected} directly measured identities")
    uris = [x.get("uri") for x in values]
    if len(set(uris)) != expected:
        raise ValueError(f"{family}/{mode}: duplicated measurement identities")
    return values


def cross_rows(simulation, walltime):
    labels = {
        "vqe4_gpmc": "vqe_nativegates_ibm_qiskit_opt0_4.qasm",
        "qaoa7_gpmc": "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
        "qft16_gpmc": "qft_nativegates_ibm_qiskit_opt0_16.qasm",
    }
    joined = []
    for row in walltime["cases"]:
        case = row["case"]
        if case not in labels:
            continue
        matching = [key for key in simulation
                    if labels[case] in key and key.endswith("-gpmc-rust]")]
        if len(matching) != 1:
            raise ValueError(f"missing/ambiguous same-SHA CPU and WallTime case {case}")
        observed = simulation[matching[0]]
        # Do not fabricate CPU seconds from an unrecognised instrument schema.
        joined.append({
            "case": case,
            "simulation_uri": matching[0],
            "simulation_raw_record": observed,
            "walltime_base_median_ms": row["base_median_ms"],
            "walltime_head_median_ms": row["head_median_ms"],
            "walltime_delta_percent": row["change_percent"],
            "verdict_base": row["verdict_base"], "verdict_head": row["verdict_head"],
            "comparable_verdict": row["performance_comparable"],
            "scope_note": "Simulation host CPU excludes subprocess; WallTime includes process startup and Solver",
        })
    if len(joined) != 3:
        raise ValueError("Required VQE4/QAOA7/QFT16 same-SHA evidence missing")
    return joined


def produce(folder, sha, base_sha, *, require_solver_cpu=False, require_memory=False,
            require_cross_method=False):
    sim = validate_simulation(folder, sha)
    native = load_provenance(folder, "rust-core", expected_sha=sha, mode="simulation")[0]
    if len(native.get("expected_ids", [])) != NATIVE_CASES:
        raise ValueError("native Rust core must preserve its original 11 identities")
    if require_memory:
        load_provenance(folder, "rust-core", expected_sha=sha, mode="memory")
    if require_solver_cpu:
        validate_optional_export(folder, "solver-cpu", "simulation", sha,
                                 "solver-cpu.json", 7)
    if require_cross_method:
        validate_optional_export(folder, "cross-method", "simulation", sha,
                                 "cross-method-simulation.json", 8)
        validate_optional_export(folder, "cross-method", "walltime", sha,
                                 "cross-method-walltime.json", 48)
    wall = validate_walltime(folder, sha, base_sha) if base_sha else None
    rows = cross_rows(sim, wall) if wall else []
    scientific_status = ("BASELINE_ONLY" if wall is None else
                         "PRECISION_LIMITED" if wall["status"] == "PRECISION_LIMITED" else wall["status"])
    report = {
        "schema": "quprs-codspeed-cross-instrument-v2",
        "head_sha": sha, "base_sha": base_sha, "five_shard_canonical_count": len(sim),
        "native_core_expected_count": NATIVE_CASES,
        "native_core_metrics": "CodSpeed service only; no fabricated local numeric result",
        "walltime_paired_cases": WALLTIME_CASES if wall else 0,
        "optional_solver_cpu_count": 7 if require_solver_cpu else 0,
        "optional_cross_method_cpu_count": 8 if require_cross_method else 0,
        "optional_cross_method_walltime_count": 48 if require_cross_method else 0,
        "optional_rust_memory_count": NATIVE_CASES if require_memory else 0,
        "cross_instrument_rows": rows,
        "scientific_status": scientific_status,
        "evidence_collection": "COMPLETE",
        "performance_certified": False,
        "limitations": [
            "No metrics from a different SHA or carried-forward CodSpeed results",
            "Native cargo-codspeed numerics must be reviewed in CodSpeed for this SHA",
            "Hosted WallTime is exploratory until stable Macro Runner variance is qualified",
            "CPU Simulation and WallTime are different instruments and cannot be subtracted",
        ],
    }
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifacts", required=True, type=Path)
    p.add_argument("--head-sha", required=True)
    p.add_argument("--base-sha", default="")
    p.add_argument("--require-solver-cpu", action="store_true")
    p.add_argument("--require-memory", action="store_true")
    p.add_argument("--require-cross-method", action="store_true")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--summary", type=Path)
    a = p.parse_args()
    try:
        result = produce(a.artifacts, a.head_sha, a.base_sha,
                         require_solver_cpu=a.require_solver_cpu,
                         require_memory=a.require_memory,
                         require_cross_method=a.require_cross_method)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"CODEXPERIMENT_AUDIT_FAILED: {exc}", file=sys.stderr)
        return 1
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown = [
        "## CodSpeed same-SHA cross-instrument v2",
        f"- HEAD: \`{a.head_sha}\`; base: \`{a.base_sha or '(baseline only)'}\`",
        "- Canonical: 32/32 original CPU Simulation IDs across five shards",
        "- Native Rust: 11 benchmark identities uploaded; numeric metrics only in CodSpeed",
        f"- Solver-inclusive: {result['walltime_paired_cases']} paired workloads, 2 revisions each",
        f"- Scientific status: **{result['scientific_status']}** (independent of CI collection)",
        "- Performance certified: **NO** (shared runner variance and external metrics)",
        "",
        "| Case | Base median WallTime (ms) | HEAD median (ms) | Matched verdict |",
        "|---|---:|---:|---|",
    ]
    for row in result["cross_instrument_rows"]:
        markdown.append(
            f"| {row['case']} | {row['walltime_base_median_ms']:.2f} | "
            f"{row['walltime_head_median_ms']:.2f} | "
            f"{row['verdict_base']} → {row['verdict_head']} |"
        )
    markdown += ["", "Simulation rows are in the JSON artifact, same SHA as the complete WallTime HEAD. "
                  "No CPU+WallTime arithmetic or cross-SHA metric carry-forward is performed.", ""]
    if a.summary:
        with a.summary.open("a", encoding="utf-8") as stream:
            stream.write("\n".join(markdown) + "\n")
    print("\n".join(markdown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

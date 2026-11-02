#!/usr/bin/env python3
"""Source-pinned, fail-closed archival audit of TACAS26 Ganak 101 CI artifacts."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

HISTORICAL = "e928abc47dd15926364ec77905eb0d5dc92ce8cc"
GANAK_HEAD = "1a38d7de190cacba4e2713f2bd7e586724a5fb6d"
GANAK_RUN = 41540814150
GPMC_RUN = 41485674318
TOL = 2e-5


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inferred_distance(obs):
    """Float-parsed printed log2-magnitude point estimate, not true D_proj."""
    delta = obs["wmc_log_wmc"] - obs["wmc_expected_log2"]
    return math.sqrt(-math.expm1(2 * math.log(2) * delta)) if delta <= 0 else None


def archive(ganak_dir, gpmc_json, output):
    files = sorted(ganak_dir.rglob("tacas26-modern-ganak101-*.jsonl"))
    if len(files) != 24:
        raise ValueError(f"Expected 24 original Ganak shards, found {len(files)}")
    g = json.loads(gpmc_json.read_text(encoding="utf-8"))
    if (g["historical_sha"] != HISTORICAL or len(g["cases"]) != 101
        or not g["gates"]["full_101_python_rust_binary_reproduction"]
        or not g["gates"]["full_101_precision90_binary_reproduction"]):
        raise ValueError("Pinned GPMC 101-case audit is incomplete")
    gpmc = {x["id"]: x for x in g["cases"]}
    actual = {}
    input_digests = {}
    for artifact in files:
        raw = artifact.read_bytes()
        input_digests[artifact.name] = digest(raw)
        if not raw.strip():
            raise ValueError(f"Empty shard: {artifact}")
        for line in raw.decode("utf-8").splitlines():
            row = json.loads(line)
            key = row["id"]
            if key not in gpmc or key in actual:
                raise ValueError(f"Unexpected or repeated case: {key}")
            obs = row["observation"]
            ref = gpmc[key]
            expected_fields = (
                row["schema"] == "tacas26-modern-ganak-101-binary-v1",
                row["modern_sha"] == GANAK_HEAD,
                row["historical_sha"] == HISTORICAL,
                row["ganak_pinned_version"] == "2.8.0",
                row["solver"] == "ganak",
                row["backend"] == "python",
                row["distance_tolerance"] == "2e-5",
                row["rr_tolerance"] == "1e-10",
                row["phase_tolerance"] == "1e-8",
                obs["run_status"] == "COMPLETED",
                obs["exit_code"] == 0,
                obs["solver_invoked"] is True,
                obs["method"] == row["method"],
                row["method"] == ref["method"],
                row["original_binary"] == ref["historical_binary"],
                row["original_qasm"]["sha256"] == ref["source_original_qasm_sha256"],
                row["counterpart_qasm"]["sha256"] == ref["source_counterpart_qasm_sha256"],
                all(x == "BINARY_MATCH" for x in ref["new_binary_comparisons"].values()),
                row["solver_arithmetic_certification"] == "NOT_CERTIFIED",
            )
            if not all(expected_fields):
                raise ValueError(f"Source/QASM/solver/provenance mismatch: {key}")
            current = ("EQUIVALENT" if obs["verdict"] in ("equivalent", "equivalent*")
                       else "NOT_EQUIVALENT" if obs["verdict"] == "not_equivalent"
                       else "CENSORED")
            independently_scored = ("BINARY_MATCH" if current == row["original_binary"]
                                    else "CENSORED" if current == "CENSORED"
                                    else "BINARY_MISMATCH")
            if row["binary_comparison"] != independently_scored:
                raise ValueError(f"Untrusted producer binary score: {key}")
            actual[key] = row
    if set(actual) != set(gpmc):
        raise ValueError("Incomplete 101-case matching")
    bad = [v for v in actual.values() if v["binary_comparison"] == "BINARY_MISMATCH"]
    eq = sum(v["original_binary"] == "EQUIVALENT" for v in actual.values())
    neq = sum(v["original_binary"] == "NOT_EQUIVALENT" for v in actual.values())
    if (len(actual), eq, neq, len(bad)) != (101, 45, 56, 20):
        raise ValueError(f"Unexpected results: {len(actual)}, {eq}, {neq}, {len(bad)}")
    if any(v["original_binary"] != "EQUIVALENT" or
           v["observation"]["verdict"] != "not_equivalent" or
           v["observation"]["wmc_precision_reason"] !=
           "ganak_point_estimate_resolution_limited" or
           (v["observation"]["wmc_print_resolution_distance"] or 0) <= TOL
           for v in bad):
        raise ValueError("A false-NEQ classification lacks its expected resolution witness")
    output.mkdir(parents=True, exist_ok=True)
    raw_text = "".join(json.dumps(actual[k], ensure_ascii=False, sort_keys=True,
                                  separators=(",", ":")) + "\n" for k in sorted(actual))
    (output / "ganak101-raw.jsonl").write_text(raw_text, encoding="utf-8")
    columns = ["id", "method", "historical_binary", "ganak_verdict",
               "binary_comparison", "solver_invoked", "wmc_expected_log2",
               "wmc_log_wmc", "log2_magnitude_deficit",
               "printed_point_distance", "print_resolution_distance",
               "resolution_to_tolerance_ratio", "precision_reason",
               "gpmc_python30_verdict", "gpmc_rust30_verdict",
               "gpmc_python90_verdict", "original_qasm_sha256",
               "counterpart_qasm_sha256", "historical_source_result_sha256"]
    science = []
    for key in sorted(actual):
        row, ref = actual[key], gpmc[key]
        obs = row["observation"]
        res = obs.get("wmc_print_resolution_distance")
        science.append({
            "id": key, "method": row["method"], "historical_binary": row["original_binary"],
            "ganak_verdict": obs["verdict"], "binary_comparison": row["binary_comparison"],
            "solver_invoked": obs["solver_invoked"],
            "wmc_expected_log2": obs["wmc_expected_log2"],
            "wmc_log_wmc": obs["wmc_log_wmc"],
            "log2_magnitude_deficit": obs["wmc_expected_log2"] - obs["wmc_log_wmc"],
            "printed_point_distance": inferred_distance(obs),
            "print_resolution_distance": res,
            "resolution_to_tolerance_ratio": res / TOL if res is not None else None,
            "precision_reason": obs["wmc_precision_reason"],
            "gpmc_python30_verdict": ref["new_verdicts"]["python_30"],
            "gpmc_rust30_verdict": ref["new_verdicts"]["rust_30"],
            "gpmc_python90_verdict": ref["new_verdicts"]["python_90"],
            "original_qasm_sha256": row["original_qasm"]["sha256"],
            "counterpart_qasm_sha256": row["counterpart_qasm"]["sha256"],
            "historical_source_result_sha256": row["historical_source_result_sha256"],
        })
    bad_rows = [x for x in science if x["binary_comparison"] == "BINARY_MISMATCH"]
    for name, subset in [("ganak101-science.csv", science),
                         ("ganak20-eq-to-neq.csv", bad_rows)]:
        with (output / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(subset)
    distances = [x["printed_point_distance"] for x in bad_rows]
    resolution = [x["print_resolution_distance"] for x in bad_rows]
    summary = {
        "schema": "tacas26-ganak101-archived-v1",
        "ganak_run": GANAK_RUN, "gpmc_run": GPMC_RUN,
        "ganak_head_sha": GANAK_HEAD, "historical_source_sha": HISTORICAL,
        "ganak_mode": 6, "distance_tolerance": "2e-5",
        "rr_tolerance": "1e-10", "phase_tolerance": "1e-8",
        "total": 101, "historical_eq": eq, "historical_neq": neq,
        "matched": 81, "false_neq": 20, "false_eq": 0, "timeout_or_missing": 0,
        "false_neq_methods": dict(Counter(x["method"] for x in bad)),
        "false_neq_printed_point_distance": {
            "min": min(distances), "median": statistics.median(distances),
            "max": max(distances)},
        "false_neq_print_resolution_distance": {
            "min": min(resolution), "median": statistics.median(resolution),
            "max": max(resolution)},
        "solver_arithmetic_certified": False,
        "original_shard_jsonl_sha256": input_digests,
        "archive_sha256": {p: digest((output / p).read_bytes())
                           for p in ["ganak101-raw.jsonl", "ganak101-science.csv",
                                     "ganak20-eq-to-neq.csv"]},
    }
    (output / "manifest.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    entries = "\n".join(
        f'| {x["id"]} | {x["method"]} | {x["printed_point_distance"]:.7g} | '
        f'{x["print_resolution_distance"]:.7g} | '
        f'{x["resolution_to_tolerance_ratio"]:.2f} |'
        for x in bad_rows)
    readme = f"""# TACAS 2026: Ganak 101 science and the 20 EQ-to-NEQ cases

Research-only source-pinned archive, **not** a production release or
certified numerical error bound. Original QuPRS v0.9.1 SHA: {HISTORICAL}.
Ganak run: https://github.com/PhysicsQoo/QuPRS/actions/runs/{GANAK_RUN}
GPMC comparison run: https://github.com/PhysicsQoo/QuPRS/actions/runs/{GPMC_RUN}

All 24 original Ganak mode-6 CI shards were independently checked against
GPMC case, verdict and QASM source SHA256 identities. Exactly 101 cases,
45 historic EQ and 56 historic NEQ, with zero timeout/missing cases.

**Ganak at distance=2e-5, RR=1e-10, phase=1e-8: 81/101 match; 20
false NEQ; 0 false EQ.** All 56 historic NEQ remain NEQ; 25/45 historic
EQ remain EQ. All 20 mismatches actually called Ganak (14 WMC-only,
6 Hybrid). GPMC Python30, Rust30 and Python90 reproduce all 101 historic
binary decisions independently in the comparison run.

## Twenty discordant cases

Each point distance below is INFERRED from float-parsed printed log2 WMC
magnitude via sqrt(1 - exp(2*ln(2)*(log2_WMC - expected_log2))).
It is NOT a certified quantum projective distance. The resolution column
is a QuPRS output-format diagnostic, NOT a proven Solver rounding bound.

| Case | Method | Inferred point D | Printed resolution D | Resolution / threshold |
|---|---|---:|---:|---:|
{entries}

Point distances for the 20 false NEQ: min {min(distances):.7g},
median {statistics.median(distances):.7g}, max {max(distances):.7g}.
Their print-resolution diagnostics: min {min(resolution):.7g},
median {statistics.median(resolution):.7g},
max {max(resolution):.7g}; every diagnostic exceeds the 2e-5 threshold.

This pattern is consistent with a Ganak MODE-6 OUTPUT limitation, not
proof that its internal complex WMC arithmetic is incorrect. The upstream
pinned src/main.cpp:656 formats the complex MPFR solution with %.8Re:
https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L650-L656
Increasing internal --mpfrprec does not recover discarded output digits.
The 56 historical NEQ controls are far from the threshold and do not
prove that a larger tolerance is safe on arbitrary inputs.

Files:
- ganak101-raw.jsonl: all 101 original complete scientific verifier records.
- ganak101-science.csv: 101-row binary/printed-number/GPMC crosscheck.
- ganak20-eq-to-neq.csv: focused 20-row P1 numerical comparison.
- manifest.json: original run IDs and SHA256 checks of shard and archive data.

No solver internals or production defaults changed. Solver arithmetic,
CNF normalization and weight/angle error remain NOT_CERTIFIED.
Performance is not evaluated here and requires CodSpeed.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ganak-dir", type=Path, required=True)
    p.add_argument("--gpmc-json", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(archive(args.ganak_dir, args.gpmc_json, args.out_dir),
                     indent=2, sort_keys=True))

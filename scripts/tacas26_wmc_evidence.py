#!/usr/bin/env python3
"""Index real, source-pinned TACAS v0.9.1 GPMC numeric observations.

Read ONLY the permanent Git-tracked source results, no Solver, no CodSpeed.
Do not infer unprinted precision, add fabricated significant figures or
classify missing WMC data as numerical zero.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs/development/tacas26-results/results.json"
OUT = ROOT / "docs/development/tacas26-results"
PREFIX = "c s exact double prec-sci"
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
COMPLEX = re.compile(rf"({NUMBER})\s*([+-](?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)i")
REAL = re.compile(NUMBER)
IMAGINARY = re.compile(rf"({NUMBER})i")
FIELDS = (
    "id", "suite", "case", "kind", "method", "verdict", "status",
    "source_run_id", "source_artifact", "source_sha", "gpmc_sha256",
    "original_qasm_sha256", "counterpart_qasm_sha256",
    "solver_invoked", "wmc_evidence_status", "solver_returncode",
    "solver_count_raw_line", "solver_real_printed", "solver_imag_printed",
    "original_float_real", "original_float_imag",
    "expected_log2", "rounded_log2", "raw_log2_abs_wmc",
    "original_phase_rad", "v091_replayed_verdict",
    "source_result_sha256",
)

def extract_printed_count(stdout):
    """Extract exactly what the original GPMC printed; no extra precision."""
    if not isinstance(stdout, str):
        return {"raw_line": None, "real": None, "imag": None, "status": "NO_STDOUT"}
    lines = [line.strip() for line in stdout.splitlines()
             if line.lstrip().startswith(PREFIX)]
    if not lines:
        return {"raw_line": None, "real": None, "imag": None, "status": "NO_COUNT_LINE"}
    if len(lines) != 1:
        return {"raw_line": "\n".join(lines), "real": None, "imag": None,
                "status": "MULTIPLE_COUNT_LINES"}
    line = lines[0]
    text = line[len(PREFIX):].strip()
    # v0.9.1 accepted exactly two real/imag numerical components, real-only
    # or imaginary-only; avoid interpreting unrelated solver diagnostics.
    found = COMPLEX.search(text)
    if found:
        real, imag = found.groups()
    elif (found := IMAGINARY.search(text)) and not REAL.match(text):
        real, imag = "0", found.group(1)
    elif (found := REAL.search(text)) and not IMAGINARY.search(text):
        real, imag = found.group(0), "0"
    else:
        return {"raw_line": line, "real": None, "imag": None,
                "status": "UNPARSED_COUNT_LINE"}
    try:
        Decimal(real)
        Decimal(imag)
    except InvalidOperation:
        return {"raw_line": line, "real": None, "imag": None,
                "status": "UNPARSED_COUNT_LINE"}
    return {"raw_line": line, "real": real, "imag": imag,
            "status": "PRINTED_COMPONENTS_AVAILABLE"}


def make_index(archive):
    rows = archive["rows"]
    selected = archive["selected_raw_evidence"]
    records = []
    detail = []
    for case in rows:
        ident = case["id"]
        evidence = selected.get(ident)
        raw = evidence.get("raw") if isinstance(evidence, dict) else None
        raw = raw if isinstance(raw, dict) else {}
        calls = raw.get("solver_calls", [])
        counts = raw.get("complex_counts", [])
        if not isinstance(calls, list) or not isinstance(counts, list):
            raise ValueError("Corrupted solver_calls or complex_counts: "+ident)
        # A source-verification call should use at most one GPMC invocation.
        # Preserve all raw calls, and flag multiple invocations for manual review.
        if len(calls) > 1 or len(counts) > 1:
            numeric_status = "MULTIPLE_GPMC_INVOCATIONS_REVIEW"
        elif not calls and not counts:
            numeric_status = ("SOURCE_CENSORED_OR_MISSING"
                              if case["status"] in ("EXTERNAL_TIMEOUT","MISSING_RESULT")
                              else "NO_WMC_COUNT_CAPTURED")
        elif not calls:
            numeric_status = "FLOAT_COUNT_ONLY"
        else:
            numeric_status = None
        call = calls[0] if calls else {}
        count = counts[0] if counts else {}
        printed = extract_printed_count(call.get("stdout"))
        if numeric_status is None:
            numeric_status = (printed["status"]
                              if printed["status"] != "PRINTED_COMPONENTS_AVAILABLE"
                              else "WMC_PRINTED_VALUE_AVAILABLE")
        row = {
            "id": ident,
            "suite": case["suite"], "case": case["case"],
            "kind": case["kind"], "method": case["method"],
            "verdict": case["observed_verdict"], "status": case["status"],
            "source_run_id": case["run_id"], "source_artifact": case["artifact"],
            "source_sha": raw.get("source_sha", archive["source_sha"]),
            "gpmc_sha256": raw.get("original_gpmc_sha256") or case["gpmc_sha256"],
            "original_qasm_sha256": case["original_sha256"],
            "counterpart_qasm_sha256": case["counterpart_sha256"],
            "solver_invoked": raw.get("solver_invoked"),
            "wmc_evidence_status": numeric_status,
            "solver_returncode": call.get("returncode"),
            "solver_count_raw_line": printed["raw_line"],
            "solver_real_printed": printed["real"],
            "solver_imag_printed": printed["imag"],
            "original_float_real": count.get("real"),
            "original_float_imag": count.get("imag"),
            "expected_log2": raw.get("expected_log2"),
            "rounded_log2": raw.get("rounded_log2"),
            "raw_log2_abs_wmc": raw.get("raw_log2_abs_wmc"),
            "original_phase_rad": raw.get("original_phase_rad"),
            "v091_replayed_verdict": raw.get("v091_replayed_verdict"),
            "source_result_sha256": evidence.get("raw_json_sha256") if evidence else None,
        }
        detail.append({
            "id": ident, "gpmc_invocations": calls,
            "original_binary64_counts": counts,
            "numeric_summary": row,
        })
        records.append(row)
    if len(records) != 184 or len({x["id"] for x in records}) != 184:
        raise ValueError("Canonical 184 direct calls missing or duplicated")
    return records, detail


def generate(archive_path=ARCHIVE, out=OUT):
    archive = json.loads(Path(archive_path).read_text(encoding="utf-8"))
    rows, detail = make_index(archive)
    counts = Counter(row["wmc_evidence_status"] for row in rows)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with (out/"wmc-evidence.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    dataset = {
        "schema": "quprs-tacas26-historical-gpmc-numeric-v1",
        "purpose": "Historical CI scientific reproducibility and future tolerance studies",
        "historical_version": "v0.9.1",
        "historical_source_sha": archive["source_sha"],
        "source_archive": "results.json",
        "raw_output_format": "GPMC -mode=1: c s exact double prec-sci",
        "source_numeric_semantics": (
            "Original QuPRS parses GPMC stdout via Python float; compares "
            "round(log2(abs(WMC)), 3) with expected_log2 and compares "
            "global phase with historical 1e-10 tolerance. "
            "Printed digits are not certified precision."
        ),
        "limitations": (
            "No implied MPFR/error bounds, no guaranteed higher-precision "
            "unprinted digits, and no automatic modern projective-distance "
            "certificate. Missing/censored outputs must not be treated as 0."
        ),
        "counts": dict(sorted(counts.items())),
        "records": detail,
    }
    (out/"wmc-evidence.json").write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2, sort_keys=True)+"\n",
        encoding="utf-8")
    return dict(sorted(counts.items()))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archive", type=Path, default=ARCHIVE)
    p.add_argument("--output", type=Path, default=OUT)
    a = p.parse_args()
    print(json.dumps(generate(a.archive, a.output), sort_keys=True))


if __name__ == "__main__":
    main()

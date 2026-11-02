#!/usr/bin/env python3
"""Optional same-SHA numeric join from a verified CodSpeed run export.

The GitHub cross-instrument JSON is a provenance/coverage report, not a
CPU numeric export. This tool never fabricates CPU numbers or interpolates
walltime and simulation. A trusted same-SHA CodSpeed retrieval must provide
numeric observations in a separate input. Until then: MISSING_NUMERIC.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.codspeed.case_registry import NATIVE_IDS, PYTHON_CORE_CASE_IDS


def join(evidence: dict, remote: dict) -> dict:
    sha = evidence["head_sha"]
    if evidence.get("schema") != "quprs-codspeed-cross-instrument-v2":
        raise ValueError("invalid cross instrument evidence schema")
    records = remote.get("results", [])
    if not isinstance(records, list):
        raise ValueError("remote results must be a list")
    lookup = {}
    for row in records:
        if row.get("sha") != sha:
            raise ValueError("cross-commit CodSpeed observation is forbidden")
        if row.get("measured_in_run") is not True or not row.get("run_id"):
            raise ValueError("CodSpeed carry-forward/not-source-certified observation")
        key = (row.get("runner_mode"), row.get("uri"))
        if key in lookup:
            raise ValueError("duplicate CodSpeed numeric observation")
        value = row.get("value")
        if not isinstance(value, (float, int)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError("invalid CodSpeed numeric measurement")
        mode = row.get("runner_mode")
        valid_units = {
            "Simulation": {"s", "ms", "us", "ns"},
            "WallTime": {"s", "ms", "us", "ns"},
            "Memory": {"B", "KiB", "MiB"},
        }
        if mode not in valid_units or row.get("unit") not in valid_units[mode]:
            raise ValueError("instrument and unit are incompatible")
        if not row.get("cpu_model"):
            raise ValueError("runner cohort must be recorded")
        lookup[key] = row

    joined = []
    for base in evidence.get("cross_instrument_rows", []):
        key = ("Simulation", base["simulation_uri"])
        measurement = lookup.get(key)
        # Numeric measurements are not enough to conclude performance GO;
        # paired WallTime comes from an independent already-audited source.
        status = "MISSING_NUMERIC"
        if measurement is not None:
            status = "NUMERIC_AVAILABLE"
            if not base.get("comparable_verdict"):
                status = "INCOMPARABLE_VERDICT"
            # Global Ganak printed-resolution caveat must not mark unrelated
            # GPMC same-source rows as noncomparable. Use per-case verdict.
        joined.append({
            "case": base["case"], "sha": sha, "status": status,
            "simulation_uri": base["simulation_uri"],
            "cpu_model": measurement.get("cpu_model") if measurement else None,
            "numeric_cpu": {"value": measurement["value"],
                            "unit": measurement["unit"],
                            "run_id": measurement["run_id"]} if measurement else None,
            "walltime": {
                "base_median_ms": base["walltime_base_median_ms"],
                "head_median_ms": base["walltime_head_median_ms"],
                "source": "separate CodSpeed WallTime instrument",
            },
            "warning": "CPU modeled cycles and real WallTime cannot be subtracted",
        })
    # Source exact native coverage is separate from the original 32 and
    # the three common CPU/WallTime cases. Rust microbench CPU numbers are
    # only available in the authorized CodSpeed service's measured run.
    native_core = []
    for native_id in NATIVE_IDS:
        uri = f"benches/core.rs::{native_id}"
        row = lookup.get(("Simulation", uri))
        native_core.append({
            "identity": native_id, "uri": uri,
            "status": "NUMERIC_AVAILABLE" if row else "MISSING_NUMERIC",
            "measurement": ({
                "run_id": row["run_id"], "value": row["value"],
                "unit": row["unit"], "cpu_model": row["cpu_model"],
            } if row else None),
        })
    legacy_uris = evidence.get("simulation_uris", [])
    if legacy_uris and (len(legacy_uris) != 32 or len(set(legacy_uris)) != 32):
        raise ValueError("canonical simulation URI inventory must contain 32 unique identities")
    legacy_core = [{
        "uri": uri,
        "status": ("NUMERIC_AVAILABLE" if ("Simulation", uri) in lookup
                   else "MISSING_NUMERIC"),
        "measurement": (lookup.get(("Simulation", uri)) and {
            key: lookup[("Simulation", uri)][key]
            for key in ("run_id", "value", "unit", "cpu_model")
        })
    } for uri in legacy_uris]

    python_core = []
    if evidence.get("optional_python_core_count") == len(PYTHON_CORE_CASE_IDS):
        for case in PYTHON_CORE_CASE_IDS:
            uri = ("benchmarks/codspeed/test_python_core.py::"
                   f"test_python_algorithm_cpu[{case}]")
            row = lookup.get(("Simulation", uri))
            python_core.append({
                "identity": case, "uri": uri,
                "status": "NUMERIC_AVAILABLE" if row else "MISSING_NUMERIC",
                "measurement": ({
                    key: row[key] for key in ("run_id", "value", "unit", "cpu_model")
                } if row else None)
            })
    return {
        "schema": "quprs-same-sha-numeric-v3",
        "sha": sha,
        "cases": joined,
        "legacy_core": legacy_core,
        "legacy_expected_count": len(legacy_uris),
        "legacy_missing_numeric": sum(x["measurement"] is None for x in legacy_core),
        "python_core": python_core,
        "python_core_expected_count": len(python_core),
        "python_core_missing_numeric": sum(x["measurement"] is None for x in python_core),
        "native_core": native_core,
        "native_core_expected_count": len(NATIVE_IDS),
        "native_core_missing_numeric": sum(x["measurement"] is None for x in native_core),
        "missing_numeric": sum(row["status"] == "MISSING_NUMERIC" for row in joined),
        "numerical_cross_validation_complete": bool(joined) and all(
            row["status"] == "NUMERIC_AVAILABLE" for row in joined)
            and all(row["measurement"] is not None for row in native_core)
            and (not legacy_uris or all(row["measurement"] is not None for row in legacy_core))
            and all(row["measurement"] is not None for row in python_core),
        "performance_certified": False,
        "external_source_status": ("PARTIALLY_MISSING" if (
            any(row["numeric_cpu"] is None for row in joined)
            or any(row["measurement"] is None for row in native_core)
            or any(row["measurement"] is None for row in legacy_core)
            or any(row["measurement"] is None for row in python_core)
        ) else "EXACT_SHA_NUMERIC_RECEIVED"),
        "source": "CodSpeed platform numeric export REQUIRED, GitHub identity JSON insufficient",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cross-evidence", type=Path, required=True)
    p.add_argument("--codspeed-results", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    output = join(json.loads(a.cross_evidence.read_text()),
                  json.loads(a.codspeed_results.read_text()))
    a.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

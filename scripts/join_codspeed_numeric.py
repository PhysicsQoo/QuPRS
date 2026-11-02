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
        if row.get("unit") not in {"s", "ms", "us", "ns", "B", "KiB", "MiB"}:
            raise ValueError("missing or unsupported instrument unit")
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
            if evidence.get("scientific_status") == "PRECISION_LIMITED":
                status = "PRECISION_LIMITED"
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
    return {
        "schema": "quprs-same-sha-numeric-v3",
        "sha": sha,
        "cases": joined,
        "missing_numeric": sum(row["status"] == "MISSING_NUMERIC" for row in joined),
        "numerical_cross_validation_complete": bool(joined) and all(
            row["numeric_cpu"] is not None for row in joined),
        "performance_certified": False,
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

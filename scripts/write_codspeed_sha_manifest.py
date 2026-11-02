#!/usr/bin/env python3
"""Write an exact-commit identity record AFTER the CodSpeed action succeeded."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


NATIVE_IDS = (
    "native_rr_tolerance[0.0000000001]", "native_rr_tolerance[0.00000001]",
    "native_rr_tolerance[0]", "phase_clifford_add", "phase_clifford_sub",
    "phase_decimal_add", "phase_decimal_scale", "phase_decimal_sub",
    "phase_symbolic_add", "rr_hh_pipeline", "rr_nonclifford_pipeline",
)


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def write_manifest(path, *, expected_sha, family, instrument, shard=None,
                   measurement=None, fixture_sha=None):
    actual_sha = git("rev-parse", "HEAD")
    if actual_sha != expected_sha:
        raise ValueError(f"benchmark checkout mismatch: {actual_sha} != {expected_sha}")
    document = {
        "schema": "quprs-codspeed-sha-v2", "sha": actual_sha,
        "tree_sha": git("rev-parse", "HEAD^{tree}"),
        "gpmc_submodule_sha": git("rev-parse", "HEAD:GPMC"),
        "family": family, "instrument": instrument,
        "shard": shard, "num_shards": 5 if shard is not None else None,
        "runner_os": os.getenv("RUNNER_OS"), "runner_arch": os.getenv("RUNNER_ARCH"),
        "runner_name": os.getenv("RUNNER_NAME"),
        "measurement_status": "uploaded_by_codspeed_action",
        "fixture_revision_sha": fixture_sha or actual_sha,
    }
    if family == "rust-core":
        document["expected_ids"] = list(NATIVE_IDS)
        document["metric_location"] = "CodSpeed service (cargo-codspeed)"
    if measurement is not None:
        raw = Path(measurement)
        if not raw.is_file():
            raise ValueError(f"missing first-party CodSpeed export: {raw}")
        document["measurement_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return document


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--family", choices=("simulation-shard", "rust-core", "solver-cpu", "cross-method"), required=True)
    p.add_argument("--instrument", required=True)
    p.add_argument("--shard", type=int, choices=range(5))
    p.add_argument("--measurement", type=Path)
    p.add_argument("--fixture-sha")
    a = p.parse_args()
    write_manifest(a.output, expected_sha=a.sha, family=a.family,
                   instrument=a.instrument, shard=a.shard,
                   measurement=a.measurement, fixture_sha=a.fixture_sha)


if __name__ == "__main__":
    main()

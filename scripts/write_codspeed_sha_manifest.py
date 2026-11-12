#!/usr/bin/env python3
"""Write an exact-commit identity record AFTER the CodSpeed action succeeded."""
import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path


import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.gpmc_release_source_identity import source_commit as pinned_gpmc_source_commit
from benchmarks.codspeed.case_registry import NATIVE_IDS
from benchmarks.codspeed.suite_compat import (
    load_catalog, normalize_manifest, suite_spec_digest,
)

def measured_cpu_model():
    if platform.system() == "Linux":
        path = Path("/proc/cpuinfo")
        if path.is_file():
            for line in path.read_text(errors="replace").splitlines():
                if line.startswith("model name") and ":" in line:
                    return line.split(":", 1)[1].strip()
    return platform.processor() or None


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def write_manifest(path, *, expected_sha, family, instrument, shard=None,
                   measurement=None, fixture_sha=None, suite_id=None,
                   num_shards=None):
    actual_sha = git("rev-parse", "HEAD")
    if actual_sha != expected_sha:
        raise ValueError(f"benchmark checkout mismatch: {actual_sha} != {expected_sha}")
    document = {
        "schema": "quprs-codspeed-sha-v2", "sha": actual_sha,
        "tree_sha": git("rev-parse", "HEAD^{tree}"),
        "gpmc_submodule_sha": None,  # Preserved for legacy manifest readers.
        "gpmc_release_source_sha": pinned_gpmc_source_commit(),
        "family": family, "instrument": instrument,
        "shard": shard, "num_shards": 5 if shard is not None else None,
        "runner_os": os.getenv("RUNNER_OS"), "runner_arch": os.getenv("RUNNER_ARCH"),
        "runner_name": os.getenv("RUNNER_NAME"),
        "cpu_model": measured_cpu_model(),
        "runner_image": os.getenv("ImageOS"),
        "runner_image_version": os.getenv("ImageVersion"),
        "measurement_status": "uploaded_by_codspeed_action",
        "fixture_revision_sha": fixture_sha or actual_sha,
    }
    if family == "simulation-shard":
        # v2 manifest remains readable. Explicit source-suite marker makes an
        # incomplete new run distinguishable from archived 32-only runs.
        from benchmarks.codspeed.simulation_addon import QASM261_COUNT, QASM261_SHA256, QASM261_SUITE_ID
        document["simulation_addon"] = {
            "suite": QASM261_SUITE_ID, "count": QASM261_COUNT,
            "identity_sha256": QASM261_SHA256,
        }
    if suite_id is not None:
        catalog = load_catalog()
        suite = next(
            (item for item in catalog["suites"]
             if item["suite_id"] == suite_id), None
        )
        if suite is None:
            raise ValueError(f"Unknown benchmark suite: {suite_id}")
        if instrument.lower() != suite["instrument"].lower():
            raise ValueError("Suite instrument differs from measured instrument")
        if num_shards is None and shard is not None:
            raise ValueError("Versioned suites require explicit num_shards")
        if num_shards is not None and shard is None:
            raise ValueError("Versioned suite shard index missing")
        if num_shards is not None and (
            type(num_shards) is not int or num_shards <= 0
            or type(shard) is not int or not 0 <= shard < num_shards
        ):
            raise ValueError("Versioned suite shard count/index invalid")
        cpu_model = document["cpu_model"] or "unknown-cpu"
        cohort = "|".join(str(value) for value in (
            document["runner_os"] or platform.system(),
            document["runner_arch"] or platform.machine(),
            cpu_model,
            document["runner_image"] or "unknown-image",
            document["runner_image_version"] or "unknown-version",
        ))
        unit = {"simulation": "modeled_cpu_seconds",
                "walltime": "wall_seconds", "memory": "bytes"}[instrument.lower()]
        document.update({
            "schema": "quprs-codspeed-sha-v3",
            "suite_id": suite["suite_id"],
            "suite_version": suite["version"],
            "suite_spec_sha256": suite_spec_digest(suite),
            "measurement_scope": suite["measurement_scope"],
            "simulation_track_subprocess": suite.get("simulation_track_subprocess"),
            "metric_units": unit,
            "runner_cohort": cohort,
            "num_shards": num_shards,
        })
        # Source-pinned fixture identities prove the source configuration;
        # they do NOT imply that a particular candidate was measured.
        fixtures = {}
        root = Path(__file__).resolve().parents[1] / "benchmarks"
        for candidate in suite.get("candidates", []):
            family_root = "Feynman" if candidate["family"] == "feynman" else "MQTBench"
            transpiled = ("h,y,z,t,tdg,cx" if family_root == "Feynman"
                          else "h,ry,rz,cx")
            left = root / family_root / candidate["qasm"]
            right = root / family_root / transpiled / candidate["qasm"]
            if not left.is_file() or not right.is_file():
                raise ValueError(f"Missing pinned QASM pair for {candidate['id']}")
            fixtures[candidate["id"]] = [
                hashlib.sha256(left.read_bytes()).hexdigest(),
                hashlib.sha256(right.read_bytes()).hexdigest(),
            ]
        document["candidate_fixture_sha256"] = fixtures
        normalize_manifest(document)
    elif num_shards is not None and (num_shards != 5 or shard is None):
        raise ValueError("Legacy shard count is fixed at five")
    if suite_id is None and shard is not None and shard not in range(5):
        raise ValueError("Legacy shard index must be in range(5)")
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
    p.add_argument("--family", choices=("simulation-shard", "rust-core", "solver-cpu", "cross-method", "candidate-pilot", "python-core", "stage-repeatability", "p5-abba", "curated-cpu"), required=True)
    p.add_argument("--instrument", required=True)
    p.add_argument("--shard", type=int)
    p.add_argument("--num-shards", type=int)
    p.add_argument("--suite-id", help="Opt-in versioned suite; legacy remains default")
    p.add_argument("--measurement", type=Path)
    p.add_argument("--fixture-sha")
    a = p.parse_args()
    write_manifest(a.output, expected_sha=a.sha, family=a.family,
                   instrument=a.instrument, shard=a.shard,
                   measurement=a.measurement, fixture_sha=a.fixture_sha,
                   suite_id=a.suite_id, num_shards=a.num_shards)


if __name__ == "__main__":
    main()

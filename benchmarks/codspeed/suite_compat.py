"""Versioned CodSpeed suite/manifest compatibility boundary.

This module intentionally does not run a benchmark or assume that a proposed
candidate has a measured CodSpeed result. Legacy v2 manifests stay readable.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CATALOG_FILE = Path(__file__).with_name("suite_catalog.json")
LEGACY_SCHEMA = "quprs-codspeed-sha-v2"
NEW_SCHEMA = "quprs-codspeed-sha-v3"
LEGACY_SUITE_ID = "quprs-legacy-simulation-32-v1"


class SuiteCompatibilityError(ValueError):
    """A benchmark report has missing or changed measurement identity."""


def load_catalog(path: Path = CATALOG_FILE) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != "quprs-codspeed-suite-catalog-v1":
        raise SuiteCompatibilityError("Unrecognized suite catalog schema")
    suites = data.get("suites", [])
    ids = [entry.get("suite_id") for entry in suites]
    if not ids or len(ids) != len(set(ids)):
        raise SuiteCompatibilityError("Missing or duplicate suite identities")
    legacy = next((x for x in suites if x["suite_id"] == LEGACY_SUITE_ID), None)
    if not legacy or (legacy.get("case_count"), legacy.get("shard_count")) != (32, 5):
        raise SuiteCompatibilityError("Legacy 32/five-shard identity missing")
    policy = data.get("policy", {})
    if (policy.get("successor_minor_releases_min", 0) < 3
            or policy.get("coexistence_days_min", 0) < 90):
        raise SuiteCompatibilityError("Insufficient legacy compatibility window")
    return data


def suite_spec_digest(suite: dict) -> str:
    """Stable versioned suite definition hash; never include runtime results."""
    if not isinstance(suite, dict) or not suite.get("suite_id"):
        raise SuiteCompatibilityError("Invalid suite specification")
    return hashlib.sha256(
        json.dumps(suite, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def normalize_manifest(document: dict) -> dict:
    """Normalize old SHA-v2 and new SHA-v3 provenance without fabricating data."""
    schema = document.get("schema")
    required = ("sha", "fixture_revision_sha", "family", "instrument",
                "measurement_status")
    for field in required:
        if not document.get(field):
            raise SuiteCompatibilityError(f"Missing provenance field: {field}")
    if document["sha"] != document["fixture_revision_sha"]:
        raise SuiteCompatibilityError("Source/fixture SHA mismatch")
    if document["measurement_status"] != "uploaded_by_codspeed_action":
        raise SuiteCompatibilityError("No confirmed measurement upload")
    if schema == LEGACY_SCHEMA:
        if document["family"] == "simulation-shard":
            if (document.get("num_shards") != 5
                    or type(document.get("shard")) is not int
                    or document["shard"] not in range(5)):
                raise SuiteCompatibilityError("Invalid legacy simulation shard")
            suite_id = LEGACY_SUITE_ID
            scope = "host_cpu_model_subprocess_excluded"
            tracked = False
        else:
            suite_id = f"legacy-{document['family']}"
            scope = "legacy-instrument-scope-not-specified"
            tracked = None
        return {"schema_version": 2, "suite_id": suite_id,
                "sha": document["sha"], "instrument": document["instrument"],
                "measurement_scope": scope,
                "simulation_track_subprocess": tracked,
                "shard": document.get("shard"),
                "num_shards": document.get("num_shards")}
    if schema != NEW_SCHEMA:
        raise SuiteCompatibilityError("Unsupported SHA manifest schema")
    new_required = ("suite_id", "suite_version", "suite_spec_sha256",
                    "measurement_scope", "metric_units", "runner_cohort")
    for field in new_required:
        if document.get(field) is None or document.get(field) == "":
            raise SuiteCompatibilityError(f"Missing new suite field: {field}")
    if (not isinstance(document["suite_version"], int)
            or isinstance(document["suite_version"], bool)
            or document["suite_version"] < 1):
        raise SuiteCompatibilityError("Invalid suite version")
    if (len(str(document["suite_spec_sha256"])) != 64
            or any(ch not in "0123456789abcdef"
                   for ch in document["suite_spec_sha256"])):
        raise SuiteCompatibilityError("Invalid suite specification SHA-256")
    instrument = document["instrument"].lower()
    if document["suite_id"] not in {x["suite_id"] for x in load_catalog()["suites"]}:
        raise SuiteCompatibilityError("Suite is not registered")
    suite = next(x for x in load_catalog()["suites"] if x["suite_id"] == document["suite_id"])
    if document["suite_version"] != suite["version"]:
        raise SuiteCompatibilityError("Registered suite version mismatch")
    if document["suite_spec_sha256"] != suite_spec_digest(suite):
        raise SuiteCompatibilityError("Suite specification hash mismatch")
    if document["measurement_scope"] != suite["measurement_scope"]:
        raise SuiteCompatibilityError("Suite measurement scope mismatch")
    if instrument != suite["instrument"].lower():
        raise SuiteCompatibilityError("Registered suite instrument mismatch")
    tracked = document.get("simulation_track_subprocess")
    if tracked is not suite.get("simulation_track_subprocess"):
        raise SuiteCompatibilityError("Registered suite subprocess policy mismatch")
    if instrument == "simulation":
        if type(tracked) is not bool:
            raise SuiteCompatibilityError("Simulation subprocess policy missing")
        if tracked and document["measurement_scope"] == "solver_free_algorithm_cpu":
            raise SuiteCompatibilityError("Solver-free CPU scope cannot track Solver subprocess")
        if document["metric_units"] != "modeled_cpu_seconds":
            raise SuiteCompatibilityError("Simulation metric units mismatch")
    elif instrument == "walltime":
        if tracked is not None:
            raise SuiteCompatibilityError("WallTime cannot declare Simulation tracking")
        if document["metric_units"] != "wall_seconds":
            raise SuiteCompatibilityError("WallTime metric units mismatch")
    elif instrument == "memory":
        if tracked is not None:
            raise SuiteCompatibilityError("Memory cannot declare Simulation tracking")
        if document["metric_units"] != "bytes":
            raise SuiteCompatibilityError("Memory metric units mismatch")
    else:
        raise SuiteCompatibilityError("Unknown CodSpeed instrument")
    count, index = document.get("num_shards"), document.get("shard")
    if count is not None:
        if (type(count) is not int or count <= 0 or type(index) is not int
                or not 0 <= index < count):
            raise SuiteCompatibilityError("Invalid versioned shard identity")
    elif index is not None:
        raise SuiteCompatibilityError("Shard index without shard count")
    return {"schema_version": 3, "suite_id": document["suite_id"],
            "suite_version": document["suite_version"],
            "suite_spec_sha256": document["suite_spec_sha256"],
            "sha": document["sha"], "instrument": instrument,
            "measurement_scope": document["measurement_scope"],
            "simulation_track_subprocess": tracked,
            "metric_units": document["metric_units"],
            "runner_cohort": document["runner_cohort"],
            "shard": index, "num_shards": count}


def measurement_comparability(base: dict, head: dict) -> tuple[bool, tuple[str, ...]]:
    """Prevent a retired, carried-forward or newly scoped record from faking a baseline."""
    base = normalize_manifest(base)
    head = normalize_manifest(head)
    fields = ("schema_version", "suite_id", "instrument",
              "measurement_scope", "simulation_track_subprocess")
    if base["schema_version"] == 3 and head["schema_version"] == 3:
        fields += ("suite_version", "suite_spec_sha256", "metric_units",
                   "runner_cohort")
    differences = tuple(field for field in fields if base.get(field) != head.get(field))
    return not differences, differences


def identity_digest(uris) -> str:
    names = list(uris)
    if len(names) != len(set(names)) or not names:
        raise SuiteCompatibilityError("Empty or duplicated benchmark identities")
    return hashlib.sha256("\n".join(sorted(names)).encode("utf-8")).hexdigest()

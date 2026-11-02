"""Stable migration contract tests; no network, solver or CodSpeed invocation."""
import json
from pathlib import Path

import pytest

from benchmarks.codspeed.suite_compat import (
    SuiteCompatibilityError, identity_digest, load_catalog,
    measurement_comparability, normalize_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40


def old_manifest():
    return {"schema": "quprs-codspeed-sha-v2", "sha": SHA,
            "fixture_revision_sha": SHA, "family": "simulation-shard",
            "instrument": "simulation", "shard": 0, "num_shards": 5,
            "measurement_status": "uploaded_by_codspeed_action"}


def new_manifest():
    return {"schema": "quprs-codspeed-sha-v3", "sha": SHA,
            "fixture_revision_sha": SHA, "family": "curated-cpu",
            "instrument": "simulation", "shard": 0, "num_shards": 3,
            "measurement_status": "uploaded_by_codspeed_action",
            "suite_id": "quprs-curated-simulation-v2", "suite_version": 2,
            "suite_spec_sha256": "b" * 64, "runner_cohort": "hosted-linux",
            "measurement_scope": "solver_free_algorithm_cpu",
            "simulation_track_subprocess": False,
            "metric_units": "modeled_cpu_seconds"}


def test_suite_catalog_has_minimum_three_successor_minor_versions():
    catalog = load_catalog()
    policy = catalog["policy"]
    assert policy["initial_release"] == "0.14.0"
    assert policy["legacy_full_run_through"] == "0.17.0"
    assert policy["earliest_legacy_retirement"] == "0.18.0"
    assert policy["successor_minor_releases_min"] >= 3
    assert policy["coexistence_days_min"] >= 90
    legacy, proposed = catalog["suites"]
    assert (legacy["case_count"], legacy["shard_count"]) == (32, 5)
    assert legacy["identity_sha256"] == (
        "7eb82617bf092c81c6a6bde6e8cd05cec9bab71879f17b2bf315c9c420c7c8ed")
    assert proposed["state"] == "candidate-not-promoted"
    assert len(proposed["candidates"]) == 9
    assert all(x["evidence"] == "PILOT_NEEDED" for x in proposed["candidates"])
    assert all(x["planned_cadence"] == "opt_in" for x in proposed["candidates"])
    assert len({x["id"] for x in proposed["candidates"]}) == 9
    for candidate in proposed["candidates"]:
        folder = "Feynman" if candidate["family"] == "feynman" else "MQTBench"
        assert (ROOT / "benchmarks" / folder / candidate["qasm"]).is_file()


def test_paper_table2_identity_matches_source_manifest_not_just_count():
    observed = json.loads(
        (ROOT / "benchmarks/codspeed/paper_difficulty.json").read_text(encoding="utf-8"))
    pinned = json.loads(
        (ROOT / "docs/development/paper-corpus-manifest.json").read_text(encoding="utf-8"))
    def normalized(key):
        if key.startswith("grover-noancilla_"):
            return key.replace("grover-noancilla_", "grover")
        if key.startswith("qwalk-noancilla_"):
            return key.replace("qwalk-noancilla_", "qwalk")
        return key.replace("_", "")
    actual = {row["id"] for row in observed["cases"]}
    expected = {normalized(row["id"]) for row in pinned["cohorts"]["table2_mqt"]["cases"]}
    assert len(actual) == len(expected) == 36
    assert actual == expected
    assert "graphstate64" in actual
    assert "wstate32" not in actual
    assert {row["id"] for row in observed["table3_only_cases"]} == {"wstate32"}
    assert pinned["additional_mqt_pair"]["id"] == "wstate_32"


def test_legacy_sha_v2_readable_and_not_reinterpreted():
    record = normalize_manifest(old_manifest())
    assert record["schema_version"] == 2
    assert record["simulation_track_subprocess"] is False
    assert record["num_shards"] == 5
    assert measurement_comparability(old_manifest(), old_manifest()) == (True, ())
    bad = {**old_manifest(), "num_shards": 3}
    with pytest.raises(SuiteCompatibilityError):
        normalize_manifest(bad)


def test_new_v3_dynamic_shards_are_safe_and_metrics_cannot_change_silently():
    new = new_manifest()
    assert normalize_manifest(new)["num_shards"] == 3
    assert measurement_comparability(new, dict(new)) == (True, ())
    for bad in (
        {**new, "metric_units": "wall_seconds"},
        {**new, "simulation_track_subprocess": True},
        {**new, "shard": 3},
        {**new, "suite_spec_sha256": ""},
        {**new, "fixture_revision_sha": "b" * 40},
    ):
        with pytest.raises(SuiteCompatibilityError):
            normalize_manifest(bad)


def test_old_and_new_or_changed_scope_are_incomparable():
    ok, difference = measurement_comparability(old_manifest(), new_manifest())
    assert not ok and ("schema_version" in difference or "suite_id" in difference)
    other = {**new_manifest(), "runner_cohort": "different-runner"}
    ok, difference = measurement_comparability(new_manifest(), other)
    assert not ok and "runner_cohort" in difference
    with pytest.raises(SuiteCompatibilityError):
        identity_digest(["duplicated", "duplicated"])

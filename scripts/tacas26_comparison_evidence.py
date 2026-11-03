#!/usr/bin/env python3
"""Create immutable, verifiable TACAS26 Qiskit->QuPRS evidence inventory.

This script archives observed *compiler* evidence separately from planned
v0.9.1/v0.14.0 verifier experiments. It does not run QuPRS or invent WMC/RR
results. Python standard-library only; no numerical or timing measurements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

from scripts.tacas26_qiskit_version_fidelity import CASE_IDS, LEVELS

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ("1.4.2", "2.6.1")
VERSION_FILES = {"1.4.2": "qiskit142.json", "2.6.1": "qiskit261.json"}
HISTORICAL_QUPRS_SHA = "e928abc47dd15926364ec77905eb0d5dc92ce8cc"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_jsonl(path: Path, records: list[dict]) -> None:
    if not records:
        raise ValueError("Cannot archive empty evidence set")
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"
                for row in records), encoding="utf8",
    )


def check_sha(path: Path, expected: str) -> None:
    if not path.is_file() or digest(path) != expected:
        raise ValueError("Missing or checksum-mismatched immutable input: " + str(path))


def make_archive(root: Path) -> None:
    by_version = {}
    for version in VERSIONS:
        data = json.loads((root / VERSION_FILES[version]).read_text(encoding="utf8"))
        if data.get("qiskit_version") != version:
            raise ValueError("Unpinned version payload: " + version)
        by_version[version] = data

    comparison = json.loads((root / "comparison.json").read_text(encoding="utf8"))
    settings = comparison["fixed_config"]
    for version in VERSIONS:
        source = by_version[version]
        for name in ("basis", "seed", "levels", "approximation_degree"):
            if list(source[name]) != list(settings[name]) if name in ("basis", "levels") else source[name] != settings[name]:
                raise ValueError("Transpile settings differ: " + name)

    inputs = []
    plans = []
    checksums = {}
    ids = set()
    archive_case_ids = set()
    versions = {}
    for version in VERSIONS:
        source = by_version[version]
        versions[version] = {row["case"]: row for row in source["cases"]}
        if set(versions[version]) != set(CASE_IDS):
            raise ValueError("Transpiler results are incomplete for " + version)
    for case in CASE_IDS:
        left, right = (versions[v][case] for v in VERSIONS)
        for field in ("original_sha256", "historic_sha256", "qubits"):
            if left[field] != right[field]:
                raise ValueError("Two versions did not share input identity: " + case)
        for version in VERSIONS:
            sample = versions[version][case]
            for level in LEVELS:
                transpile = next(row for row in sample["transpiles"]
                                 if row["level"] == level)
                if transpile["status"] != "OK":
                    raise ValueError("Compiler error requires explicit rerun or failed archive: "
                                     + case + " " + version)
                name = transpile.get("qasm2_file")
                if not name or not name.endswith(".qasm"):
                    raise ValueError("Actual transpiled QASM bytes were not archived")
                path = root / name
                if path.resolve().is_relative_to(root.resolve()) is False:
                    raise ValueError("QASM path escaped the evidence archive")
                check_sha(path, transpile["qasm2_sha256"])
                checksums[name] = digest(path)
                key = case + ":qiskit-" + version + ":opt-" + str(level)
                if key in ids:
                    raise ValueError("Duplicate evidence identity")
                ids.add(key)
                archive_case_ids.add(case)
                metric = transpile["serialized"]
                if metric["metric_kind"] != sample["historical_saved"]["metric_kind"]:
                    raise ValueError("Incompatible metric meaning")
                inputs.append({
                    "evidence_type": "OBSERVED_QISKIT_TRANSPILATION",
                    "schema": "tacas26-transpiled-input-evidence-v1",
                    "input_id": key,
                    "case": case,
                    "qubits": sample["qubits"],
                    "original_qasm": {
                        "path_in_repository": sample.get("original_file"),
                        "sha256": sample["original_sha256"],
                    },
                    "paper_transpiled_qasm": {
                        "sha256": sample["historic_sha256"],
                        "numeric_check": sample["historical_saved"],
                        "original_compiler_settings": "UNKNOWN",
                    },
                    "compiled_qasm": {
                        "path_in_evidence_archive": name,
                        "sha256": checksums[name],
                        "serialization": "OPENQASM_2",
                        "full_bytes_in_git_archive": True,
                    },
                    "compiler": {
                        "name": "qiskit",
                        "version": version,
                        "seed": source["seed"],
                        "basis": source["basis"],
                        "optimization_level": level,
                        "approximation_degree": source["approximation_degree"],
                        "numpy_version": source["numpy_version"],
                        "source_corpus_commit": source["source_sha"],
                    },
                    "circuit": {
                        "gates": transpile["gates"],
                        "depth": transpile["depth"],
                        "compiler_global_phase_float": transpile["global_phase"],
                    },
                    "fidelity": {
                        "metric_kind": metric["metric_kind"],
                        "serialized_qasm2_vs_original": metric,
                        "in_memory_vs_original": transpile["compiled_in_memory"],
                        "mathematical_certificate": False,
                    },
                })
                for verifier_name, verifier_sha in (
                    ("v0.9.1", HISTORICAL_QUPRS_SHA),
                    ("v0.14.0-candidate", None),
                ):
                    plans.append({
                        "schema": "tacas26-planned-quprs-verifier-record-v1",
                        "observation": False,
                        "input_id": key,
                        "verifier_name": verifier_name,
                        "verifier_source_sha": verifier_sha,
                        "execution_status": "NOT_COLLECTED",
                        "backend": None,
                        "strategy": None,
                        "solver": None,
                        "tolerances": {
                            "rr_tolerance": None,
                            "wmc_phase_tolerance": None,
                            "approximate_distance_tolerance": None,
                            "wmc_magnitude_tolerance": None,
                            "legacy_tolerance": None,
                            "classifier_definition": None,
                        },
                        "rr": {
                            "status": "NOT_COLLECTED",
                            "entered": None,
                            "ended_before_wmc": None,
                            "rules_applied": None,
                            "residual_pathsum_sha256": None,
                            "residual_cnf_sha256": None,
                        },
                        "wmc": {
                            "status": "NOT_COLLECTED",
                            "invoked": None,
                            "solver_binary_sha256": None,
                            "solver_mode": None,
                            "internal_precision_bits": None,
                            "internal_precision_decimal_digits": None,
                            "printed_precision_significant_digits": None,
                            "input_weights_sha256": None,
                            "raw_stdout": None,
                            "raw_stderr": None,
                            "raw_stdout_sha256": None,
                            "printed_real": None,
                            "printed_imag": None,
                            "parsed_real": None,
                            "parsed_imag": None,
                            "normalization_exponent": None,
                            "printed_point_projective_distance": None,
                            "distance_error_bound_certified": None,
                        },
                        "verdict": {
                            "status": "NOT_COLLECTED",
                            "label": None,
                            "binary_class": None,
                            "decision_basis": None,
                            "precision_warning": None,
                        },
                        "failure": {
                            "kind": None,
                            "message": None,
                            "solver_timeout": None,
                            "external_watchdog_censoring": None,
                        },
                        "execution_provenance": {
                            "github_run_id": None,
                            "source_sha": None,
                            "environment": None,
                            "qasm_input_sha256": checksums[name],
                        },
                        "performance": {
                            "codspeed_run_id": None,
                            "codspeed_benchmark_id": None,
                        },
                    })
    if len(inputs) != 36 or len(plans) != 72 or len(archive_case_ids) != 9:
        raise ValueError("Unexpected evidence row cardinalities")
    input_name = "transpiled-inputs.jsonl"
    plan_name = "planned-verifier-runs.jsonl"
    dump_jsonl(root / input_name, inputs)
    dump_jsonl(root / plan_name, plans)
    checksums.update({
        input_name: digest(root/input_name),
        plan_name: digest(root/plan_name),
        "qiskit142.json": digest(root/"qiskit142.json"),
        "qiskit261.json": digest(root/"qiskit261.json"),
        "comparison.json": digest(root/"comparison.json"),
        "comparison.csv": digest(root/"comparison.csv"),
    })
    manifest = {
        "schema": "tacas26-transpiler-and-verifier-provenance-v1",
        "scope": "EXPERIMENT_ONLY_NO_RELEASE_IMPACT",
        "source_branch": "experiment/tacas26-paper-reproduction",
        "original_quprs_sha": HISTORICAL_QUPRS_SHA,
        "compiler_versions": list(VERSIONS),
        "compiler_observed_rows": len(inputs),
        "verifier_planned_not_collected_rows": len(plans),
        "verifier_observed_rows": 0,
        "case_count": len(archive_case_ids),
        "source_git_commit_at_ci": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_workflow": os.getenv("GITHUB_WORKFLOW"),
        "collector_python": platform.python_version(),
        "collector_platform": platform.platform(),
        "retention": "GIT_TRACKED_PERMANENT_PLUS_ACTIONS_ARTIFACT",
        "source_legacy_wmc_archive": (
            "docs/development/tacas26-results/wmc-evidence.json"
        ),
        "source_ganak_archive": (
            "docs/development/tacas26-ganak101-permanent/ganak101-raw.jsonl"
        ),
        "interpretation": {
            "numerical_certified": False,
            "performance_certified": False,
            "sampled_state_distance_is_not_projective_trace": True,
            "uncollected_solver_values_are_null_not_zero": True,
            "planned_verifier_records_are_not_experiment_results": True,
            "historical_wmc_comes_from_different_transpiled_qasm": True,
        },
        "file_sha256": dict(sorted(checksums.items())),
    }
    (root/"evidence-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)+"\n", encoding="utf8"
    )
    print("TACAS26_EVIDENCE_ARCHIVED",json.dumps({
        "observed_transpiled_qasm":len(inputs),
        "planned_not_executed_verifications":len(plans),
        "full_qasm_files":len(checksums)-6,
        "manifest_sha256":digest(root/"evidence-manifest.json"),
    },sort_keys=True))


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive-dir",required=True,type=Path)
    make_archive(parser.parse_args().archive_dir)

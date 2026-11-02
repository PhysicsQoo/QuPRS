#!/usr/bin/env python3
"""Read-only TACAS'26 v0.9.1 WMC classifier replay.

Historical reproduction is a separate scientific observation, never the
production QuPRS classifier or an alternative performance timer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ARTIFACT_REPO = "PhysicsQoo/Artifact-of-tacas26"
ARTIFACT_SHA = "d8d3e7da555e9e20bdec6f3abe4a13ad899af62b"
QU_PRS_TAG = "v0.9.1"
QU_PRS_SHA = "e928abc47dd15926364ec77905eb0d5dc92ce8cc"
ARTIFACT_TIMEOUT_SECONDS = 200
ARTIFACT_STRATEGY = "Proportional"
LEGACY_TOLERANCE = 1e-10
QPE20_SOURCE_SHA256 = {
    "original": "1aab3d61462144fc59ace2ffda5d2382776aec4bf5f1bacdb8ac31ee7400751c",
    "transpiled": "3d8370285c872197c45853c0ebe96be09ef08eabe998da48d426de80e54aeb82",
}
PAPER_EXPECTED_VERDICT = "equivalent*"

def replay_classifier(log2_abs_count: float, expected_log2: float,
                      theta_rad: float | None = None) -> dict:
    """Reproduce v0.9.1 WMC classification order: round first, compare after.

    The archived code uses numpy.log2(float magnitude) followed by Python
    round(..., 3). The input here is already the recorded log2 magnitude.
    An omitted phase MUST NOT be silently inferred as equivalent*.
    """
    z = float(log2_abs_count)
    normal = float(expected_log2)
    if not math.isfinite(z) or not math.isfinite(normal):
        raise ValueError("Nonfinite input cannot be replayed")
    rounded = round(z, 3)
    pass_magnitude = abs(rounded - normal) < LEGACY_TOLERANCE
    if not pass_magnitude:
        verdict = "not_equivalent"
    elif theta_rad is None:
        verdict = "PHASE_UNOBSERVED"
    else:
        if not math.isfinite(theta_rad):
            raise ValueError("Nonfinite phase cannot be replayed")
        verdict = ("equivalent" if abs(theta_rad) <
                   LEGACY_TOLERANCE * math.tau else "equivalent*")
    return {
        "rounded_log2_magnitude": rounded,
        "expected_log2": normal,
        "magnitude_accepted": pass_magnitude,
        "phase_rad_available": theta_rad is not None,
        "legacy_verdict": verdict,
        "precision_rounding_is_not_a_rigorous_distance_bound": True,
    }

def replay_qpe20_observation(report: dict) -> dict:
    """Reconcile same source identities, actual modern calls, legacy formula.

    This performs no solver call, has no runtime benchmarking, and cannot
    certify archived Docker execution or exact source operator equivalence.
    """
    identities = report.get("source_qasm_sha256", {})
    for key, expected in QPE20_SOURCE_SHA256.items():
        if identities.get(key) != expected:
            raise ValueError(f"Unpinned source: {key}")
    probes = report.get("observations", [])
    if len(probes) != len({x.get("id") for x in probes}):
        raise ValueError("Duplicate observed source probes")
    rows = {x.get("id"): x for x in probes}
    strict = rows.get("python_default")
    loose = rows.get("python_d1e-5")
    if strict is None or loose is None:
        raise ValueError("Missing actual Python baseline or 1e-5 probe")
    # An early P0 experiment wrote status=null because of a recorder defect.
    # We accept its recorded exit_code, solver stage, log count and verdict;
    # record the untrusted status separately instead of inventing a new one.
    for row in (strict, loose):
        if (row.get("exit_code") != 0 or row.get("solver_invoked") is not True
                or row.get("verdict") not in (
                    "equivalent", "equivalent*", "not_equivalent")):
            raise ValueError("Invalid science provenance or solver observation")
    if strict.get("effective_distance_tolerance") != 1e-8:
        raise ValueError("Not the published modern default threshold")
    if loose.get("effective_distance_tolerance") != 1e-5:
        raise ValueError("Not the declared configured reproduction threshold")
    if strict.get("wmc_expected_log2") is None or strict.get("wmc_log_wmc") is None:
        raise ValueError("Missing GPMC log count needed to replay v0.9.1")
    prior = replay_classifier(strict["wmc_log_wmc"], strict["wmc_expected_log2"])
    return {
        "schema": "quprs-tacas26-artifact-classifier-replay-v1",
        "artifact": {"repository": ARTIFACT_REPO, "git_sha": ARTIFACT_SHA,
                     "quprs_tag": QU_PRS_TAG, "quprs_git_sha": QU_PRS_SHA,
                     "paper_strategy": ARTIFACT_STRATEGY,
                     "timeout_seconds": ARTIFACT_TIMEOUT_SECONDS,
                     "solver_mode": "gpmc -mode=1",
                     "effective_legacy_tolerance": LEGACY_TOLERANCE},
        "science_origin_sha": report.get("sha"),
        "source_qasm_sha256": {key:identities[key] for key in QPE20_SOURCE_SHA256},
        "paper_expected_verdict": PAPER_EXPECTED_VERDICT,
        "replayed_legacy_magnitude": prior,
        "modern_default": {"verdict": strict["verdict"],
                           "distance_tolerance": 1e-8,
                           "raw_runner_status": strict.get("status"),
                           "wmc_precision_reason": strict.get("wmc_precision_reason")},
        "modern_explicit_paper_comparison": {
            "verdict": loose["verdict"],
            "distance_tolerance": 1e-5,
            "raw_runner_status": loose.get("status"),
            "wmc_precision_reason": loose.get("wmc_precision_reason"),
        },
        "paper_phase_verdict_reproduced_from_archived_solver": False,
        "archived_solver_reexecuted": False,
        "modern_source_operator_equivalence_certified": False,
        "current_default_unchanged": True,
        "performance_measured": False,
        "qualification": "LEGACY_MAGNITUDE_REPLAY_ONLY",
        "warning": ("Historical formula explains the old near-unit magnitude "
                    "label, but does not by itself establish equivalent* phase "
                    "from the archived GPMC or a rigorous modern distance."),
    }

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--observations", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    report = replay_qpe20_observation(
        json.loads(a.observations.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "legacy_magnitude_accepted": report["replayed_legacy_magnitude"]["magnitude_accepted"],
        "paper_expected": report["paper_expected_verdict"],
        "modern_default": report["modern_default"]["verdict"],
        "modern_configured": report["modern_explicit_paper_comparison"]["verdict"],
        "qualification": report["qualification"],
    }, sort_keys=True))

if __name__ == "__main__":
    main()

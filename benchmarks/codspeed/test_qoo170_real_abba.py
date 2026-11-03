"""Opt-in REAL QuPRS/GPMC paired ABBA / BAAB with official CodSpeed WallTime.

Two QASM261 QAOA7 negative cases, Rust Hybrid and Rust WMC-only.
Every position calls the pinned verifier+GPMC only once inside CodSpeed
pedantic(rounds=1, iterations=1, warmup_rounds=0); the plugin's extra
non-timed return call must reuse the already validated observation.
No custom clocks, no invented walltime, no changes to routine 10 paired IDs.
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
from pathlib import Path

import pytest

FILENAME = "qaoa_nativegates_ibm_qiskit_opt0_7.qasm"
PREFIX = "QUPRS_WALLTIME_RESULT "
METHODS = ("hybrid", "wmc_only")
SEQUENCES = (
    ("ABBA", ("A1", "B1", "B2", "A2")),
    ("BAAB", ("B1", "A1", "A2", "B2")),
    ("BAAB", ("B1", "A1", "A2", "B2")),
    ("ABBA", ("A1", "B1", "B2", "A2")),
)
PARAMS = [
    pytest.param(method, block, sequence, position,
                 id=f"{method}-block{block}-{position}")
    for method in METHODS
    for block, (sequence, positions) in enumerate(SEQUENCES)
    for position in positions
]


def input_hashes() -> dict:
    root = Path(os.environ["GITHUB_WORKSPACE"]) / "abba-pr-head" / "benchmarks" / "MQTBench"
    return {
        "source_sha256": hashlib.sha256((root / FILENAME).read_bytes()).hexdigest(),
        "target_sha256": hashlib.sha256((
            root / "qiskit-2.6.1-opt0" / "Random_Rotation" / FILENAME
        ).read_bytes()).hexdigest(),
    }


def real_solver(revision: str, method: str) -> dict:
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    root = workspace / ("abba-dev-base" if revision == "base" else "abba-pr-head")
    interpreter = Path(os.environ["RUNNER_TEMP"]) / f"quprs-pr-walltime-{revision}/bin/python"
    harness = workspace / "abba-pr-head/benchmarks/codspeed/solver_case.py"
    command = [
        str(interpreter), str(harness), str(workspace / "abba-pr-head"),
        FILENAME, "proportional", "gpmc", "rust", "0",
        "random_rotation", method, "qiskit-2.6.1-opt0",
    ]
    env = dict(os.environ)
    env.update({
        "QUPRS_DIAGNOSTIC_RR_TOLERANCE": "1e-10",
        "QUPRS_DIAGNOSTIC_DISTANCE_TOLERANCE": "1e-8",
        "QUPRS_DIAGNOSTIC_PHASE_TOLERANCE": "1e-8",
        "QUPRS_DIAGNOSTIC_GPMC_DIGITS": "90",
    })
    process = subprocess.Popen(
        command, env=env, cwd=root, text=True, start_new_session=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = process.communicate(timeout=110)
    except subprocess.TimeoutExpired as e:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise AssertionError(f"real Solver timeout {revision}/{method}") from e
    if process.returncode:
        raise AssertionError(
            f"real Solver exit {process.returncode} {revision}/{method}: "
            f"{stdout[-1400:]} {stderr[-1400:]}"
        )
    markers = [line[len(PREFIX):] for line in stdout.splitlines()
               if line.startswith(PREFIX)]
    if len(markers) != 1:
        raise AssertionError(f"missing or duplicate real Solver marker: {stdout[-900:]}")
    observation = json.loads(markers[0])
    for key, expected in (
        ("verdict", "not_equivalent"),
        ("solver_invoked", True),
        ("method", method),
        ("solver", "gpmc"),
        ("pair_variant", "random_rotation"),
        ("qasm_corpus", "qiskit-2.6.1-opt0"),
        ("effective_rr_tolerance", 1e-10),
        ("effective_distance_tolerance", 1e-8),
        ("effective_phase_tolerance", 1e-8),
        ("effective_gpmc_digits", 90),
    ):
        if observation.get(key) != expected:
            raise AssertionError(
                f"wrong real Solver {revision}/{method}/{key}: "
                f"{observation.get(key)!r}, expected {expected!r}"
            )
    if observation.get("precision_contract") not in (
        "legacy_90_digit_distance_source_checked", "public_per_call_pinned",
    ):
        raise AssertionError("unverified GPMC precision source path")
    return observation


@pytest.fixture(scope="session")
def prewarmed_verifiers():
    # Explicit equally treated unmeasured prewarm, distinct from each position.
    evidence = []
    for method in METHODS:
        for revision in ("base", "head"):
            result = real_solver(revision, method)
            evidence.append({
                "kind": "prewarm", "method": method, "revision": revision,
                "verdict": result["verdict"],
                "precision_contract": result["precision_contract"],
            })
    dest = Path(os.environ["RUNNER_TEMP"]) / "qoo170-abba-real-prewarm.json"
    dest.write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


@pytest.mark.parametrize("method,block,sequence,position", PARAMS)
def test_qoo170_real_single_position(benchmark, prewarmed_verifiers,
                                    method, block, sequence, position):
    revision = "base" if position.startswith("A") else "head"
    cache: list[dict] = []
    counts = {"target_calls": 0, "real_solver_calls": 0}

    def once_then_cached():
        counts["target_calls"] += 1
        if cache:
            return cache[0]
        result = real_solver(revision, method)
        counts["real_solver_calls"] += 1
        cache.append(result)
        return result

    result = benchmark.pedantic(
        once_then_cached, rounds=1, iterations=1, warmup_rounds=0,
    )
    if counts != {"target_calls": 2, "real_solver_calls": 1}:
        raise AssertionError(f"CodSpeed extra target call contract changed: {counts}")
    if result is not cache[0] or not result["solver_invoked"]:
        raise AssertionError("real Solver result cache or provenance mismatch")

    hashes = input_hashes()
    benchmark.extra_info.update({
        "case": "qaoa7_negative_" + method,
        "method": method, "block": block, "sequence": sequence,
        "position": position, "revision": revision,
        "revision_sha": os.environ["BASE_SHA" if revision == "base" else "HEAD_SHA"],
        "source_sha256": hashes["source_sha256"],
        "target_sha256": hashes["target_sha256"],
        "solver": "gpmc", "backend": "rust",
        "real_solver_calls": 1, "target_calls": 2,
        "verdict": result["verdict"], "solver_invoked": True,
        "requested_gpmc_digits": 90,
    })
    evidence = {
        **hashes, "case": "qaoa7_negative_" + method,
        "method": method, "block": block, "sequence": sequence,
        "position": position, "revision": revision,
        "revision_sha": os.environ["BASE_SHA" if revision == "base" else "HEAD_SHA"],
        "fixture_sha": os.environ["HEAD_SHA"],
        "target_calls": 2, "real_solver_calls": 1,
        "observation": result,
    }
    out = Path(os.environ["RUNNER_TEMP"]) / "qoo170-real-abba-science.jsonl"
    with out.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(evidence, sort_keys=True) + "\n")

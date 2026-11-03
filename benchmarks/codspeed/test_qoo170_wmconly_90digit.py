"""Isolated QOO-170 admission experiment, NEVER included in routine CodSpeed.

Measure an actual Rust WMC-only/GPMC subprocess at the same 90 printed digits
used by the existing paired-QASM261 WallTime contract. Only one pinned QAOA7
negative workload is measured. The test is intentionally not part of dev.
"""
import hashlib
import json
import os
import signal
import subprocess
from pathlib import Path

import pytest

RESULT_PREFIX = "QUPRS_WALLTIME_RESULT "
FILENAME = "qaoa_nativegates_ibm_qiskit_opt0_7.qasm"


def one_pinned_wmc_request():
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    verifier = workspace / "qoo170-pinned-dev"
    python = Path(os.environ["QOO170_VENV"]) / "bin/python"
    harness = verifier / "benchmarks/codspeed/solver_case.py"
    expected_sha = os.environ["QOO170_VERIFIER_SHA"]
    if not harness.is_file() or not python.is_file() or len(expected_sha) != 40:
        raise RuntimeError("Pinned dev verifier or independently built venv missing")
    command = [
        str(python), str(harness), str(verifier),
        FILENAME, "proportional", "gpmc", "rust", "0",
        "random_rotation", "wmc_only", "qiskit-2.6.1-opt0",
    ]
    env = os.environ.copy()
    env.update({
        "QUPRS_DIAGNOSTIC_RR_TOLERANCE": "1e-10",
        "QUPRS_DIAGNOSTIC_DISTANCE_TOLERANCE": "1e-8",
        "QUPRS_DIAGNOSTIC_PHASE_TOLERANCE": "1e-8",
        "QUPRS_DIAGNOSTIC_GPMC_DIGITS": "90",
    })
    process = subprocess.Popen(
        command, cwd=verifier, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=110)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise AssertionError("90-digit GPMC WMC-only timed out")
    if process.returncode:
        raise AssertionError(
            f"90-digit WMC subprocess exit={process.returncode}: "
            f"{stdout[-1500:]} {stderr[-1500:]}"
        )
    markers = [
        row[len(RESULT_PREFIX):]
        for row in stdout.splitlines() if row.startswith(RESULT_PREFIX)
    ]
    if len(markers) != 1:
        raise AssertionError("missing or duplicated verifier source marker")
    out = json.loads(markers[0])
    # These checks execute inside every warmup/measurement invocation; no
    # timed round is silently accepted merely because pytest later passes.
    expected = {
        "method": "wmc_only",
        "solver": "gpmc",
        "pair_variant": "random_rotation",
        "qasm_corpus": "qiskit-2.6.1-opt0",
        "effective_rr_tolerance": 1e-10,
        "effective_distance_tolerance": 1e-8,
        "effective_phase_tolerance": 1e-8,
        "effective_gpmc_digits": 90,
    }
    for key, value in expected.items():
        if out.get(key) != value:
            raise AssertionError(f"{key} expected {value!r}, observed {out.get(key)!r}")
    if out.get("solver_invoked") is not True or out.get("verdict") != "not_equivalent":
        raise AssertionError(f"Scientifically unexpected WMC-only observation: {out}")
    return out


def test_qoo170_qaoa7_negative_rust_wmconly_gpmc90(benchmark):
    observation = benchmark(one_pinned_wmc_request)
    verifier = Path(os.environ["GITHUB_WORKSPACE"]) / "qoo170-pinned-dev"
    base = verifier / "benchmarks/MQTBench"
    source_sha = hashlib.sha256((base / FILENAME).read_bytes()).hexdigest()
    negative_sha = hashlib.sha256((
        base / "qiskit-2.6.1-opt0/Random_Rotation" / FILENAME
    ).read_bytes()).hexdigest()
    benchmark.extra_info.update({
        "instrument_scope": "full_solver_inclusive_walltime",
        "case_id": "q261_qaoa7_negative_wmconly_gpmc90_rust",
        "method": "wmc_only", "backend": "rust", "solver": "gpmc",
        "source_sha256": source_sha, "target_sha256": negative_sha,
        "verifier_sha": os.environ["QOO170_VERIFIER_SHA"],
        "requested_gpmc_digits": 90,
        "real_solver_invoked": True, "observed_verdict": observation["verdict"],
        "scientific_scope": "independent complex128 source witness; no certified GPMC numerical bound",
    })
    destination = Path(os.environ["RUNNER_TEMP"]) / "qoo170-wmconly90-science.json"
    destination.write_text(json.dumps({
        "case_id": "q261_qaoa7_negative_wmconly_gpmc90_rust",
        "verifier_sha": os.environ["QOO170_VERIFIER_SHA"],
        "source_sha256": source_sha, "target_sha256": negative_sha,
        "observation": observation,
        "limitations": [
            "Numerical source truth is complex128, not a rigorous GPMC error bound",
            "One final observation logged; each warmup/timed invocation asserts status",
            "Non-Macro Runner and shared-host drift may affect CodSpeed WallTime"
        ],
    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")

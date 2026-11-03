"""Every-PR, source-pinned, same-host CodSpeed WallTime coverage.

Base and HEAD have separate built Python/Rust installations but read the
exact same QASM files from HEAD. The timed unit is a complete verification
request, including the Solver subprocess when the Hybrid stage reaches WMC.
"""
import hashlib
import json
import os
import signal
import subprocess
from pathlib import Path

import pytest


# Match the existing representative MQT case settings (method=Hybrid,
# backend, Solver, strategy, direction). IDs are stable across PR runs.
from benchmarks.codspeed.case_registry import (
    ALL_WALLTIME_CASES as CASES, QASM261_WALLTIME_CASE_IDS,
)

RESULT_PREFIX = "QUPRS_WALLTIME_RESULT "
VALID_VERDICTS = {"equivalent", "equivalent*", "not_equivalent"}


def execute_source_pinned_case(revision: str, case: tuple) -> dict:
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    runner_temp = Path(os.environ["RUNNER_TEMP"])
    source_root = workspace / "pr-walltime-base" if revision == "base" else workspace
    interpreter = runner_temp / f"quprs-pr-walltime-{revision}" / "bin" / "python"
    harness = workspace / "benchmarks" / "codspeed" / "solver_case.py"
    _, filename, strategy, solver, reverse, backend = case
    command = [
        str(interpreter), str(harness), str(workspace),
        filename, strategy, solver, backend, "1" if reverse else "0",
    ]
    case_env = os.environ.copy()
    if case[0] in QASM261_WALLTIME_CASE_IDS:
        command.extend(("random_rotation", "hybrid", "qiskit-2.6.1-opt0"))
        # Explicitly pin numerical semantics in BOTH verifier revisions.
        # Do not merely label historical defaults as effective tolerances.
        case_env.update({
            "QUPRS_DIAGNOSTIC_RR_TOLERANCE": "1e-10",
            "QUPRS_DIAGNOSTIC_DISTANCE_TOLERANCE": "1e-8",
            "QUPRS_DIAGNOSTIC_PHASE_TOLERANCE": "1e-8",
            "QUPRS_DIAGNOSTIC_GPMC_DIGITS": "30",
        })
    process = subprocess.Popen(
        command,
        env=case_env,
        cwd=source_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=110)
    except subprocess.TimeoutExpired as exc:
        # Kill the Python verifier AND Solver descendants to avoid residual
        # processes contaminating subsequent performance observations.
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise RuntimeError(f"timed out: {revision}/{case[0]}") from exc

    if process.returncode:
        raise RuntimeError(
            f"failed: {revision}/{case[0]}, exit={process.returncode}\n"
            f"stdout={stdout[-3000:]}\nstderr={stderr[-3000:]}"
        )
    markers = [
        line[len(RESULT_PREFIX):]
        for line in stdout.splitlines() if line.startswith(RESULT_PREFIX)
    ]
    if len(markers) != 1:
        raise RuntimeError(
            f"missing or duplicated source-verdict marker: "
            f"{revision}/{case[0]} stdout={stdout[-3000:]}"
        )
    return json.loads(markers[0])


# Interleave base and head for each case to reduce runner drift.
PARAMS = [
    pytest.param(revision, case, id=f"{case[0]}-{revision}")
    for case in CASES
    for revision in ("base", "head")
]


@pytest.mark.parametrize("revision,case", PARAMS)
def test_pr_solver_inclusive_walltime(benchmark, revision, case):
    measured = benchmark(execute_source_pinned_case, revision, case)
    case_id, filename, strategy, solver, reverse, backend = case
    versioned_negative = case_id in QASM261_WALLTIME_CASE_IDS
    fixture_hashes = None
    if versioned_negative:
        folder = Path(os.environ["GITHUB_WORKSPACE"]) / "benchmarks" / "MQTBench"
        fixture_hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in (
            folder / filename,
            folder / "qiskit-2.6.1-opt0" / "Random_Rotation" / filename,
        )]
    benchmark.extra_info.update({
        "measurement": "solver_inclusive_end_to_end_walltime",
        "case": case_id,
        "revision": revision,
        "revision_sha": os.environ["BASE_SHA" if revision == "base" else "HEAD_SHA"],
        "fixture_revision_sha": os.environ["HEAD_SHA"],
        "method": "hybrid",
        "strategy": strategy,
        "reverse_inputs": str(reverse),
        "backend": backend,
        "solver": solver,
        "solver_invoked": str(measured["solver_invoked"]),
        "verdict": measured["verdict"],
        "fixture_sha256": fixture_hashes,
        "pair_variant": "random_rotation" if versioned_negative else "transpiled",
        "qasm_corpus": "qiskit-2.6.1-opt0" if versioned_negative else "historical",
        "verification_status": (
            "EXPECTED_SOURCE_NEGATIVE" if versioned_negative and measured["verdict"] == "not_equivalent"
            else "EXTERNAL_GANAK_PRINT_LIMITATION"
            if measured["verdict"] == "not_equivalent" and solver == "ganak"
            else "PASS" if measured["verdict"] in {"equivalent", "equivalent*"}
            else "INVALID_RESULT"
        ),
        "rr_approximate": str(measured["rr_approximate"]),
        "wmc_printed_verdict": str(measured.get("wmc_printed_verdict")),
        "wmc_precision_reason": str(measured.get("wmc_precision_reason")),
        "wmc_print_resolution_distance": str(measured.get("wmc_print_resolution_distance")),
        "approximate_distance_tolerance": str(measured.get("approximate_distance_tolerance")),
        "evidence": "same_host_shared_github_runner_exploratory",
    })
    # Do not silently count an RR-only transition as a comparable Solver sample.
    assert measured["solver_invoked"] is True, (
        f"not solver-inclusive: {revision}/{case_id}"
    )
    # Inconclusive/resource/external Solver failures are not timing successes.
    assert measured["verdict"] in VALID_VERDICTS, (
        f"not a determinate benchmark result: {revision}/{case_id}: {measured}"
    )
    # The historical VQE4/Grover4 Ganak printed-resolution problem may yield
    # a negative numerical point estimate for a near-equivalent pair. Retain
    # that timing with explicit provenance; it is NOT a correctness PASS.
    if versioned_negative:
        assert measured["verdict"] == "not_equivalent" and measured["pair_variant"] == "random_rotation", (
            f"QASM261 Random_Rotation must give genuine NEQ: {case_id}: {measured}"
        )
    if measured["verdict"] == "not_equivalent" and not versioned_negative:
        assert solver == "ganak" and case_id in {"vqe4_ganak", "grover4_ganak", "vqe4_ganak_python"}, (
            f"unexpected not-equivalent verdict: {revision}/{case_id}"
        )

    # Provenance is recorded AFTER CodSpeed measurement and verdict validation;
    # the benchmarked execution performs no extra logging/timing.
    provenance = {
        "case": case_id,
        "revision": revision,
        "sha": os.environ["BASE_SHA" if revision == "base" else "HEAD_SHA"],
        "fixture_sha": os.environ["HEAD_SHA"],
        "method": "hybrid",
        "backend": backend,
        "solver": solver,
        "strategy": strategy,
        "reverse": reverse,
        "solver_invoked": bool(measured["solver_invoked"]),
        "verdict": measured["verdict"],
        "rr_approximate": measured["rr_approximate"],
        "wmc_printed_verdict": measured.get("wmc_printed_verdict"),
        "wmc_precision_reason": measured.get("wmc_precision_reason"),
        "wmc_print_resolution_distance": measured.get("wmc_print_resolution_distance"),
        "approximate_distance_tolerance": measured.get("approximate_distance_tolerance"),
        "wmc_numerical_verdict": measured.get("wmc_numerical_verdict"),
        "verification_status": benchmark.extra_info["verification_status"],
        "pair_variant": benchmark.extra_info["pair_variant"],
        "qasm_corpus": benchmark.extra_info["qasm_corpus"],
        "fixture_sha256": fixture_hashes,
        "effective_rr_tolerance": measured.get("effective_rr_tolerance"),
        "effective_distance_tolerance": measured.get("effective_distance_tolerance"),
        "effective_phase_tolerance": measured.get("effective_phase_tolerance"),
        "effective_gpmc_digits": measured.get("effective_gpmc_digits"),
    }
    output = Path(os.environ["RUNNER_TEMP"]) / "quprs-paired-walltime-provenance.jsonl"
    with output.open("a", encoding="utf-8") as log:
        log.write(json.dumps(provenance, sort_keys=True) + "\n")

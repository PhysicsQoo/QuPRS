"""Source-paired cross-method CodSpeed benchmark.

Same QASM bytes and same GitHub runner for separately built base/HEAD.
The verdict is measured, not forced; request latency and scientific
equivalence correctness are separate axes.
"""
import hashlib
import json
import os
import signal
import subprocess
from pathlib import Path
import pytest

CIRCUITS = (
    ("vqe4", "vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", False),
    ("grover4", "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", True),
    ("qaoa7", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", False),
    ("qft16", "qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", True),
    ("graphstate16", "graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "naive", False),
    ("ghz32", "ghz_nativegates_ibm_qiskit_opt0_32.qasm", "straightforward", True),
)
CASES = tuple(
    (f"{name}_{solver}_{backend}", filename, strategy, reverse, solver, backend)
    for name, filename, strategy, reverse in CIRCUITS
    for solver in ("gpmc", "ganak") for backend in ("rust", "python")
)
CPU_CASES = tuple(c for c in CASES if c[0] in {
    "vqe4_gpmc_rust", "vqe4_ganak_rust",
    "qaoa7_gpmc_rust", "qaoa7_ganak_rust",
})
VALID_VERDICTS = {"equivalent", "equivalent*", "not_equivalent", "unknown"}


def execute(revision, case, instrument):
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    source = workspace / "cross-method-base" if revision == "base" else workspace
    executable = Path(os.environ["RUNNER_TEMP"]) / f"cross-method-{revision}/bin/python"
    harness = workspace / "benchmarks/codspeed/solver_case.py"
    _, filename, strategy, reverse, solver, backend = case
    command = [str(executable), str(harness), str(workspace),
               filename, strategy, solver, backend, str(int(reverse))]
    child_env = os.environ.copy()
    if instrument == "simulation":
        child_env["QUPRS_CROSS_METHOD_SOLVER_TIMEOUT"] = "300"
    child = subprocess.Popen(
        command, cwd=source, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, start_new_session=True,
        env=child_env,
    )
    try:
        stdout, stderr = child.communicate(timeout=390 if instrument == "simulation" else 180)
    except subprocess.TimeoutExpired as exc:
        os.killpg(child.pid, signal.SIGKILL)
        child.communicate()
        raise RuntimeError(f"timeout: {revision}/{case[0]}") from exc
    if child.returncode:
        raise RuntimeError(f"{revision}/{case[0]} exit={child.returncode}: "
                           f"{stderr[-1200:]} {stdout[-1200:]}")
    prefix = "QUPRS_WALLTIME_RESULT "
    observed = [json.loads(line[len(prefix):])
                for line in stdout.splitlines() if line.startswith(prefix)]
    if len(observed) != 1 or observed[0]["verdict"] not in VALID_VERDICTS:
        raise RuntimeError(f"invalid result: {revision}/{case[0]} {observed}")
    return observed[0]


def fixture_hashes(case):
    root = Path(os.environ["GITHUB_WORKSPACE"]) / "benchmarks/MQTBench"
    paths = [root / case[1], root / "h,ry,rz,cx" / case[1]]
    return [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]


def measure(benchmark, instrument, revision, case):
    hashes = fixture_hashes(case)
    result = benchmark(execute, revision, case, instrument)
    case_id, filename, strategy, reverse, solver, backend = case
    row = {
        "instrument": instrument, "case": case_id, "revision": revision,
        "sha": os.environ["BASE_SHA" if revision == "base" else "HEAD_SHA"],
        "fixture_sha": os.environ["HEAD_SHA"],
        "qasm_sha256": hashes, "method": "hybrid", "strategy": strategy,
        "solver_timeout_secs": 300 if instrument == "simulation" else 90,
        "reverse": reverse, "backend": backend, "solver": solver,
        "verdict": result["verdict"], "solver_invoked": bool(result["solver_invoked"]),
        "rr_approximate": result.get("rr_approximate"),
        "wmc_printed_verdict": result.get("wmc_printed_verdict"),
        "wmc_precision_reason": result.get("wmc_precision_reason"),
        "wmc_print_resolution_distance": result.get("wmc_print_resolution_distance"),
        "approximate_distance_tolerance": result.get("approximate_distance_tolerance"),
        "measurement_scope": ("whole_request_walltime" if instrument == "walltime"
                              else "subprocess_tracked_simulated_cpu"),
    }
    benchmark.extra_info.update(row)
    output = Path(os.environ["RUNNER_TEMP"]) / f"cross-method-{instrument}.jsonl"
    with output.open("a", encoding="utf-8") as log:
        log.write(json.dumps(row, sort_keys=True) + "\n")


WALL_PARAMS = [
    pytest.param(revision, case, id=f"{case[0]}-{revision}")
    for case in CASES for revision in ("base", "head")
]
CPU_PARAMS = [
    pytest.param(revision, case, id=f"{case[0]}-{revision}")
    for case in CPU_CASES for revision in ("base", "head")
]


@pytest.mark.parametrize("revision,case", WALL_PARAMS)
def test_cross_method_walltime(benchmark, revision, case):
    measure(benchmark, "walltime", revision, case)


@pytest.mark.parametrize("revision,case", CPU_PARAMS)
def test_cross_method_cpu(benchmark, revision, case):
    measure(benchmark, "simulation", revision, case)

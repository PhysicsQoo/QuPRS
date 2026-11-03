"""Bounded, opt-in CodSpeed screening — never promoted automatically to PR gates.

Runs fixed source QASM through a single verifier subprocess; the *only* timing
instrument is CodSpeed WallTime. Timeout/watchdog are safety controls, not a
substitute for its statistics. Both successes and timeouts remain evidence.
"""
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from benchmarks.codspeed.case_registry import PILOT_CASES

MARKER = "QUPRS_WALLTIME_RESULT "


def sample_candidate(case):
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    harness = workspace / "benchmarks" / "codspeed" / "solver_case.py"
    env = os.environ.copy()
    env["QUPRS_CROSS_METHOD_SOLVER_TIMEOUT"] = str(case.solver_timeout_s)
    command = [
        sys.executable, str(harness), str(workspace), case.qasm,
        case.strategy, case.solver, case.backend, "1" if case.reverse else "0",
        case.pair_variant,
    ]
    if case.qasm_corpus != "historical":
        command.extend([case.method, case.qasm_corpus])
    child = subprocess.Popen(
        command, cwd=workspace, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    try:
        stdout, stderr = child.communicate(timeout=case.watchdog_s)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.communicate()
        return {"status": "WATCHDOG_TIMEOUT", "verdict": None,
                "solver_invoked": None, "exit_code": None}
    if child.returncode:
        # A request-level solver timeout is different from the outer watchdog.
        # Preserve the diagnostic text without mislabeling arbitrary exceptions.
        diagnostic = (stderr + "\n" + stdout)[-1400:]
        solver_timeout = ("timeout" in diagnostic.lower()
                          or "time limit exceeded" in diagnostic.lower())
        return {"status": "SOLVER_TIMEOUT" if solver_timeout else "PROCESS_ERROR",
                "verdict": None, "solver_invoked": None,
                "exit_code": child.returncode,
                "stderr_tail": diagnostic[-600:]}
    matches = [line[len(MARKER):] for line in stdout.splitlines()
               if line.startswith(MARKER)]
    if len(matches) != 1:
        return {"status": "MISSING_RESULT", "verdict": None,
                "solver_invoked": None, "exit_code": child.returncode}
    try:
        result = json.loads(matches[0])
    except json.JSONDecodeError:
        return {"status": "UNPARSEABLE_RESULT", "verdict": None,
                "solver_invoked": None, "exit_code": child.returncode}
    result["status"] = "COMPLETED"
    result["exit_code"] = child.returncode
    return result


def run_source_pinned_candidate(benchmark, case):
    fixture_root = Path(os.environ["GITHUB_WORKSPACE"]) / "benchmarks" / "MQTBench"
    counterpart = ("Random_Rotation" if case.pair_variant == "random_rotation"
                   else "h,ry,rz,cx")
    target_root = (fixture_root if case.qasm_corpus == "historical"
                   else fixture_root / case.qasm_corpus)
    sources = (fixture_root / case.qasm,
               target_root / counterpart / case.qasm)
    source_hashes = [hashlib.sha256(source.read_bytes()).hexdigest()
                     for source in sources]
    result = benchmark(sample_candidate, case)
    # A fast solver-avoiding RR result can still be useful as a separate
    # category. It cannot enter a Solver-inclusive benchmark by assumption.
    passed = (result["status"] == "COMPLETED"
              and (result.get("verdict") in {"equivalent", "equivalent*"}
                   if case.expected_verdict == "equivalent_or_phase"
                   else result.get("verdict") == case.expected_verdict))
    if case.expected_solver_invoked is not None:
        # Never promote an RR-terminated request as Solver-inclusive.
        # Timeouts and missing observations remain censored, not stage PASS.
        passed = (passed and result.get("solver_invoked") is case.expected_solver_invoked)
    status = ("ELIGIBLE_FOR_INDEPENDENT_ORACLE_REVIEW" if passed else
              "NEEDS_SCIENTIFIC_OR_TIMEOUT_REVIEW")
    metadata = {
        "case_id": case.id, "filename": case.qasm,
        "pair_variant": case.pair_variant,
        "qasm_corpus": case.qasm_corpus,
        "expected_verdict": case.expected_verdict,
        "expected_solver_invoked": case.expected_solver_invoked,
        "qasm_sha256": source_hashes,
        "codspeed_sample_policy": "one_measured_round_no_warmup_exploratory",
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "source_sha": os.environ["HEAD_SHA"], "method": case.method,
        "strategy": case.strategy, "backend": case.backend,
        "solver": case.solver, "reverse": case.reverse,
        "solver_timeout_s": case.solver_timeout_s,
        "watchdog_s": case.watchdog_s, "observed": result,
        "pilot_qualification": status,
        "scope": "bounded exploratory source-pinned CodSpeed WallTime",
    }
    benchmark.extra_info.update(metadata)
    path = Path(os.environ["RUNNER_TEMP"]) / "candidate-pilot-science.jsonl"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(metadata, sort_keys=True) + "\n")
    # Expected timeouts are *censored* observations. Do not transform them
    # into successful performance comparisons or arbitrary fixed durations.
    assert result["status"] in {
        "WATCHDOG_TIMEOUT", "SOLVER_TIMEOUT", "PROCESS_ERROR", "MISSING_RESULT",
        "UNPARSEABLE_RESULT", "COMPLETED",
    }



@pytest.mark.parametrize("case", PILOT_CASES, ids=[case.id for case in PILOT_CASES])
def test_source_pinned_candidate(benchmark, case):
    return run_source_pinned_candidate(benchmark, case)

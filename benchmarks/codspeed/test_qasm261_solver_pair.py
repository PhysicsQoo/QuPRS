"""Versioned QASM261 GPMC full-request paired CodSpeed WallTime.

A1(dev)-B1(PR)-B2(PR)-A2(dev) on a single hosted runner. Each cell
measured by CodSpeed WallTime (five requested rounds). Same source/target
QASM bytes from this experiment checkout for ALL four positions. No
custom stopwatch, no inherited historical benchmark ID.
"""
import hashlib
import json
import os
import signal
import subprocess
from pathlib import Path
import pytest

from benchmarks.codspeed.qasm261_paired_cases import GPMC_PAIRS, POSITIONS

PREFIX = "QUPRS_WALLTIME_RESULT "
PARAMS = [
    pytest.param(case, position, revision, id=f"{case[0]}-{position}")
    for case in GPMC_PAIRS
    for position, revision in POSITIONS
]

def invoke(revision, case):
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    root = workspace / "qasm261-dev-base" if revision == "base" else workspace / "qasm261-pr-head"
    exe = Path(os.environ["RUNNER_TEMP"]) / f"qasm261-{revision}" / "bin/python"
    harness = workspace / "benchmarks/codspeed/solver_case.py"
    _, filename, strategy, reverse, variant, _ = case
    command = [
        str(exe), str(harness), str(workspace), filename,
        strategy, "gpmc", "rust", "1" if reverse else "0",
        variant, "hybrid", "qiskit-2.6.1-opt0",
    ]
    child = subprocess.Popen(
        command, cwd=root, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    try:
        stdout, stderr = child.communicate(timeout=110)
    except subprocess.TimeoutExpired as e:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.communicate()
        raise RuntimeError(f"{case[0]}/{revision}: external watchdog; censored") from e
    if child.returncode:
        raise RuntimeError(
            f"{case[0]}/{revision} exit={child.returncode}; "
            f"stderr={stderr[-2000:]}; stdout={stdout[-2000:]}"
        )
    markers = [line[len(PREFIX):] for line in stdout.splitlines()
               if line.startswith(PREFIX)]
    if len(markers) != 1:
        raise RuntimeError(f"{case[0]}/{revision}: expected one result marker, found {len(markers)}")
    return json.loads(markers[0])


@pytest.mark.parametrize("case,position,revision", PARAMS)
def test_qasm261_solver_pair(benchmark, case, position, revision):
    observations = []
    def sample():
        result = invoke(revision, case)
        observations.append({
            "verdict": result["verdict"],
            "solver_invoked": result["solver_invoked"],
            "pair_variant": result["pair_variant"],
            "method": result["method"],
            "qasm_corpus": result["qasm_corpus"],
            "rr_approximate": result["rr_approximate"],
            "wmc_precision_reason": result["wmc_precision_reason"],
            "distance": result["effective_distance_tolerance"],
            "rr_tolerance": result["effective_rr_tolerance"],
            "phase_tolerance": result["effective_phase_tolerance"],
            "gpmc_digits": result["effective_gpmc_digits"],
        })
        return result

    benchmark(sample)
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    _, filename, strategy, reverse, variant, expected = case
    source = workspace / "benchmarks/MQTBench" / filename
    counterpart = ("Random_Rotation" if variant == "random_rotation"
                   else "h,ry,rz,cx")
    target = workspace / "benchmarks/MQTBench/qiskit-2.6.1-opt0" / counterpart / filename
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest()
              for path in (source, target)]
    record = {
        "case": case[0], "position": position, "revision": revision,
        "sha": os.environ["BASE_SHA" if revision == "base" else "HEAD_SHA"],
        "fixture_sha": os.environ["FIXTURE_SHA"],
        "fixture_paths": [str(source.relative_to(workspace)),
                          str(target.relative_to(workspace))],
        "fixture_sha256": hashes,
        "solver": "gpmc", "backend": "rust", "method": "hybrid",
        "strategy": strategy, "reverse": reverse, "variant": variant,
        "expected_binary": expected,
        "observations": observations, "observed_invocations": len(observations),
        "source_scope": "Qiskit261 Level0, no runtime QASM regeneration",
        "instrument": "CodSpeed WallTime",
    }
    benchmark.extra_info.update({
        "case": case[0], "position": position, "revision": revision,
        "verdict": observations[-1]["verdict"],
        "solver_invoked": observations[-1]["solver_invoked"],
        "qasm_sha256": hashes, "fixture_sha": os.environ["FIXTURE_SHA"],
        "source_sha": record["sha"], "instrument": "solver-inclusive-end-to-end",
    })
    with (Path(os.environ["RUNNER_TEMP"]) / "qasm261-paired-provenance.jsonl").open(
        "a", encoding="utf-8"
    ) as out:
        out.write(json.dumps(record, sort_keys=True) + "\n")
    assert observations, "CodSpeed measured no invocations"

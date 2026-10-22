#!/usr/bin/env python3
"""Observe whether unchanged Hybrid verification needs WMC after reduction.

Run under strace outside CodSpeed\'s measured benchmark. Reduction-only is a\nvalid successful result; solver invocation is observed, never required.\n"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test"))

CASES = {
    "qft16": "qft_nativegates_ibm_qiskit_opt0_16.qasm",
    "graphstate16": "graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
}


def positive_verdict(value: object) -> bool:
    return str(value) in ("equivalent", "equivalent*")


def numeric_tool_time(value: object) -> bool:
    return (isinstance(value, (float, int)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)


def native_solver_work_execve(trace_text: str, binary: str, solver: str) -> bool:
    """Match a successful *model-counting* launch, not a --version probe.

    Both selected native solvers are invoked with their existing Mode 1 / Mode 6
    CNF-solving command line. A bare executable execve is insufficient evidence.
    """
    solver_mode = {"gpmc": "-mode=1", "ganak": "--mode=6"}[solver]
    return any(
        'execve("' + binary + '"' in line
        and '"' + solver_mode + '"' in line
        and line.rstrip().endswith("= 0")
        for line in trace_text.splitlines()
    )


def classify_hybrid_execution(
    verdict: object, tool_time: object, trace_text: str, binary: str, solver: str
) -> dict:
    """Observe Hybrid's route; WMC is optional after successful reduction.

    A native model-counting exec is independently witnessed, whereas tool_time
    is only diagnostic metadata. A version check is not WMC execution.
    """
    if not positive_verdict(verdict):
        raise ValueError("Equivalence check is not positive")
    native = native_solver_work_execve(trace_text, binary, solver)
    numeric = numeric_tool_time(tool_time)
    return {
        "native_model_count_execve": native,
        "tool_time_numeric": numeric,
        "native_time_consistent": native == numeric,
        "execution_path": (
            "native_wmc" if native else (
                "rr_only" if not numeric else "unverified_native_dispatch"
            )
        ),
    }


def verify(case: str, solver: str, backend: str) -> dict:
    from _benchmark_cases import MQT_CASES
    from QuPRS import check_equivalence
    from QuPRS.utils import WMC

    filename = CASES[case]
    matches = [row for row in MQT_CASES if row[0] == filename]
    if len(matches) != 1:
        raise RuntimeError(f"Original paper case missing or not unique: {filename}")
    _, strategy, reverse = matches[0]
    root = ROOT / "benchmarks" / "MQTBench"
    first = root / filename
    second = root / "h,ry,rz,cx" / filename
    hashes = {
        "source": hashlib.sha256(first.read_bytes()).hexdigest(),
        "transpiled": hashlib.sha256(second.read_bytes()).hexdigest(),
    }
    if reverse:
        first, second = second, first

    with WMC(solver) as binary:
        binary_path = Path(binary).resolve(strict=True)
        solver_binary = str(binary_path)
        solver_hash = hashlib.sha256(binary_path.read_bytes()).hexdigest()

    result = check_equivalence(
        str(first), str(second), method="hybrid", strategy=strategy,
        tool_name=solver, backend=backend, timeout=60,
    )
    verdict = str(result.equivalent)
    time = getattr(result, "tool_time", None)
    if not positive_verdict(result.equivalent):
        raise RuntimeError(f"Nonpositive equivalence for {case}/{solver}/{backend}: {verdict}")
    return {
        "case": case,
        "filename": filename,
        "method": "hybrid",
        "strategy": strategy,
        "reverse": reverse,
        "backend": backend,
        "solver": solver,
        "verdict": verdict,
        "tool_time_s": time,
        # Tool time is a diagnostic hint, not a requirement for Hybrid.
        "tool_time_numeric": numeric_tool_time(time),
        "solver_binary": solver_binary,
        "solver_sha256": solver_hash,
        "qasm_sha256": hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=tuple(CASES), required=True)
    parser.add_argument("--solver", choices=("gpmc", "ganak"), required=True)
    parser.add_argument("--backend", choices=("python", "rust"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.case, args.solver, args.backend)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()

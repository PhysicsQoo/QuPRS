#!/usr/bin/env python3
"""Prove Rust backend native WMC execution separately from instrumented timing."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test"))


def verify(solver: str) -> dict:
    from _benchmark_cases import MQT_CASES
    from QuPRS import check_equivalence
    from QuPRS.utils import WMC

    filename = "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm"
    rows = [row for row in MQT_CASES if row[0] == filename]
    if len(rows) != 1:
        raise RuntimeError("Original Grover4 benchmark case not uniquely found")
    _, strategy, reverse = rows[0]
    root = ROOT / "benchmarks" / "MQTBench"
    first, second = root / filename, root / "h,ry,rz,cx" / filename
    if reverse:
        first, second = second, first
    source_hashes = {
        "source": hashlib.sha256(first.read_bytes()).hexdigest(),
        "transpiled": hashlib.sha256(second.read_bytes()).hexdigest(),
    }
    with WMC(solver) as binary:
        binary = Path(binary)
        solver_info = {
            "name": solver,
            "binary": str(binary.resolve()),
            "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        }
    result = check_equivalence(
        str(first), str(second), method="hybrid", strategy=strategy,
        tool_name=solver, backend="rust", timeout=45,
    )
    status = str(result.equivalent)
    solver_time = getattr(result, "tool_time", None)
    if status not in ("equivalent", "equivalent*"):
        raise RuntimeError(f"{solver}: invalid correctness outcome {status}")
    if (not isinstance(solver_time, (int, float))
            or not math.isfinite(solver_time) or solver_time < 0):
        raise RuntimeError(
            f"{solver}: no evidence of completed native WMC invocation: "
            f"{solver_time!r}"
        )
    return {
        "case": filename, "strategy": strategy, "method": "hybrid",
        "backend": "rust", "source_hashes": source_hashes,
        "solver": solver_info, "status": status,
        "solver_time_seconds": solver_time,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver", required=True, choices=("gpmc", "ganak"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.solver)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

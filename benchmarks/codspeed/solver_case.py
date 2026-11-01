"""One source-pinned Hybrid call in an isolated Python/Rust verifier environment.

The enclosing CodSpeed WallTime benchmark captures parent startup, Rust
execution, Solver execution/wait, and I/O. This script does not time anything.
"""
import json
import sys
from pathlib import Path

from QuPRS import check_equivalence


def main() -> None:
    if len(sys.argv) != 7:
        raise SystemExit(
            "usage: solver_case.py FIXTURE_ROOT FILENAME STRATEGY SOLVER BACKEND REVERSE"
        )

    fixture_root = Path(sys.argv[1])
    filename, strategy, solver, backend = sys.argv[2:6]
    reverse = sys.argv[6] == "1"
    first = fixture_root / "benchmarks" / "MQTBench" / filename
    second = fixture_root / "benchmarks" / "MQTBench" / "h,ry,rz,cx" / filename
    if reverse:
        first, second = second, first
    if not first.is_file() or not second.is_file():
        raise FileNotFoundError(f"missing benchmark fixtures: {first}, {second}")

    result = check_equivalence(
        str(first), str(second), method="hybrid",
        strategy=strategy, tool_name=solver, backend=backend,
        timeout=90,
    )
    invoked = getattr(result, "wmc_solver_invoked", None)
    if invoked is None:
        # Older base revisions did not expose this provenance field.
        invoked = getattr(result, "tool_time", None) is not None

    print("QUPRS_WALLTIME_RESULT " + json.dumps({
        "verdict": str(result.equivalent),
        "solver_invoked": bool(invoked),
        "solver": solver,
        "rr_approximate": getattr(result, "rr_approximate", None),
        # Diagnostic only; these fields come from the already-executed
        # verifier request, so no additional Solver call is made.
        "wmc_printed_verdict": getattr(result, "wmc_printed_verdict", None),
        "wmc_precision_reason": getattr(result, "wmc_precision_reason", None),
        "wmc_print_resolution_distance": getattr(result, "wmc_print_resolution_distance", None),
        "approximate_distance_tolerance": getattr(result, "approximate_distance_tolerance", None),
        "wmc_numerical_verdict": getattr(result, "wmc_numerical_verdict", None),
    }, sort_keys=True))


if __name__ == "__main__":
    main()

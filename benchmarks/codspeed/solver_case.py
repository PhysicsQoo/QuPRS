"""One source-pinned Hybrid call in an isolated Python/Rust verifier environment.

The enclosing CodSpeed WallTime benchmark captures parent startup, Rust
execution, Solver execution/wait, and I/O. This script does not time anything.
"""
import json
import os
import sys
from pathlib import Path

from QuPRS import check_equivalence


def main() -> None:
    if len(sys.argv) not in (7, 8, 9):
        raise SystemExit(
            "usage: solver_case.py FIXTURE_ROOT FILENAME STRATEGY SOLVER "
            "BACKEND REVERSE [transpiled|random_rotation] [hybrid|wmc_only|reduction_rules]"
        )

    fixture_root = Path(sys.argv[1])
    filename, strategy, solver, backend = sys.argv[2:6]
    reverse = sys.argv[6] == "1"
    pair_variant = sys.argv[7] if len(sys.argv) >= 8 else "transpiled"
    method = sys.argv[8] if len(sys.argv) == 9 else "hybrid"
    if method not in {"hybrid", "wmc_only", "reduction_rules"}:
        raise ValueError(f"Unsupported diagnostic method: {method}")
    if pair_variant not in {"transpiled", "random_rotation"}:
        raise ValueError(f"Unsupported benchmark pair variant: {pair_variant}")
    counterpart = ("Random_Rotation" if pair_variant == "random_rotation"
                   else "h,ry,rz,cx")
    first = fixture_root / "benchmarks" / "MQTBench" / filename
    second = fixture_root / "benchmarks" / "MQTBench" / counterpart / filename
    if reverse:
        first, second = second, first
    if not first.is_file() or not second.is_file():
        raise FileNotFoundError(f"missing benchmark fixtures: {first}, {second}")

    result = check_equivalence(
        str(first), str(second), method=method,
        strategy=strategy, tool_name=solver, backend=backend,
        # Simulation under Valgrind can slow child Solver work dramatically.
        # Both versions use the same bounded experiment-specific override.
        # Standard Solver-inclusive WallTime retains the original 90 seconds.
        timeout=int(os.environ.get("QUPRS_CROSS_METHOD_SOLVER_TIMEOUT", "90")),
    )
    invoked = getattr(result, "wmc_solver_invoked", None)
    if invoked is None:
        # Older base revisions did not expose this provenance field.
        invoked = getattr(result, "tool_time", None) is not None

    print("QUPRS_WALLTIME_RESULT " + json.dumps({
        "verdict": str(result.equivalent),
        "solver_invoked": bool(invoked),
        "solver": solver,
        "method": method,
        "pair_variant": pair_variant,
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

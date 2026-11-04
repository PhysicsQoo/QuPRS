"""One source-pinned Hybrid call in an isolated Python/Rust verifier environment.

The enclosing CodSpeed WallTime benchmark captures parent startup, Rust
execution, Solver execution/wait, and I/O. This script does not time anything.
"""
import json
import inspect
import re
import os
import sys
from pathlib import Path

from QuPRS import check_equivalence


def _compatible_solver_kwargs(optional: dict) -> tuple[dict, str]:
    """Fail-closed bridge for the frozen pre-v0.14 dev verifier API.

    The old dev API supports distance=1e-8 and phase=1e-8, but does
    not accept per-call RR tolerance or GPMC digits. Its global RR value
    must already match 1e-10, and the old Rust GPMC *distance* adapter
    uses -prec=90 (NOT the new 30-digit default). Do not silently
    compare mixed GPMC precision or mutate old verifier code.
    """
    if not optional:
        return {}, "historical_api_defaults"
    supported = set(inspect.signature(check_equivalence).parameters)
    clean = dict(optional)
    legacy = False
    if "rr_tolerance" in clean and "rr_tolerance" not in supported:
        from QuPRS import config
        if getattr(config, "TOLERANCE", None) != clean["rr_tolerance"]:
            raise RuntimeError(
                "Legacy dev RR default differs from explicitly pinned 1e-10"
            )
        del clean["rr_tolerance"]
        legacy = True
    if "gpmc_precision_digits" in clean and "gpmc_precision_digits" not in supported:
        # The frozen dev Rust distance solver runs with -prec=90. Verify
        # the actual checked-out dev source instead of trusting a label.
        if (clean["gpmc_precision_digits"] != 90
                or clean.get("approximate_distance_tolerance") is None):
            raise RuntimeError(
                "Cannot compare old GPMC distance precision against non-90 digits"
            )
        adapter_source = Path.cwd() / "rust/pathsum/src/solver_adapter.rs"
        text = adapter_source.read_text(encoding="utf-8")
        if re.search(
            r"impl[ ]+SolverAdapter[ ]+for[ ]+GpmcDistanceAdapter[ ]*[{].{0,600}?[-]prec=90",
            text, flags=re.DOTALL,
        ) is None:
            raise RuntimeError("Legacy dev GPMC distance precision not proven to be 90")
        del clean["gpmc_precision_digits"]
        legacy = True
    unknown = set(clean) - supported
    if unknown:
        raise RuntimeError("Unrecognized verifier numerical parameters: " + ", ".join(sorted(unknown)))
    return clean, "legacy_90_digit_distance_source_checked" if legacy else "public_per_call_pinned"


CAPABILITY_PREFIX = "QUPRS_CAPABILITY_RESULT "
LEGACY_GPMC_90_UNPROVEN = "Legacy dev GPMC distance precision not proven to be 90"


def probe_qasm261_contract() -> None:
    """Use the *installed revision* to check the pinned numeric contract.

    This preflight performs no verification and produces no timings. Only the
    specific source-proven absence of legacy 90-digit distance support can
    become NOT_COMPARABLE_LEGACY_BASE; all other failures remain hard errors.
    """
    required = {
        "rr_tolerance": 1e-10,
        "approximate_distance_tolerance": 1e-8,
        "wmc_phase_tolerance": 1e-8,
        "gpmc_precision_digits": 90,
    }
    try:
        _, precision_contract = _compatible_solver_kwargs(required)
    except RuntimeError as exc:
        if str(exc) != LEGACY_GPMC_90_UNPROVEN:
            raise
        record = {
            "status": "NOT_COMPARABLE_LEGACY_BASE",
            "reason": LEGACY_GPMC_90_UNPROVEN,
        }
    else:
        record = {"status": "SUPPORTED", "precision_contract": precision_contract}
    print(CAPABILITY_PREFIX + json.dumps(record, sort_keys=True))


def main() -> None:
    if sys.argv[1:] == ["--probe-qasm261-contract"]:
        probe_qasm261_contract()
        return
    if len(sys.argv) not in (7, 8, 9, 10):
        raise SystemExit(
            "usage: solver_case.py FIXTURE_ROOT FILENAME STRATEGY SOLVER "
            "BACKEND REVERSE [transpiled|random_rotation] [hybrid|wmc_only|reduction_rules] "
            "[historical|qiskit-2.6.1-opt0]"
        )

    fixture_root = Path(sys.argv[1])
    filename, strategy, solver, backend = sys.argv[2:6]
    reverse = sys.argv[6] == "1"
    pair_variant = sys.argv[7] if len(sys.argv) >= 8 else "transpiled"
    method = sys.argv[8] if len(sys.argv) >= 9 else "hybrid"
    qasm_corpus = sys.argv[9] if len(sys.argv) == 10 else "historical"
    if qasm_corpus not in {"historical", "qiskit-2.6.1-opt0"}:
        raise ValueError(f"Unsupported QASM corpus: {qasm_corpus}")
    if Path(filename).name != filename or not filename.endswith(".qasm"):
        raise ValueError("QASM filename must be a basename")
    if method not in {"hybrid", "wmc_only", "reduction_rules"}:
        raise ValueError(f"Unsupported diagnostic method: {method}")
    if pair_variant not in {"transpiled", "random_rotation"}:
        raise ValueError(f"Unsupported benchmark pair variant: {pair_variant}")
    counterpart = ("Random_Rotation" if pair_variant == "random_rotation"
                   else "h,ry,rz,cx")
    first = fixture_root / "benchmarks" / "MQTBench" / filename
    target_dir = fixture_root / "benchmarks" / "MQTBench"
    if qasm_corpus != "historical":
        target_dir /= qasm_corpus
    second = target_dir / counterpart / filename
    if reverse:
        first, second = second, first
    if not first.is_file() or not second.is_file():
        raise FileNotFoundError(f"missing benchmark fixtures: {first}, {second}")

    # Per-call overrides are diagnostics only. Existing benchmarks with no
    # environment overrides retain their historical default semantics.
    optional = {}
    for name, env_name in (
        ("rr_tolerance", "QUPRS_DIAGNOSTIC_RR_TOLERANCE"),
        ("approximate_distance_tolerance", "QUPRS_DIAGNOSTIC_DISTANCE_TOLERANCE"),
        ("wmc_phase_tolerance", "QUPRS_DIAGNOSTIC_PHASE_TOLERANCE"),
    ):
        if env_name in os.environ:
            optional[name] = float(os.environ[env_name])
    if "QUPRS_DIAGNOSTIC_GPMC_DIGITS" in os.environ:
        optional["gpmc_precision_digits"] = int(os.environ["QUPRS_DIAGNOSTIC_GPMC_DIGITS"])
    supported_optional, precision_contract = _compatible_solver_kwargs(optional)
    result = check_equivalence(
        str(first), str(second), method=method,
        strategy=strategy, tool_name=solver, backend=backend,
        **supported_optional,
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
        "qasm_corpus": qasm_corpus,
        "precision_contract": precision_contract,
        "effective_rr_tolerance": optional.get("rr_tolerance", 1e-10),
        "effective_distance_tolerance": optional.get(
            "approximate_distance_tolerance", 1e-8),
        "effective_phase_tolerance": optional.get("wmc_phase_tolerance", 1e-8),
        "effective_gpmc_digits": optional.get("gpmc_precision_digits", 30),
        "wmc_log_wmc": getattr(result, "log_wmc", None),
        "wmc_expected_log2": getattr(result, "expect", None),
        "wmc_numeric_model_bound": getattr(result, "wmc_numeric_model_bound", None),
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

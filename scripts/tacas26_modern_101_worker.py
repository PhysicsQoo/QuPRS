#!/usr/bin/env python3
"""One modern TACAS science verification; capture solver stdout without changing GPMC.

Research-only. This emits NO performance timing or claims of arithmetic certification.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import sys

MARKER = "QUPRS_WALLTIME_RESULT "


def _safe(x):
    if x is None or isinstance(x, (str, bool, int)):
        return x
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    return str(x)


def _solver_stdout_details(stdout, expected_twice, eps):
    """Exactly parse the printed representation; this is NOT an arithmetic proof."""
    from QuPRS.utils.precision_count import (
        parse_printed_solver_output, classify_printed_distance
    )
    from decimal import Decimal, localcontext
    from fractions import Fraction
    try:
        cnt = parse_printed_solver_output(stdout)
        lines = [s for s in stdout.splitlines()
                 if s.startswith(("c s exact", "c o precision "))]
        if expected_twice is None:
            return {"printed_status": "MISSING_NORMALIZATION", "raw_lines": lines,
                    "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest()}
        proof = classify_printed_distance(cnt, expected_twice, eps)
        with localcontext() as ctx:
            ctx.prec = 100
            def to_dec(frac):
                return Decimal(frac.numerator) / Decimal(frac.denominator)
            abs_count = (to_dec(cnt.real) ** 2 + to_dec(cnt.imag) ** 2).sqrt()
            threshold = (
                (Decimal(2) ** Decimal(expected_twice))
                * (Decimal(1) - Decimal(str(eps)) ** 2)
            ).sqrt()
            rounding_l2 = (
                to_dec(cnt.real_print_half_unit) ** 2
                + to_dec(cnt.imag_print_half_unit) ** 2
            ).sqrt()
            # Any combined true complex-count error strictly less than
            # this gap would preserve the printed-count binary classification.
            # We do not assert that GPMC or input weights satisfy such a bound.
            allowance = abs(abs_count - threshold) - rounding_l2
            relative_allowance = allowance / (Decimal(2) ** Decimal(expected_twice / 2))
        return {
            "printed_status": proof.status,
            "printed_reason": proof.reason,
            "printed_resolution_only": True,
            "certified_solver_arithmetic": False,
            "solver_arithmetic_error_bound": None,
            "solver_arithmetic_certificate": "ABSENT",
            "conditional_allowable_count_error": str(allowance),
            "conditional_allowable_normalized_error": str(relative_allowance),
            "rounding_component_half_unit_re": str(cnt.real_print_half_unit),
            "rounding_component_half_unit_im": str(cnt.imag_print_half_unit),
            "solver_printed_complex_re": str(cnt.real),
            "solver_printed_complex_im": str(cnt.imag),
            "raw_lines": lines,
            "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        }
    except Exception as exc:
        return {"printed_status": "UNCLASSIFIABLE", "parse_error": str(exc),
                "certified_solver_arithmetic": False,
                "solver_arithmetic_certificate": "ABSENT",
                "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest()}


def main():
    if len(sys.argv) != 9:
        raise SystemExit("usage: worker.py ROOT FILENAME STRATEGY SOLVER BACKEND REVERSE PAIR_VARIANT METHOD")
    root = Path(sys.argv[1]).resolve()
    filename, strategy, solver, backend, reverse, variant, method = sys.argv[2:]
    if solver != "gpmc" or backend not in ("python", "rust") or method not in ("hybrid", "wmc_only"):
        raise ValueError("Unsupported science probe configuration")
    if variant not in ("transpiled", "random_rotation"):
        raise ValueError("Unknown counterpart variant")
    if any(s in filename for s in ("/", "\\", "..")) or not filename.endswith(".qasm"):
        raise ValueError("Invalid fixture filename")
    first = root / "benchmarks/MQTBench" / filename
    second = root / "benchmarks/MQTBench" / (
        "Random_Rotation" if variant == "random_rotation" else "h,ry,rz,cx"
    ) / filename
    if reverse == "1":
        first, second = second, first
    if not first.is_file() or not second.is_file():
        raise ValueError("Missing pinned QASM inputs")
    from QuPRS import check_equivalence
    from QuPRS.utils import solver_process, get_gpmc_path
    with get_gpmc_path() as path:
        gpmc_sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    eps = float(os.environ["QUPRS_DIAGNOSTIC_DISTANCE_TOLERANCE"])
    rr = float(os.environ["QUPRS_DIAGNOSTIC_RR_TOLERANCE"])
    phase = float(os.environ["QUPRS_DIAGNOSTIC_PHASE_TOLERANCE"])
    digits = int(os.environ["QUPRS_DIAGNOSTIC_GPMC_DIGITS"])
    limit = int(os.environ["QUPRS_CROSS_METHOD_SOLVER_TIMEOUT"])
    if digits not in (30, 90) or not 0 < eps < 1 or rr < 0 or not 0 <= phase < 1:
        raise ValueError("Unsupported diagnostic precision/tolerance")
    captures = []
    actual_run = solver_process.run
    if backend == "python":
        def capture(command, timeout):
            output = actual_run(command, timeout)
            if "gpmc" in Path(str(command[0])).name.lower():
                captures.append({"command_args": list(map(str, command[1:-1])),
                                 "cnf_sha256": hashlib.sha256(Path(command[-1]).read_bytes()).hexdigest(),
                                 "returncode": output.returncode,
                                 "stdout": output.stdout,
                                 "stderr_sha256": hashlib.sha256(output.stderr.encode()).hexdigest()})
            return output
        solver_process.run = capture
    try:
        result = check_equivalence(
            str(first), str(second), method=method, strategy=strategy,
            tool_name="gpmc", timeout=limit, backend=backend,
            rr_tolerance=rr, wmc_phase_tolerance=phase,
            approximate_distance_tolerance=eps, gpmc_precision_digits=digits,
        )
    finally:
        solver_process.run = actual_run
    invoked = getattr(result, "wmc_solver_invoked", None)
    if invoked is None:
        invoked = getattr(result, "tool_time", None) is not None
    twice = None
    expected = getattr(result, "expect", None)
    if expected is not None and math.isfinite(float(expected)):
        k = float(expected) * 2
        if abs(k - round(k)) < 1e-9:
            twice = int(round(k))
    detail = []
    for captured in captures:
        entry = {k: v for k, v in captured.items() if k != "stdout"}
        entry["printed_count"] = _solver_stdout_details(captured["stdout"], twice, eps)
        detail.append(entry)
    record = {
        "verdict": str(result.equivalent),
        "solver": "gpmc",
        "solver_binary_sha256": gpmc_sha,
        "solver_invoked": bool(invoked),
        "backend": backend, "method": method,
        "pair_variant": variant,
        "effective_rr_tolerance": rr,
        "effective_distance_tolerance": eps,
        "effective_phase_tolerance": phase,
        "effective_gpmc_digits": digits,
        "wmc_expected_log2": _safe(expected),
        "wmc_normalization_twice_log2": twice,
        "wmc_log_wmc": _safe(getattr(result, "log_wmc", None)),
        "wmc_numerical_verdict": _safe(getattr(result, "wmc_numerical_verdict", None)),
        "wmc_precision_reason": _safe(getattr(result, "wmc_precision_reason", None)),
        "wmc_printed_verdict": _safe(getattr(result, "wmc_printed_verdict", None)),
        "wmc_numeric_model_bound": _safe(getattr(result, "wmc_numeric_model_bound", None)),
        "wmc_print_resolution_distance": _safe(getattr(result, "wmc_print_resolution_distance", None)),
        "rr_approximate": _safe(getattr(result, "rr_approximate", None)),
        "observed_solver_calls": detail,
        "solver_output_observation": (
            "GPMC_RAW_STDOUT_CAPTURED" if detail
            else ("RUST_INTERNAL_SOLVER_STDOUT_UNAVAILABLE" if invoked and backend == "rust"
                  else "NO_EXTERNAL_SOLVER_INVOKED")
        ),
        "arithmetic_certification": (
            "NOT_CERTIFIED_SOLVER_ERROR_BOUND_ABSENT"
            if invoked else "NOT_APPLICABLE_NO_SOLVER_CALL"
        ),
        "timing": "SCIENCE_ONLY_NO_WALLTIME",
    }
    print(MARKER + json.dumps(record, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()

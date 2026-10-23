#!/usr/bin/env python3
"""Exact source-radian oracle versus Rust's actual QASM->Angle->PathSum.

This intentionally produces an observational report with a separate genuine
scientific RED, not an xfail and not a production change. No WMC solver runs.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys

CASES = (
    "zero", "tiny_positive_1e12", "tiny_negative_1e12",
    "tiny_positive_1e10", "above_epsilon_below_denom",
    "denominator_boundary", "retained_small", "retained_reference",
)
PREFIX = "ANGLE_BOUNDARY"
EXACT_QASM_PREFIX = (
    'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_cosine_trace_reference(angle):
    """Rational proof 1-x²/2 <= cos(x) <= 1-x²/2+x⁴/24.

    For |angle|<=1, x=|angle|/2<=1/2. The upper bound is <1
    whenever x>0. This detects physical non-equivalence up to global
    phase with no floating-point near-unity comparison.
    """
    if not isinstance(angle, Fraction) or abs(angle) > 1:
        raise ValueError("Unsupported exact-radian source angle")
    x = abs(angle) / 2
    lo = 1 - x * x / 2
    hi = lo + x ** 4 / 24
    return dict(
        normalized_trace_lower=str(lo),
        normalized_trace_upper=str(hi),
        lower_bound_on_strict_magnitude_defect=str(1 - hi),
        certified_non_equivalent_up_to_global_phase=(hi < 1),
    )


def parse_native_lines(stdout, output):
    found = {}
    for raw in stdout.splitlines():
        if not raw.startswith(PREFIX + "\t"):
            raise ValueError("Unexpected native output: " + raw[:120])
        parts = raw.split("\t")
        if len(parts) != 8:
            raise ValueError("Malformed Rust source provenance record")
        marker, label, token, num, denom, n, term_count, identity = parts
        if marker != PREFIX or label not in CASES or label in found:
            raise ValueError("Repeated or unsupported Rust boundary record")
        qasm = (output / (label + ".qasm")).read_bytes()
        expected = (EXACT_QASM_PREFIX + f"rz({token}) q[0];\n").encode()
        if qasm != expected:
            raise ValueError("Rust emitted QASM differs from parsed source token")
        angle = Fraction(token)
        numerator = int(num)
        denominator = int(denom)
        if denominator <= 0 or int(n) != 1 or int(term_count) < 0:
            raise ValueError("Invalid Rust angle or circuit dimensions")
        if identity not in ("true", "false"):
            raise ValueError("Malformed Rust boolean identity status")
        collapsed = numerator == 0
        pathsum_identity = identity == "true"
        if collapsed and not pathsum_identity:
            raise ValueError("Zero input angle unexpectedly produced nonidentity")
        mathematical = strict_cosine_trace_reference(angle)
        if not angle and not pathsum_identity:
            raise ValueError("Zero control unexpectedly produced nonidentity")
        if angle and collapsed and pathsum_identity:
            stage = "ANGLE_CONVERSION_LOSS_BEFORE_WMC"
        elif angle and not collapsed and not pathsum_identity:
            stage = "NONZERO_ANGLE_RETAINED_BY_PATHSUM"
        elif not angle and pathsum_identity:
            stage = "ZERO_REFERENCE_CONTROL"
        else:
            stage = "INDETERMINATE_PATHSUM_AFTER_ANGLE_CONVERSION"
        found[label] = {
            "case": label, "source_qasm_sha256": sha256(qasm),
            "literal": token, "exact_source_radians": str(angle),
            "exact_source_nonzero": angle != 0,
            "rust_angle_numerator": numerator,
            "rust_angle_denominator": denominator,
            "rust_angle_exact_rational_pi_units": str(Fraction(numerator, denominator)),
            "rust_angle_zero": collapsed,
            "pathsum_identity_after_rust_parse": pathsum_identity,
            "pathsum_phase_terms": int(term_count),
            "stage_classification": stage,
            **mathematical,
        }
    if set(found) != set(CASES):
        raise ValueError("Incomplete Rust boundary capture")
    return [found[name] for name in CASES]


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--output", type=Path, default=Path("rust-angle-red-results"))
    opts = args.parse_args()
    output = opts.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cmd = ["cargo", "run", "--release", "--locked", "--manifest-path",
           "rust/Cargo.toml", "-p", "pathsum", "--example",
           "qasm_angle_boundary", "--", str(output)]
    completed = subprocess.run(cmd, capture_output=True, text=True, timeout=360)
    (output / "rust-stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (output / "rust-stdout.txt").write_text(completed.stdout, encoding="utf-8")
    if completed.returncode:
        print(f"RUST_DIAGNOSTIC_BUILD_OR_EXECUTION_FAILED={completed.returncode}")
        return 2
    records = parse_native_lines(completed.stdout, output)
    summary = {
        "schema": "tiny-rust-qasm-angle-stage-audit-v1",
        "source_oracle": "exact decimal radians, alternating cosine bound",
        "probed_stage": "Rust QASM -> Angle -> unreduced PathSum, before WMC",
        "native_solver_called": False,
        "wmc_tolerance_used": False,
        "scientific_result": (
            "SOURCE_SEMANTIC_LOSS"
            if any(row["stage_classification"] == "ANGLE_CONVERSION_LOSS_BEFORE_WMC"
                   for row in records)
            else "NO_COLLAPSE_IN_TESTED_CASES"
        ),
        "cases": records,
    }
    (output / "angle-boundary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "scientific_result": summary["scientific_result"],
        "cases": len(records),
        "source_nonzero_collapsed": sum(
            row["exact_source_nonzero"] and row["rust_angle_zero"]
            for row in records
        ),
    }, sort_keys=True), flush=True)
    # Evidence production succeeding != scientific property passing:
    # the separate non-xfail strict RED test enforces that property.
    return 0


if __name__ == "__main__":
    sys.exit(main())

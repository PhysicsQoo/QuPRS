"""Compare genuine Python versus Rust d4 counts for identical QuPRS CNF bytes.

Printed-decimal parity is an integration contract, not a rigorous solver
roundoff bound. Source-CNF SHA and original binary provenance remain separate.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path


def compare(python_report: Path, rust_log: Path, output: Path):
    py = json.loads(python_report.read_text())
    if py.get("native_python_wmc_facade_gate") != "PASS":
        raise ValueError("Python native d4 count gate was not PASS")
    expected = {item["source"]: item for item in py["cases"]}
    if len(expected) != 6:
        raise ValueError("Python report must contain six distinct source CNFs")
    rust = {}
    for line in rust_log.read_text().splitlines():
        if not line.startswith("QOO157_RUST_SAME_CNF\t"):
            continue
        parts = line.split("\t")
        if len(parts) != 7:
            raise ValueError("malformed Rust d4 parity record")
        _, name, sha, re, im, ru, iu = parts
        if name in rust:
            raise ValueError("duplicate Rust d4 parity case")
        rust[name] = {
            "sha256": sha, "count": (Fraction(re), Fraction(im)),
            "printed_units": (Fraction(ru), Fraction(iu)),
        }
    if set(rust) != set(expected):
        raise ValueError("mismatched Python/Rust source CNF set")
    outcomes = []
    for name in sorted(expected):
        py_case = expected[name]
        actual = rust[name]
        source_sha = py_case["cnf_sha256"]
        if source_sha != actual["sha256"]:
            raise ValueError(f"Python/Rust input CNF SHA mismatch: {name}")
        py_count = tuple(Fraction(x) for x in py_case["observed_decimal_exact"])
        equal = py_count == actual["count"]
        outcomes.append({
            "source": name, "sha256": source_sha, "status": (
                "SAME_PRINTED_RATIONAL" if equal else "PRINTED_COUNT_MISMATCH"
            ),
            "python": [str(x) for x in py_count],
            "rust": [str(x) for x in actual["count"]],
            "rust_printed_half_units": [str(x) for x in actual["printed_units"]],
        })
    success = all(x["status"] == "SAME_PRINTED_RATIONAL" for x in outcomes)
    result = {
        "complete": True, "cases": outcomes,
        "python_native_binary_sha256": py["d4_binary_sha256"],
        "source_sha_identical": True,
        "same_input_printed_count_gate": "PASS" if success else "FAIL",
        "arithmetic_certified": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "report": str(output), "cases": len(outcomes),
        "same_input_printed_count_gate": result["same_input_printed_count_gate"]
    }))
    if not success:
        raise SystemExit(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python-report", type=Path, required=True)
    parser.add_argument("--rust-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    compare(args.python_report, args.rust_log, args.output)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Research-only A/B replay of native GPMC significant-digit output bounds.

Input: extract the sealed dev-public-single-pass-boundary-experiment artifact.
No Solver invocation, QuPRS import, production change, or proof certification.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
import re


CASES = (
    ("forced_unit_12", 0, Fraction(1, 10**8), "equivalent"),
    ("forced_unit_128", 0, Fraction(1, 10**8), "unknown"),
    ("forced_unit_160", 0, Fraction(1, 10**8), "unknown"),
    ("forced_unit_512", 0, Fraction(1, 10**8), "unknown"),
    ("sxsx_global_phase", 2, Fraction(2, 10**4), "equivalent*"),
)


def conditional_verdict(real, imag, half_r, half_i, model_error, exponent, epsilon):
    lo_r = max(Fraction(0), abs(real) - half_r - model_error)
    lo_i = max(Fraction(0), abs(imag) - half_i - model_error)
    hi_r = abs(real) + half_r + model_error
    hi_i = abs(imag) + half_i + model_error
    low = lo_r * lo_r + lo_i * lo_i
    high = hi_r * hi_r + hi_i * hi_i
    norm_sq = Fraction(2) ** exponent
    boundary = norm_sq * (1 - epsilon*epsilon)
    if low > norm_sq:
        return "unknown"
    if high < boundary:
        return "not_equivalent"
    if low >= boundary:
        return "equivalent*" if imag and real == 0 else "equivalent"
    return "unknown"


def significant_digit_half_unit(value, precision):
    """Candidate MPFR %.pRg rounding half-unit for suppressed trailing zeros.

    This requires independent verification that the exact native GPMC build
    uses the indicated mpfr::mpreal stream significant-digit contract.
    """
    if value == 0:
        return Fraction(0)
    if value.denominator != 1:
        raise ValueError("Study deliberately limited to exact integer stdout")
    decimal_value = Decimal(value.numerator)
    exponent = decimal_value.adjusted() - precision + 1
    return Fraction(1, 2) * Fraction(10) ** exponent


def replay(folder: Path):
    records = json.loads((folder/"boundary-observations.json").read_text())
    lookup = {r["case"]: r for r in records}
    results = []
    for name, n, epsilon, expected in CASES:
        record = lookup[name]
        evidence = record.get("raw", record.get("raw_stdout"))
        native_file = folder / (
            ("public_" if name == "sxsx_global_phase" else "") +
            name + ".stdout.txt"
        )
        text = native_file.read_text()
        marks = re.findall(r"^c o precision (\d+)\s*$", text, re.MULTILINE)
        assert marks == ["90"], (name, marks)
        assert evidence["raw_count_lines"][0] in text
        assert evidence["format_name"] == "c s exact double prec-sci"

        re_v, im_v = Fraction(evidence["real"]), Fraction(evidence["imag"])
        old_re = Fraction(evidence["real_print_half_unit"])
        old_im = Fraction(evidence["imag_print_half_unit"])
        error = Fraction(record.get("conditional_component_error",
                                   record.get("production_numeric_model_bound")))
        old = conditional_verdict(
            re_v, im_v, old_re, old_im, error, n, epsilon)
        new_re = significant_digit_half_unit(re_v, 90)
        new_im = significant_digit_half_unit(im_v, 90)
        candidate = conditional_verdict(
            re_v, im_v, new_re, new_im, error, n, epsilon)
        assert old == "unknown", (name, old)
        assert candidate == expected, (name, candidate, expected)
        results.append({
            "case": name,
            "native_stdout": evidence["raw_count_lines"][0],
            "native_precision_digits": 90,
            "current_status": old,
            "candidate_status": candidate,
            "current_half_units": [str(old_re), str(old_im)],
            "candidate_half_units": [str(new_re), str(new_im)],
            "conditional_model_component_error": str(error),
            "source_classification": "printer_only_AB_not_solver_certificate",
        })
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-folder", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    rows = replay(options.artifact_folder)
    result = {
        "assumption": "Pinned native GPMC cout.precision(90) plus mpfr::mpreal %.90Rg; not Ganak",
        "verdicts_are_conditional": True,
        "solver_invocations": 0,
        "rows": rows,
    }
    body = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(body)
    if options.output:
        options.output.write_text(body)
    print("RESEARCH_PRINTER_PRECISION_AB_PASS", flush=True)


if __name__ == "__main__":
    main()

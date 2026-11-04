"""Research-only d4 nominal decimal-precision parity with GPMC -prec.

Pinned jm62300/d4 fork only; patches its C++ counter in a *scratch checkout*.
GPMC sets MPFR's bits=ceil(digits*log2(10)). GMP mpf rounds requested bits
up to implementation limbs: the *actual* GMP bit count MUST be read from
the native runtime and reported, not falsely declared equal to MPFR bits.

Both d4 model counting *and* output formatting use the requested 30 or 90
decimal digits. Not an error bound or an upstream production patch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

UPSTREAM = "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690"
ALLOWED_DIGITS = (30, 90)
MARKER = "// QOO-157 research-only GPMC decimal precision matched d4 variant"
MAIN_OLD = "int main(int argc, char** argv) {\n  auto start = std::chrono::system_clock::now();"
OUTPUT_OLD = "  os.precision(50);"
WORK_OLD = "    mpf_set_default_prec(426);  // ~128 decimal digits"
PRINT_OLD = "    std::cout.precision(50);"


def patch(d4_root: Path, digits: int, evidence: Path) -> dict:
    if digits not in ALLOWED_DIGITS:
        raise ValueError("Only published GPMC 30/90 decimal modes are supported")
    bits = math.ceil(digits * math.log2(10))
    root = d4_root.resolve()
    actual_sha = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual_sha != UPSTREAM:
        raise ValueError("d4 source not pinned to approved upstream")
    if subprocess.check_output(
        ["git", "-C", str(root), "status", "--porcelain"], text=True
    ).strip():
        raise ValueError("d4 source checkout must be pristine before patch")

    main = root / "c++/counter/src/Main.cpp"
    counter = root / "c++/counter/src/Counter.cpp"
    old_main, old_counter = main.read_text(), counter.read_text()
    if old_main.count(MAIN_OLD) != 1 or MARKER in old_main:
        raise ValueError("unrecognized d4 main precision initialization")
    if (old_counter.count(OUTPUT_OLD) != 1 or
            old_counter.count(WORK_OLD) != 2 or
            old_counter.count(PRINT_OLD) != 2):
        raise ValueError("unrecognized pinned d4 output precision anchors")

    # Before any option parsing, DIMACS weight construction, or count objects.
    # Record the *real* GMP-allocated default bits; GMP can round to its
    # internal limb precision, unlike MPFR's exact requested bit precision.
    new_main = old_main.replace(
        MAIN_OLD,
        "int main(int argc, char** argv) {\n"
        f"  {MARKER}\n"
        f"  mpf_set_default_prec({bits});\n"
        f"  std::cout << \"c o requested-precision-digits {digits}\\\\n\";\n"
        "  std::cout << \"c o actual-gmp-precision-bits \""
        " << mpf_get_default_prec() << \"\\\\n\";\n"
        "  auto start = std::chrono::system_clock::now();"
    )
    # Change the old post-count precision setting too so no late stage can
    # silently switch the requested mode. Match emitted decimal digits for
    # real and imaginary components, not only the *default* std::cout.
    new_counter = (old_counter
        .replace(OUTPUT_OLD, f"  os.precision({digits});")
        .replace(WORK_OLD, f"    mpf_set_default_prec({bits});  // QOO-157 research mode")
        .replace(PRINT_OLD, f"    std::cout.precision({digits});"))
    main.write_text(new_main)
    counter.write_text(new_counter)
    evidence.mkdir(parents=True, exist_ok=True)
    report = {
        "source_commit": UPSTREAM, "precision_target_decimal_digits": digits,
        "mpfr_equivalent_requested_bits": bits,
        "d4_gmp_requested_bits": bits,
        "gmp_actual_bits": "MUST_READ_FROM_NATIVE_OUTPUT",
        "output_print_significant_digits": digits,
        "source_decimal_input_weights": "unchanged",
        "precision_certificate": False, "valid_comparison": "nominal digits only",
        "source_files": {
            "c++/counter/src/Main.cpp": {
                "before_sha256": hashlib.sha256(old_main.encode()).hexdigest(),
                "after_sha256": hashlib.sha256(new_main.encode()).hexdigest(),
            },
            "c++/counter/src/Counter.cpp": {
                "before_sha256": hashlib.sha256(old_counter.encode()).hexdigest(),
                "after_sha256": hashlib.sha256(new_counter.encode()).hexdigest(),
            },
        },
    }
    target = evidence / f"d4-precision-{digits}-source-provenance.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--digits", type=int, choices=ALLOWED_DIGITS, required=True)
    args = p.parse_args()
    print(json.dumps(patch(args.upstream, args.digits, args.evidence)))


if __name__ == "__main__":
    main()

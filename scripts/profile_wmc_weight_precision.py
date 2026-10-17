"""Reproducible microprofile for Python path-sum WMC weight generation.

Compare 53-bit and 113-bit SymEngine phase weights on the *same* runner.
No solver is invoked and no performance result is used as a CI hard gate.

Example:
    python scripts/profile_wmc_weight_precision.py --samples 96 --repeats 5 \
        --json-file python_wmc_precision_profile.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from functools import lru_cache
from pathlib import Path

import symengine as se


def phase_corpus(samples: int, distinct: bool) -> list:
    """Deterministic rational phases; repeated mode uses eight distinct phases."""
    unique_count = samples if distinct else min(8, samples)
    unique_phases = [
        se.Rational(2 * i + 1, 7 * i + 19) for i in range(unique_count)
    ]
    return [unique_phases[i % unique_count] for i in range(samples)]


def generate_weight(phase, bits: int):
    """Match the two evaluations and serialization used by ps2wmc.py."""
    angle = 2 * se.pi * phase
    real = se.cos(angle).evalf(bits)
    imag = se.sin(angle).evalf(bits)
    return real, imag


@lru_cache(maxsize=4096)
def cached_weight(phase, bits: int):
    """Measurement-only prototype; production QuPRS does not use this cache."""
    return generate_weight(phase, bits)


def weight_strings(phases: list, bits: int, cached: bool) -> int:
    generator = cached_weight if cached else generate_weight
    return sum(
        len(f"{real} {imag} 0")
        for real, imag in (generator(phase, bits) for phase in phases)
    )


def timed_trial(fn) -> int:
    start = time.perf_counter_ns()
    result = fn()
    elapsed = time.perf_counter_ns() - start
    if result <= 0:
        raise AssertionError("Expected nonempty serialized weight input")
    return elapsed


def measure(fn, warmups: int, repeats: int, samples: int) -> dict:
    for _ in range(warmups):
        fn()
    durations = [timed_trial(fn) for _ in range(repeats)]
    per_weight_ns = statistics.median(durations) / samples
    return {
        "median_ns_per_weight": per_weight_ns,
        "median_us_per_weight": per_weight_ns / 1000.0,
        "min_ns_per_weight": min(durations) / samples,
        "max_ns_per_weight": max(durations) / samples,
        "repeats": repeats,
    }


def precision_oracle(phases: list) -> dict:
    """Compare against independent 80-digit mpmath trig (never through f64).

    Oracle measurements are separate from the timed region.
    """
    from mpmath import mp

    max_error = {"53": mp.mpf("0"), "113": mp.mpf("0")}
    max_delta = mp.mpf("0")
    with mp.workdps(80):
        for phase in dict.fromkeys(phases):
            angle = 2 * mp.pi * mp.mpf(str(phase.p)) / mp.mpf(str(phase.q))
            reference = (mp.cos(angle), mp.sin(angle))
            evaluated = {}
            for bits in (53, 113):
                re, im = generate_weight(phase, bits)
                actual = (mp.mpf(str(re)), mp.mpf(str(im)))
                evaluated[bits] = actual
                error = max(abs(a - b) for a, b in zip(actual, reference))
                name = str(bits)
                max_error[name] = max(max_error[name], error)
            max_delta = max(
                max_delta,
                max(abs(a - b) for a, b in zip(evaluated[53], evaluated[113])),
            )
        return {
            "oracle_decimal_digits": 80,
            "oracle": "mpmath cos/sin of rational * 2*pi",
            "max_abs_component_error": {
                bits: mp.nstr(val, 14) for bits, val in max_error.items()
            },
            "max_abs_component_delta_53_to_113": mp.nstr(max_delta, 14),
        }


def run_profile(samples: int, warmups: int, repeats: int) -> dict:
    corpus = {}
    for name, distinct in [("distinct", True), ("repeated", False)]:
        phases = phase_corpus(samples, distinct=distinct)
        digest = hashlib.sha256(
            "|".join(str(phase) for phase in phases).encode("utf-8")
        ).hexdigest()
        measurements = {}

        # Alternating bit order is a simple guard against warm-up bias.
        for bits in ((53, 113) if name == "distinct" else (113, 53)):
            measurements[str(bits)] = measure(
                lambda b=bits: weight_strings(phases, b, cached=False),
                warmups, repeats, samples,
            )

        # Independent cache experiment, not an active production optimization.
        cached_weight.cache_clear()
        for bits in (53, 113):
            measurements[f"{bits}_cache_warm"] = measure(
                lambda b=bits: weight_strings(phases, b, cached=True),
                warmups, repeats, samples,
            )

        ratio = (
            measurements["113"]["median_ns_per_weight"]
            / measurements["53"]["median_ns_per_weight"]
        )
        corpus[name] = {
            "unique_phases": samples if distinct else min(8, samples),
            "phase_sha256": digest,
            "accuracy": precision_oracle(phases),
            "measurements": measurements,
            "ratio_113_to_53": ratio,
            "cache_is_prototype_only": True,
        }

    return {
        "schema_version": 1,
        "unit": "nanoseconds per serialized complex weight",
        "samples": samples,
        "warmups": warmups,
        "repeats": repeats,
        "environment": {
            "python": sys.version.split()[0],
            "symengine": getattr(se, "__version__", "unknown"),
            "symengine_mpfr_available": getattr(se, "have_mpfr", None),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "precision_bits": [53, 113],
        "corpora": corpus,
        "notes": [
            "Measures phase conversion, SymEngine cos/sin evaluation, and string serialization.",
            "Both precision modes use identical preconstructed rational phases.",
            "Warm-cache timings are hypothetical: no application cache is enabled.",
            "Accuracy uses an independent 80-digit mpmath reference outside timed regions.",
            "Times are local to this runner; cross-runner absolute comparisons are invalid.",
            "Precision bits do not establish an exact-arithmetic circuit certificate.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=96)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--json-file", type=Path)
    args = parser.parse_args()

    if args.samples < 8 or args.repeats < 3 or args.warmups < 0:
        parser.error("samples must be >= 8, repeats >= 3, warmups >= 0")

    report = run_profile(args.samples, args.warmups, args.repeats)
    print(f"Python {report['environment']['python']}, SymEngine {report['environment']['symengine']}")
    for name, row in report["corpora"].items():
        times = row["measurements"]
        print(
            f"{name} (unique={row['unique_phases']}): "
            f"53 bits={times['53']['median_us_per_weight']:.3f} us/weight; "
            f"113 bits={times['113']['median_us_per_weight']:.3f} us/weight; "
            f"ratio={row['ratio_113_to_53']:.3f}x"
        )
        print(
            f"  hypothetical warm-cache: "
            f"53 bits={times['53_cache_warm']['median_us_per_weight']:.3f}, "
            f"113 bits={times['113_cache_warm']['median_us_per_weight']:.3f} us/weight"
        )

    if args.json_file:
        args.json_file.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"JSON: {args.json_file}")


if __name__ == "__main__":
    main()

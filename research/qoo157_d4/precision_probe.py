"""Bounded d4 C++ complex-WMC precision-loss experiment.

A reported finite complex decimal is not a rounding certificate. Unlike the
general conformance pilot, a disappeared 1e-40 residual is never declared
"tight" just because its absolute error falls below 1e-25.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

from poc_d4 import (
    UPSTREAM_REPO, UPSTREAM_SHA, as_pair, native_count, oracle_count, sha256
)

SWEEP = (12, 16, 18, 19, 20, 21, 24, 28, 32, 40, 60)
IMAG_SWEEP = (16, 20, 28, 40)


def one_plus_inverse_power(k: int) -> str:
    if k < 1 or k > 100:
        raise ValueError("invalid precision sweep exponent")
    return "1." + ("0" * (k - 1)) + "1"


def weighted_free_complex(pos_re: str, pos_im: str, neg_re: str, neg_im: str) -> str:
    return (
        "p cnf 1 0\nc t wmc\n"
        f"c p weight 1 {pos_re} {pos_im} 0\n"
        f"c p weight -1 {neg_re} {neg_im} 0\n"
    )


def cases() -> dict[str, str]:
    output = {}
    for k in SWEEP:
        output[f"real_residual_1e-{k}"] = weighted_free_complex(
            one_plus_inverse_power(k), "0", "-1", "0"
        )
    for k in IMAG_SWEEP:
        output[f"imag_residual_1e-{k}"] = weighted_free_complex(
            "0", one_plus_inverse_power(k), "0", "-1"
        )
    large = "1" + ("0" * 30)
    output["large_cancellation_keep_one"] = weighted_free_complex(
        str(int(large) + 1), "0", "-" + large, "0"
    )
    return output


def run_probe(binary: Path, workdir: Path, timeout: int) -> dict:
    binary = binary.resolve()
    if not binary.is_file():
        raise FileNotFoundError(binary)
    workdir = workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    records = []
    for name, source in cases().items():
        inp = workdir / f"{name}.cnf"
        inp.write_text(source, encoding="utf-8")
        expected = oracle_count(source)
        record = {
            "case": name,
            "cnf_sha256": sha256(source.encode()),
            "exact_decimal_oracle": as_pair(expected),
            "arithmetic_certified": False,
        }
        try:
            observed, meta = native_count(binary, inp, timeout)
        except (OSError, RuntimeError, ValueError) as exc:
            record.update(status="NATIVE_ERROR", error=str(exc)[:1024])
        else:
            absolute_error = tuple(abs(a - b) for a, b in zip(observed, expected))
            lost = observed == (0, 0) and expected != (0, 0)
            status = (
                "RESIDUAL_LOST" if lost else
                "PRINTED_EQUAL" if observed == expected else "PRINTED_DIFFERENCE"
            )
            record.update(
                status=status,
                reported_decimal=as_pair(observed),
                absolute_error=as_pair(absolute_error),
                **meta,
            )
        records.append(record)
    summary = dict(sorted(Counter(x["status"] for x in records).items()))
    report = {
        "upstream_repo": UPSTREAM_REPO,
        "upstream_commit": UPSTREAM_SHA,
        "binary_sha256": sha256(binary.read_bytes()),
        "precision_gate": "NOT_CERTIFIED",
        "note": "Observed printed-decimal arithmetic loss, never a safe QuPRS tolerance",
        "status_counts": summary,
        "cases": records,
    }
    path = workdir / "precision_report.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(path),
        "case_count": len(records),
        "status_counts": summary,
        "precision_gate": "NOT_CERTIFIED",
    }, sort_keys=True))
    if summary.get("NATIVE_ERROR", 0):
        raise SystemExit(3)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    run_probe(args.binary, args.workdir, args.timeout)


if __name__ == "__main__":
    main()

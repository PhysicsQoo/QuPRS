"""Exact Fraction oracle for research-only Rust d4 printed rational transcript."""
from __future__ import annotations
import argparse
from fractions import Fraction
import json
from pathlib import Path
import re

from poc_d4 import oracle_count

MARKER = re.compile(r"^D4_RUST_COUNT (\S+\.cnf) (-?\d+(?:/\d+)?) (-?\d+(?:/\d+)?)\s*$")


def evaluate(log: Path, directory: Path, out: Path):
    values = {}
    for line in log.read_text().splitlines():
        match = MARKER.match(line.strip())
        if match:
            name = match.group(1)
            if name in values:
                raise ValueError("duplicate Rust d4 count " + name)
            values[name] = (Fraction(match.group(2)), Fraction(match.group(3)))
    cases = sorted(directory.glob("quprs_*.cnf"))
    if len(cases) != 6 or set(values) != {p.name for p in cases}:
        raise ValueError(f"expected six paired Rust native results, got {list(values)}")
    records = []
    for case in cases:
        source = case.read_text()
        expected = oracle_count(source)
        observed = values[case.name]
        difference = tuple(abs(a - b) for a, b in zip(observed, expected))
        scale = max(Fraction(1), abs(expected[0]), abs(expected[1]))
        tight = all(x <= scale / 10**25 for x in difference)
        records.append({
            "name": case.name,
            "oracle_exact": [str(x) for x in expected],
            "rust_d4_printed": [str(x) for x in observed],
            "count_error": [str(x) for x in difference],
            "pilot_tight": tight,
            "arithmetic_certified": False,
        })
    report = {
        "complete": True,
        "native_rust_d4_gate": "PASS" if all(x["pilot_tight"] for x in records) else "FAIL",
        "arithmetic_certified": False,
        "warning": "only exact printed-decimal oracle difference, not a GMP internal error bound",
        "cases": records,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(out), "native_rust_d4_gate": report["native_rust_d4_gate"]}))
    if report["native_rust_d4_gate"] != "PASS":
        raise SystemExit(2)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--cnf-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args=p.parse_args()
    evaluate(args.log, args.cnf_dir, args.out)


if __name__=="__main__":
    main()

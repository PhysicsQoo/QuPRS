#!/usr/bin/env python3
"""Classify original benchmark cases by real GPMC/Ganak native execve evidence.

This is a separate strace preflight, not included in timed measurements.
Cases without complete positive native invocation are excluded explicitly.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from validate_native_solver_actions import positive_check, sha256
from QuPRS.utils import WMC


CELLS = (("gpmc", "python"), ("ganak", "python"),
         ("ganak", "rust"), ("gpmc", "rust"))


def select_eligible(rows: list[dict], candidates: tuple[str, ...]) -> list[str]:
    selected = []
    for case in candidates:
        matching = [r for r in rows if r.get("case") == case]
        if (len(matching) == len(CELLS) and
                {(r.get("solver"), r.get("backend")) for r in matching} == set(CELLS) and
                all(r.get("status") == "PASS"
                    and r.get("native_execve") is True
                    and r.get("positive_equivalence") is True for r in matching)):
            selected.append(case)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--case", action="append", choices=("vqe4", "graphstate16"),
                        required=True)
    args = parser.parse_args()
    if len(set(args.case)) != len(args.case):
        parser.error("Duplicate case")
    if sys.platform != "linux":
        parser.error("Linux with strace is required")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("Evidence directory must be absent or empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "scope": "native-execve-preflight-not-timing",
        "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"],
            text=True).strip(),
        "candidates": args.case,
        "rows": [],
        "selected_cases": [],
    }
    try:
        for case in args.case:
            for solver, backend in CELLS:
                cell_dir = args.output_dir / case / solver / backend
                cell_dir.mkdir(parents=True)
                try:
                    with WMC(solver) as executable:
                        binary = Path(executable).resolve(strict=True)
                        row = positive_check(solver, backend, binary, cell_dir, case=case)
                except Exception as exc:
                    row = {
                        "case": case, "solver": solver, "backend": backend,
                        "status": "INCONCLUSIVE",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                results["rows"].append(row)
                print(json.dumps({
                    "case": case, "solver": solver, "backend": backend,
                    "status": row["status"],
                    "native_execve": row.get("native_execve"),
                    "positive_equivalence": row.get("positive_equivalence"),
                }, sort_keys=True), flush=True)
        results["selected_cases"] = select_eligible(results["rows"], tuple(args.case))
        results["status"] = ("COMPLETE" if results["selected_cases"]
                              else "INCONCLUSIVE")
        (args.output_dir / "selected-cases.txt").write_text(
            "".join(c + "\n" for c in results["selected_cases"])
        )
        (args.output_dir / "preflight-manifest.json").write_text(
            json.dumps(results, indent=2, sort_keys=True) + "\n"
        )
    finally:
        if not (args.output_dir / "preflight-manifest.json").is_file():
            (args.output_dir / "preflight-manifest.json").write_text(
                json.dumps(results, indent=2, sort_keys=True) + "\n"
            )
    return 0 if results["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())

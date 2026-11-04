"""Run actual QuPRS Python WMC facade through an explicit external d4 adapter.

Consumes SHA-pinned source CNFs from a previous Rust-emitted artifact; runs
the EXISTING Python SolverAdapter process supervisor. Never bundles a d4
binary or claims complete source-to-verdict scientific certification.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

from QuPRS.interface.ps2wmc import run_wmc
from QuPRS.utils.solver_adapter import get_solver_adapter, registered_solver_adapter
from d4_solver_adapter_poc import external_research_adapter
from poc_d4 import oracle_count


def pair(value):
    return [str(value[0]), str(value[1])]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(executable: Path, provenance: Path, inputs: list[Path], output: Path) -> None:
    if len(inputs) != 6 or len({x.resolve() for x in inputs}) != len(inputs):
        raise ValueError("expected six distinct SHA-pinned QuPRS source CNFs")
    adapter = external_research_adapter(executable, provenance)
    output.parent.mkdir(parents=True, exist_ok=True)
    results = []
    default_before = get_solver_adapter("gpmc").arguments
    try:
        with registered_solver_adapter(adapter):
            for input_file in inputs:
                content = input_file.read_text()
                exact = oracle_count(content)
                record = {
                    "source": input_file.name, "cnf_sha256": sha256(input_file),
                    "oracle_decimal_exact": pair(exact),
                    "solver": "d4-poc", "status": "PENDING",
                    "arithmetic_certified": False,
                }
                try:
                    count = run_wmc(
                        str(input_file), tool_name="d4-poc", timeout=30,
                        preserve_count=True,
                    )
                    observed = (count.real, count.imag)
                    difference = tuple(abs(a - b) for a, b in zip(exact, observed))
                    scale = max(Fraction(1), abs(exact[0]), abs(exact[1]))
                    record.update({
                        "observed_decimal_exact": pair(observed),
                        "error_components": pair(difference),
                        "printed_half_units": pair((
                            count.real_print_half_unit,
                            count.imag_print_half_unit,
                        )),
                        "output_dialect": count.format_name,
                        "status": (
                            "PILOT_TIGHT"
                            if all(delta <= scale / 10**25 for delta in difference)
                            else "PILOT_MISMATCH"
                        ),
                    })
                except Exception as exc:
                    record.update(status="NATIVE_ERROR", error=repr(exc)[:1200])
                results.append(record)
                output.write_text(json.dumps({
                    "complete": False, "precision_certified": False,
                    "d4_binary_sha256": sha256(executable),
                    "cases": results,
                }, indent=2) + "\n")
    finally:
        if get_solver_adapter("gpmc").arguments != default_before:
            raise RuntimeError("incumbent GPMC adapter changed by d4 PoC")
    success = all(item["status"] == "PILOT_TIGHT" for item in results)
    report = {
        "complete": True, "precision_certified": False,
        "d4_binary_sha256": sha256(executable),
        "adapter": "d4-poc",
        "native_python_wmc_facade_gate": "PASS" if success else "FAIL",
        "warning": "printed-only pilot does not bound d4 internal GMP error",
        "cases": results,
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "report": str(output), "cases": len(results),
        "native_python_wmc_facade_gate": report["native_python_wmc_facade_gate"],
    }))
    if not success:
        raise SystemExit(2)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", required=True, type=Path)
    p.add_argument("--provenance", required=True, type=Path)
    p.add_argument("--cnf", action="append", type=Path, default=[])
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    measure(a.binary.resolve(), a.provenance.resolve(),
            a.cnf, a.out.resolve())


if __name__ == "__main__":
    main()

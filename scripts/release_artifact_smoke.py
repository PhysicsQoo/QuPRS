#!/usr/bin/env python3
"""Fail-closed smoke of a clean installed QuPRS wheel or sdist.

Run from outside the repository so that sources do not shadow site-packages.
"""

from __future__ import annotations

import argparse
from importlib.metadata import distribution, version
from pathlib import Path
import json
import sys

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

import QuPRS
import QuPRS._pathsum_rust as native
from QuPRS import check_equivalence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-version", required=True)
    args = parser.parse_args()

    package = distribution("QuPRS")
    site = Path(package.locate_file("")).resolve()
    imported = Path(QuPRS.__file__).resolve()
    native_path = Path(native.__file__).resolve()
    expected = args.expected_version
    if not (QuPRS.__version__ == version("QuPRS") == expected):
        raise AssertionError(
            f"Version mismatch: runtime={QuPRS.__version__}, metadata={version('QuPRS')}, expected={expected}"
        )
    if not imported.is_relative_to(site) or not native_path.is_relative_to(site):
        raise AssertionError(f"Not an installed package: {imported}, {native_path}, site={site}")

    identity = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    hh.h(0)
    hh.h(0)
    phased = QuantumCircuit(1)
    phased.h(0)
    phased.h(0)
    phased.global_phase = 0.25
    inequivalent = QuantumCircuit(1)
    inequivalent.x(0)

    cases = [
        ("equivalent", hh, True),
        ("global_phase", phased, True),
        ("inequivalent", inequivalent, False),
    ]
    measurements = []
    for label, circuit, should_match in cases:
        oracle = Operator(identity).equiv(Operator(circuit))
        if oracle != should_match:
            raise AssertionError(f"Qiskit Operator oracle disagrees: {label} {oracle}")
        for solver in ("ganak", "gpmc"):
            for backend in ("python", "rust"):
                result = check_equivalence(
                    identity, circuit, method="wmc_only",
                    tool_name=solver, backend=backend, timeout=60,
                )
                valid = (
                    result.equivalent in {"equivalent", "equivalent*"}
                    if should_match else result.equivalent == "not_equivalent"
                )
                if not valid or result.tool_name != solver or result.tool_time is None:
                    raise AssertionError(
                        f"{label}: {solver}/{backend}, status={result.equivalent}, "
                        f"solver_used={result.tool_name}, tool_time={result.tool_time}"
                    )
                measurements.append({
                    "case": label, "backend": backend, "solver": solver,
                    "equivalent": result.equivalent, "tool_time": result.tool_time,
                })
    print(json.dumps({
        "version": expected, "python": sys.version.split()[0],
        "package": str(imported), "native": str(native_path),
        "checks": measurements,
    }, default=str, sort_keys=True))


if __name__ == "__main__":
    main()

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

    # PEP 561 typing data must exist in the installed wheel or sdist
    # (source-tree presence alone is not packaging evidence).
    typing_marker = imported.parent / "py.typed"
    pathsum_stub = imported.parent / "pathsum" / "core.pyi"
    if not typing_marker.is_file() or typing_marker.read_bytes():
        raise AssertionError(f"Installed QuPRS py.typed marker missing/invalid: {typing_marker}")
    if not pathsum_stub.is_file() or not pathsum_stub.resolve().is_relative_to(site):
        raise AssertionError(f"Installed PathSum typing stub missing: {pathsum_stub}")
    import ast
    stub = ast.parse(pathsum_stub.read_text(encoding="utf-8"), filename=str(pathsum_stub))
    core_classes = {
        node.name: node for node in stub.body if isinstance(node, ast.ClassDef)
    }
    for name in ("Register", "F", "PathSum"):
        if name not in core_classes:
            raise AssertionError(f"Installed typing stub is incomplete: {name}")
    static_gates = {
        node.name for node in core_classes["PathSum"].body
        if isinstance(node, ast.FunctionDef)
    }
    if not {"h", "cx", "rz", "mcx", "CRk", "reduction"}.issubset(static_gates):
        raise AssertionError("Installed typing stub omits representative PathSum methods")

    identity = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    hh.h(0)
    hh.h(0)
    phased = QuantumCircuit(1)
    # XZXZ = -I: a genuine gate-derived global phase that QASM2 preserves.
    for gate in ("x", "z", "x", "z"):
        getattr(phased, gate)(0)
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
    # Preserve the Rust QASM2 transport contract: unequal explicit scalar
    # phases cannot be serialized faithfully and must fail closed, even when
    # their operators are equal up to global phase.
    explicit_phase = QuantumCircuit(1)
    explicit_phase.global_phase = 0.25
    if not Operator(identity).equiv(Operator(explicit_phase)):
        raise AssertionError("Explicit scalar phase oracle unexpectedly disagrees")
    for solver in ("ganak", "gpmc"):
        try:
            check_equivalence(
                identity, explicit_phase, method="wmc_only",
                tool_name=solver, backend="rust", timeout=60,
            )
        except ValueError as exc:
            if "global_phase" not in str(exc):
                raise
        else:
            raise AssertionError(f"Rust QASM2 must reject unequal explicit scalar phases: {solver}")

    # Exercise the *installed archive's* private Python/Rust isolation
    # files. Source-tree editable installs can conceal packaging omissions.
    isolated_files = (
        "rust_isolation.py", "rust_supervisor.py", "rust_resources.py",
        "rust_worker_bootstrap.py", "rust_worker_standalone.py",
        "rust_macos_process.py",
    )
    interface_dir = imported.parent / "interface"
    for filename in isolated_files:
        helper = interface_dir / filename
        if not helper.is_file() or not helper.resolve().is_relative_to(site):
            raise AssertionError(f"Missing installed Rust Worker helper: {helper}")

    isolated_cases = (
        ("equivalent", identity, "equivalent"),
        ("inequivalent", inequivalent, "not_equivalent"),
    )
    for label, circuit, expected_status in isolated_cases:
        common = dict(
            backend="rust", method="reduction_rules", timeout=60,
        )
        direct = check_equivalence(identity, circuit, safe_mode=False, **common)
        isolated = check_equivalence(identity, circuit, safe_mode=True, **common)
        if (direct.equivalent != expected_status
                or isolated.equivalent != direct.equivalent):
            raise AssertionError(
                f"installed isolated Rust parity failed: {label}: "
                f"direct={direct.equivalent}, isolated={isolated.equivalent}"
            )
        measurements.append({
            "case": label, "backend": "rust_isolated",
            "equivalent": isolated.equivalent,
        })

    print(json.dumps({
        "version": expected, "python": sys.version.split()[0],
        "package": str(imported), "native": str(native_path),
        "checks": measurements,
    }, default=str, sort_keys=True))


if __name__ == "__main__":
    main()

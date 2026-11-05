#!/usr/bin/env python3
"""Source-pinned real Python API/cgroup admission witness for QOO-175.

Research-only: run within a transient systemd Delegate=memory unit, on a
trusted disposable CI runner. Never move or alter a shared host cgroup.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from QuPRS import check_equivalence


QASM = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
X_QASM = QASM + 'x q[0];\n'


def service_ancestor() -> Path:
    membership = Path("/proc/self/cgroup").read_text().splitlines()
    location = next((line[3:] for line in membership if line.startswith("0::")), "")
    if "/quprs-pilot" not in location:
        raise RuntimeError("API witness not running inside designated delegated unit")
    child = Path("/sys/fs/cgroup") / location.lstrip("/")
    parent = child.parent
    if parent.name == "system.slice" or not parent.name.startswith("qoo175-native-"):
        raise RuntimeError("API witness cannot prove private delegated membership")
    if "memory" not in (parent / "cgroup.subtree_control").read_text().split():
        raise RuntimeError("private service did not delegate memory controller")
    return parent


def snapshot_private_leaves(parent: Path) -> set[str]:
    return {p.name for p in parent.glob("quprs-py-*")}


def witness() -> dict:
    parent = service_ancestor()
    old_limit = os.environ.get("QUPRS_ISOLATED_MAX_MEMORY_MIB")
    before = snapshot_private_leaves(parent)
    # Use the same packaged PyO3/Rust implementation for both paths.
    cases = [
        ("identity", QASM, QASM, "equivalent"),
        ("x_negative", QASM, X_QASM, "not_equivalent"),
    ]
    observations = []
    try:
        os.environ.pop("QUPRS_ISOLATED_MAX_MEMORY_MIB", None)
        for name, a, b, expected in cases:
            direct = check_equivalence(
                a, b, backend="rust", safe_mode=False,
                method="reduction_rules", timeout=40,
            )
            if direct.equivalent != expected:
                raise AssertionError(
                    f"direct Rust verdict {name}: {direct.equivalent} != {expected}"
                )
            os.environ["QUPRS_ISOLATED_MAX_MEMORY_MIB"] = "512"
            isolated = check_equivalence(
                a, b, backend="rust", safe_mode=True,
                method="reduction_rules", timeout=40,
            )
            if isolated.equivalent != direct.equivalent:
                raise AssertionError(
                    f"isolated Rust verdict {name}: {isolated.equivalent} "
                    f"!= {direct.equivalent}"
                )
            if isolated.Statistics != direct.Statistics:
                raise AssertionError(f"reduction statistics differ in {name}")
            observations.append({
                "case": name,
                "direct": direct.equivalent,
                "isolated": isolated.equivalent,
                "cgroup_memory_max_mib": 512,
                "rr_statistics_parity": True,
            })
            # A successful call must not leave a private cgroup leaf behind.
            active = snapshot_private_leaves(parent)
            if active != before:
                raise AssertionError(
                    f"isolated call leaked private cgroup leaves: {sorted(active - before)}"
                )
    finally:
        if old_limit is None:
            os.environ.pop("QUPRS_ISOLATED_MAX_MEMORY_MIB", None)
        else:
            os.environ["QUPRS_ISOLATED_MAX_MEMORY_MIB"] = old_limit
    return {
        "status": "PASS",
        "scope": "real_Python_API_isolated_PyO3_under_delegated_cgroup",
        "cases": observations,
        "no_private_cgroup_leftovers": snapshot_private_leaves(parent) == before,
        "python_version": sys.version.split()[0],
    }


if __name__ == "__main__":
    try:
        print(json.dumps(witness(), sort_keys=True), flush=True)
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL", "scope": "real_Python_API_isolated_PyO3_under_delegated_cgroup",
            "error_type": type(exc).__name__, "reason": str(exc)[:600]
        }, sort_keys=True), flush=True)
        raise

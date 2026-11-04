"""Standalone, deliberately small CPython 3.14 binary + solver contract probe.

This is a diagnostic, not a replacement for v0.14.0's official CI matrix.
Runs against an installed source-built wheel; deliberately uses real GPMC/Ganak.
"""
import importlib.metadata as metadata
import json
import os
import sys
from pathlib import Path

import numpy as np
import qiskit
import symengine as se
import sympy as sp
from sympy.logic.boolalg import to_anf
from qiskit import QuantumCircuit, qasm2, qasm3
from QuPRS import _pathsum_rust, check_equivalence


QASM2 = "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\n"
# A post-parse scientific verdict near a deliberately relaxed projective
# distance boundary; neither category tests bit-for-bit real-number equality.
CASES = (
    ("gpmc", "wmc_only", "0.00032", "equivalent"),
    ("gpmc", "wmc_only", "0.00048", "not_equivalent"),
    ("ganak", "hybrid", "0.00048", "not_equivalent"),
)


def run():
    assert sys.version_info[:2] == (3, 14), sys.version
    versions = {name: metadata.version(name) for name in
                ("QuPRS", "qiskit", "qiskit-qasm3-import",
                 "numpy", "symengine", "sympy", "psutil", "pytest")}
    assert versions["qiskit"] == os.environ["EXPECTED_QISKIT"], versions
    assert _pathsum_rust.__file__, "Rust native extension must actually be loaded"

    # Test real SymEngine symbolic operations, not only import/wheel metadata.
    x, y = se.symbols("x y")
    assert se.expand((x + y)**2 - x*x - 2*x*y - y*y) == 0
    assert to_anf(sp.Xor(sp.Symbol("x"), sp.Symbol("y"))) == sp.Xor(
        sp.Symbol("x"), sp.Symbol("y")
    )

    c2 = qasm2.loads(QASM2 + "h q[0];\nh q[0];\n")
    assert isinstance(c2, QuantumCircuit)
    c3 = qasm3.loads('OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit q;\nh q;\nh q;\n')
    assert isinstance(c3, QuantumCircuit)
    checks = []
    identity = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    hh.h(0)
    hh.h(0)
    for backend in ("python", "rust"):
        v = check_equivalence(identity, hh, backend=backend,
                              method="reduction_rules", strategy="Naive",
                              timeout=30)
        assert v.equivalent == "equivalent", (backend, v)
        checks.append(dict(backend=backend, method="reduction_rules",
                           expected="equivalent", observed=v.equivalent))
        for solver, method, theta, expected in CASES:
            v = check_equivalence(QASM2, QASM2 + f"rz({theta}) q[0];\n",
                                  backend=backend, method=method,
                                  strategy="Naive", tool_name=solver,
                                  approximate_distance_tolerance=2e-4,
                                  timeout=45)
            assert v.equivalent == expected, (
                backend, solver, method, theta, expected, v.equivalent,
                getattr(v, "wmc_precision_reason", None),
            )
            assert v.wmc_solver_invoked is True, (backend, solver, method)
            checks.append(dict(backend=backend, solver=solver, method=method,
                               theta=theta, expected=expected,
                               observed=v.equivalent,
                               solver_invoked=v.wmc_solver_invoked))
    # Python 3.14 changes the POSIX default process context; QuPRS explicitly
    # uses spawn. Confirm a real public safe_mode invocation still works.
    safe = check_equivalence(identity, hh, backend="python",
                             method="reduction_rules", strategy="Naive",
                             safe_mode=True, timeout=30)
    assert safe.equivalent == "equivalent", safe
    checks.append(dict(backend="python", method="reduction_rules",
                       safe_mode=True, observed=safe.equivalent))
    evidence = dict(python=sys.version, package_versions=versions,
                    ffi_path=str(Path(_pathsum_rust.__file__).resolve()),
                    checks=checks, status="PASS")
    Path("evidence").mkdir(exist_ok=True)
    Path("evidence/probe.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()

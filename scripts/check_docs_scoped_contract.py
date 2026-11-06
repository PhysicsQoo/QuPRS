#!/usr/bin/env python3
"""Small independent documentation witnesses and source-backed API contracts.

No solver subprocess, external native build, or package import is required by
the default static check. --runtime is used only after an existing native
source build has been installed by the Documentation Examples workflow.
"""
from __future__ import annotations

import argparse
import ast
import cmath
from math import pi, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH_DOC = ROOT / "docs/site/path-sum.md"
SOLVER_DOC = ROOT / "docs/site/weighted-model-counting.md"
ADAPTER = ROOT / "src/QuPRS/utils/solver_adapter.py"
PROBLEM = ROOT / "src/QuPRS/utils/wmc_problem.py"


def classes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {item.name: item for item in tree.body if isinstance(item, ast.ClassDef)}


def static_contract() -> None:
    """Reject removed public explanations or implementation-field mismatches."""
    path = PATH_DOC.read_text(encoding="utf-8")
    solver = SOLVER_DOC.read_text(encoding="utf-8")
    for token in ("Hand-checkable applicability and counterexamples",
                  "P=y₀/2", "Q=3", "y₀/3"):
        if token not in path:
            raise AssertionError(f"Rule witness missing: {token}")
    for token in ("Implemented adapter boundary versus future extensions",
                  "SolverCapabilities", "SolverResult", "WmcProblem",
                  "WmcWeight", "registered_solver_adapter", "SolverTimeout",
                  "exact_count_certificate=False"):
        if token not in solver:
            raise AssertionError(f"Adapter contract missing: {token}")

    declared = {
        "SolverCapabilities": {"weight_format", "complex_weights", "exact_count_certificate"},
        "SolverResult": {"solver_id", "count", "arguments", "returncode", "elapsed_seconds"},
        "SolverAdapter": {"solver_id", "arguments", "capabilities", "resource_factory"},
        "WmcWeight": {"variable", "real", "imag"},
        "WmcProblem": {"variables", "clauses", "weights"},
    }
    sc, wc = classes(ADAPTER), classes(PROBLEM)
    for name, expected in declared.items():
        cls = (sc if name in sc else wc).get(name)
        if cls is None:
            raise AssertionError(f"Missing documented source class: {name}")
        fields = {stmt.target.id for stmt in cls.body
                  if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)}
        if fields != expected:
            raise AssertionError(f"Documented fields drifted: {name}: {fields}")
    functions = {node.name for node in ast.parse(ADAPTER.read_text(encoding="utf-8")).body
                 if isinstance(node, ast.FunctionDef)}
    if not {"get_solver_adapter", "registered_solver_adapter",
            "execute_solver"}.issubset(functions):
        raise AssertionError("Documented selected solver transport missing")

    # Elim: y-dependent source phase or output cannot be replaced by twice a term.
    if abs(sum(cmath.exp(2j * pi * y / 2) for y in (0, 1))) > 1e-12:
        raise AssertionError("Invalid Elim scalar negative control")
    if (1 + 0j, 1 + 0j) == (2 + 0j, 0j):
        raise AssertionError("Invalid Elim output-ket negative control")
    # HH: Q=3, y1=0 cancels as a scalar, but leaves |0>-|1>
    # when the output depends on the supposedly eliminated y0.
    hh_vector = tuple(cmath.exp(2j * pi * y * 3 / 2) for y in (0, 1))
    if abs(hh_vector[0] - 1) > 1e-12 or abs(hh_vector[1] + 1) > 1e-12:
        raise AssertionError("Invalid HH output-ket negative control")
    # Omega: y0/3 is not a quarter-cycle coefficient.
    omega_wrong = sum(cmath.exp(2j * pi * y / 3) for y in (0, 1))
    if abs(abs(omega_wrong) - 1) > 1e-12 or abs(abs(omega_wrong) - sqrt(2)) < 1e-8:
        raise AssertionError("Invalid Omega coefficient negative control")


def runtime_contract() -> None:
    """Actual Python matcher and solver-neutral IR, without a solver process."""
    import symengine as se
    from QuPRS.pathsum.pattern_match import match_Elim, match_HH, match_omega
    from QuPRS.utils.solver_adapter import get_solver_adapter
    from QuPRS.utils.verification_tolerances import scoped_rr_tolerance
    from QuPRS.utils.wmc_problem import WmcProblem, WmcWeight

    y0, y1 = se.symbols("docs_yo docs_yi")
    with scoped_rr_tolerance(0):
        if match_Elim(se.Rational(1, 8), (y0,)) != y0:
            raise AssertionError("Actual Elim matcher rejected unused variable")
        if match_Elim(y0 / 2, (y0,)) is not None:
            raise AssertionError("Actual Elim ignored phase dependence")
        if match_Elim(se.Rational(1, 8), ()) is not None:
            raise AssertionError("Actual Elim ignored output eligibility")
        if match_HH(y0 * y1 / 2, (y0,), (y0, y1), ())[:2] != (y0, y1):
            raise AssertionError("Actual HH matcher rejected cross term")
        if match_HH(y0 / 3, (y0,), (y0, y1), ())[0] is not None:
            raise AssertionError("Actual HH accepted third-cycle coefficient")
        om = match_omega(y0 * (se.Rational(1, 4) + y1),
                         (y0,), (y0, y1), ())
        if om[0] != y0 or not om[3]:
            raise AssertionError("Actual Omega rejected quarter-cycle fixture")
        if match_omega(y0 / 3, (y0,), (y0, y1), ())[0] is not None:
            raise AssertionError("Actual Omega accepted third-cycle coefficient")

    gpmc, ganak = get_solver_adapter("gpmc"), get_solver_adapter("ganak")
    if (gpmc.capabilities.weight_format, ganak.capabilities.weight_format) != ("pair", "complex-i"):
        raise AssertionError("Documented complex weight grammar disagrees with adapters")
    if gpmc.capabilities.exact_count_certificate or ganak.capabilities.exact_count_certificate:
        raise AssertionError("Printed counts must not imply exact certification")
    weight_text = WmcProblem(1, ((1,),), (WmcWeight(1, 1, -1),)).serialize(gpmc)
    if "c p weight -1 1.0 0.0 0" not in weight_text:
        raise AssertionError("Negative literal weight changed")
    try:
        get_solver_adapter("not-a-built-in-solver")
    except ValueError:
        pass
    else:
        raise AssertionError("Unregistered solver incorrectly selected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", action="store_true",
                        help="Also check installed Python matcher and adapter contracts")
    options = parser.parse_args()
    static_contract()
    if options.runtime:
        runtime_contract()
    print("Public rule and adapter documentation contracts: PASS")

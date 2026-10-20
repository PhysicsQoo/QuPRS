#!/usr/bin/env python3
"""Read-only, attempt-scoped probe for Omega -> HH coefficient reuse.

This is an isolated diagnostic: coeff() is ALWAYS called. No memoization, no
production source patches and no cross-reduction cache. Counts refer to the
same expanded phase and same variable *in a single apply_reduction attempt*.
"""
import argparse
import ast
from collections import defaultdict
import functools
import inspect
import json
from pathlib import Path
import platform
import sys
import textwrap
import time

CASES = {
    "qaoa7": ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", False),
    "grover4": ("grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", True),
}
COUNTS = defaultdict(lambda: {"calls": 0, "time_ns": 0})
ATTEMPTS = {"total": 0, "omega_then_hh": 0, "phase_mismatches": 0}
STACK = []
OVERLAP = {"hits": 0, "misses": 0, "same_value": 0, "different_value": 0,
           "hit_hh_coefficient_time_ns": 0}


def observed_coeff(stage, poly, variable):
    start = time.perf_counter_ns()
    result = poly.coeff(variable)  # Real call. Deliberately no caching.
    elapsed = time.perf_counter_ns() - start
    rec = COUNTS[stage]
    rec["calls"] += 1
    rec["time_ns"] += elapsed

    if not STACK:
        raise AssertionError("coeff observed outside an apply_reduction attempt")
    scope = STACK[-1]
    if stage == "omega":
        scope["omega_coefficients"][variable] = result
    elif stage == "hh":
        if variable not in scope["omega_coefficients"]:
            OVERLAP["misses"] += 1
        else:
            OVERLAP["hits"] += 1
            OVERLAP["hit_hh_coefficient_time_ns"] += elapsed
            if result == scope["omega_coefficients"][variable]:
                OVERLAP["same_value"] += 1
            else:
                OVERLAP["different_value"] += 1
    return result


class ReplaceCoeff(ast.NodeTransformer):
    def __init__(self, stage):
        self.stage = stage
        self.replacements = 0

    def visit_Call(self, node):
        self.generic_visit(node)
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == "coeff"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "P_expanded"):
            self.replacements += 1
            return ast.copy_location(ast.Call(
                func=ast.Name(id="_qoo112_coeff", ctx=ast.Load()),
                args=[ast.Constant(self.stage), node.func.value, *node.args],
                keywords=node.keywords), node)
        return node


def compiled_matcher(func, stage):
    source = textwrap.dedent(inspect.getsource(func))
    patch = ReplaceCoeff(stage)
    tree = patch.visit(ast.parse(source))
    if patch.replacements != 1:
        raise AssertionError("Expected exactly one P_expanded.coeff in " + func.__name__)
    ast.fix_missing_locations(tree)
    namespace = {}
    func.__globals__["_qoo112_coeff"] = observed_coeff
    exec(compile(tree, inspect.getsourcefile(func) or "<qoo112>", "exec"),
         func.__globals__, namespace)
    return namespace[func.__name__]


def install_readonly_probe():
    import QuPRS.pathsum.reduction as red
    import QuPRS.pathsum.pattern_match as match

    for stage, name in (("omega", "match_omega"), ("hh", "match_HH")):
        fn = compiled_matcher(getattr(match, name), stage)

        @functools.wraps(fn)
        def matcher_with_scope(*args, _fn=fn, _stage=stage, **kwargs):
            if not STACK:
                raise AssertionError("Matcher called without a reduction scope")
            scope = STACK[-1]
            phase = id(args[0])
            if _stage == "omega":
                scope["omega_phase_id"] = phase
            else:
                if scope["omega_phase_id"] != phase:
                    ATTEMPTS["phase_mismatches"] += 1
                else:
                    ATTEMPTS["omega_then_hh"] += 1
            return _fn(*args, **kwargs)

        setattr(match, name, matcher_with_scope)
        setattr(red, name, matcher_with_scope)

    original = red.apply_reduction

    @functools.wraps(original)
    def with_attempt_scope(*args, **kwargs):
        ATTEMPTS["total"] += 1
        STACK.append({"omega_coefficients": {}, "omega_phase_id": None})
        try:
            return original(*args, **kwargs)
        finally:
            STACK.pop()
    red.apply_reduction = with_attempt_scope


def independent_operator_status(left, right):
    import numpy as np
    from qiskit.quantum_info import Operator
    a, b = Operator(left), Operator(right)
    if np.allclose(a.data, b.data, atol=1e-10, rtol=0):
        return "equivalent"
    if a.equiv(b, atol=1e-10, rtol=0):
        return "equivalent*"
    return "not_equivalent"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=sorted(CASES), required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    from qiskit import qasm2
    from QuPRS import check_equivalence
    filename, swap = CASES[args.case]
    lhs = args.case_root / filename
    rhs = args.case_root / "h,ry,rz,cx" / filename
    if swap:
        lhs, rhs = rhs, lhs
    a, b = qasm2.load(str(lhs)), qasm2.load(str(rhs))
    oracle = independent_operator_status(a, b)
    if args.probe:
        install_readonly_probe()
    start = time.perf_counter()
    res = check_equivalence(a, b, backend="python", tool_name="gpmc",
                            method="hybrid", strategy="Proportional",
                            timeout=args.timeout)
    duration = time.perf_counter() - start
    counts = {name: dict(value) for name, value in COUNTS.items()}
    data = {
        "schema": 1, "case": args.case, "probe": args.probe,
        "backend": "python", "solver": "gpmc",
        "method": "hybrid", "strategy": "Proportional",
        "status": res.equivalent, "operator_oracle": oracle,
        "elapsed_seconds": duration,
        "qasm_paths": [str(lhs), str(rhs)],
        "counts": counts, "attempts": dict(ATTEMPTS),
        "overlap": dict(OVERLAP), "python": platform.python_version(),
        "quprs_location": str(sys.modules["QuPRS"].__file__),
        "comments": "No coeff result was reused; this profile records an upper bound.",
    }
    print(json.dumps(data, sort_keys=True), flush=True)
    if res.equivalent not in ("equivalent", "equivalent*"):
        raise SystemExit("Incomplete or unexpected verification classification")
    if res.equivalent != oracle:
        raise SystemExit("Independent Operator semantic oracle mismatch")
    if args.probe:
        if STACK or ATTEMPTS["phase_mismatches"] or OVERLAP["different_value"]:
            raise SystemExit("Invalid coefficient alias/phase semantics")
        if not COUNTS["omega"]["calls"] or not COUNTS["hh"]["calls"]:
            raise SystemExit("Did not observe both matcher coefficient sites")
        if OVERLAP["hits"] + OVERLAP["misses"] != COUNTS["hh"]["calls"]:
            raise SystemExit("Overlap counter does not cover HH calls")


if __name__ == "__main__":
    main()

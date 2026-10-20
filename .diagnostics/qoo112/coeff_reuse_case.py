#!/usr/bin/env python3
"""Isolated source-pinned Python circuit verification and phase operation probe.

Invoked as a new Python process for every observation. --probe instruments
expand/coeff only at Python source call sites, not native SymEngine methods
globally. Timed check_equivalence excludes QASM parsing and optional Operator.
"""
import argparse
import ast
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
STAGES = {}


def clock_call(label, expr, operation, *args, **kwargs):
    started = time.perf_counter_ns()
    try:
        return getattr(expr, operation)(*args, **kwargs)
    finally:
        record = STAGES.setdefault(label, {"calls": 0, "total_ns": 0})
        record["calls"] += 1
        record["total_ns"] += time.perf_counter_ns() - started


class Probe(ast.NodeTransformer):
    def __init__(self, name):
        self.name = name

    def visit_Call(self, node):
        self.generic_visit(node)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in ("expand", "coeff")
            and not node.keywords
        ):
            return ast.copy_location(
                ast.Call(
                    func=ast.Name(id="_qoo112_clock_call", ctx=ast.Load()),
                    args=[
                        ast.Constant(self.name + "." + node.func.attr),
                        node.func.value,
                        ast.Constant(node.func.attr),
                        *node.args,
                    ],
                    keywords=[],
                ),
                node,
            )
        return node


def patch_func(module, name):
    fn = getattr(module, name)
    source = textwrap.dedent(inspect.getsource(fn))
    tree = Probe(name).visit(ast.parse(source))
    ast.fix_missing_locations(tree)
    module.__dict__["_qoo112_clock_call"] = clock_call
    namespace = {}
    exec(compile(tree, inspect.getsourcefile(fn) or "<qoo112>", "exec"),
         module.__dict__, namespace)
    setattr(module, name, namespace[name])


def install_probe():
    import QuPRS.pathsum.pattern_match as match
    import QuPRS.pathsum.reduction as red

    for name in ("match_HH", "match_omega"):
        patch_func(match, name)
        setattr(red, name, getattr(match, name))
    patch_func(red, "apply_reduction")


def operator_status(a, b):
    import numpy as np
    from qiskit.quantum_info import Operator
    aa, bb = Operator(a), Operator(b)
    if np.allclose(aa.data, bb.data, atol=1e-9, rtol=0):
        return "equivalent"
    if aa.equiv(bb, atol=1e-9, rtol=0):
        return "equivalent*"
    return "not_equivalent"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=sorted(CASES), required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--solver", default="gpmc", choices=("gpmc", "ganak"))
    parser.add_argument("--variant", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--oracle", action="store_true")
    args = parser.parse_args()

    from qiskit import qasm2
    from QuPRS import check_equivalence, __version__
    filename, switch = CASES[args.case]
    lhs = args.case_root / filename
    rhs = args.case_root / "h,ry,rz,cx" / filename
    if switch:
        lhs, rhs = rhs, lhs
    a, b = qasm2.load(str(lhs)), qasm2.load(str(rhs))
    oracle = operator_status(a, b) if args.oracle else None

    if args.probe:
        install_probe()
    start = time.perf_counter()
    r = check_equivalence(a, b, method="hybrid", strategy="Proportional",
                          tool_name=args.solver, backend="python", timeout=args.timeout)
    elapsed = time.perf_counter() - start
    status = r.equivalent
    output = {
        "case": args.case, "variant": args.variant, "profile": args.probe,
        "backend": "python", "solver": args.solver, "method": "hybrid",
        "strategy": "Proportional", "status": status,
        "oracle": oracle, "elapsed_seconds": elapsed, "stage_operations": STAGES,
        "paths": [str(lhs), str(rhs)], "gate_counts": [len(a.data), len(b.data)],
        "python": platform.python_version(), "quprs": __version__,
        "quprs_module_path": sys.modules["QuPRS"].__file__,
    }
    print(json.dumps(output, sort_keys=True, default=str), flush=True)
    if status not in ("equivalent", "equivalent*"):
        raise SystemExit(2)
    if oracle is not None and status != oracle:
        raise SystemExit(3)


if __name__ == "__main__":
    main()

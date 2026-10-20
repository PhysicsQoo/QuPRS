#!/usr/bin/env python3
"""Opt-in, no-production-change Python Reduction attribution.

Run from an installed QuPRS checkout with Qiskit, SymEngine and real solvers.
Exclusive time subtracts instrumented child spans; this is NOT a zero-overhead timer.
"""
import argparse
import ast
import collections
import contextlib
import functools
import inspect
import json
from pathlib import Path
import time
import textwrap

import QuPRS.pathsum.reduction as red
import QuPRS.pathsum.pattern_match as match

COUNTERS = collections.defaultdict(lambda: {"calls": 0, "inclusive_ns": 0, "exclusive_ns": 0})
STACK = []
DEPTH = {"current": 0, "max": 0, "calls": 0}


def wrapped(name, func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        start = time.perf_counter_ns()
        frame = [name, start, 0]
        STACK.append(frame)
        if name == "apply_reduction" or name == "reduction_apply_reduction":
            DEPTH["current"] += 1
            DEPTH["calls"] += 1
            DEPTH["max"] = max(DEPTH["max"], DEPTH["current"])
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter_ns() - start
            _, _, children = STACK.pop()
            rec = COUNTERS[name]
            rec["calls"] += 1
            rec["inclusive_ns"] += elapsed
            rec["exclusive_ns"] += max(0, elapsed - children)
            if STACK:
                STACK[-1][2] += elapsed
            if name == "apply_reduction" or name == "reduction_apply_reduction":
                DEPTH["current"] -= 1
    return inner


def timed_free_symbols(category, expression):
    """Time a real property access, leaving native SymEngine types unchanged."""
    return wrapped("free_symbols." + category, lambda: expression.free_symbols)()


class FreeSymbolsProbe(ast.NodeTransformer):
    """Instrument only actual free_symbols attribute reads in an isolated function."""
    def __init__(self, category):
        self.category = category

    def visit_Attribute(self, node):
        self.generic_visit(node)
        if node.attr != "free_symbols" or not isinstance(node.ctx, ast.Load):
            return node
        call = ast.Call(
            func=ast.Name(id="_qoo112_timed_symbols", ctx=ast.Load()),
            args=[ast.Constant(self.category), node.value],
            keywords=[],
        )
        return ast.copy_location(call, node)


def probe_function(func, category):
    """Recompile one known Python function with identical expressions plus timers.

    Run only inside this opt-in diagnostic. Do not change package source files,
    attempt to patch immutable SymEngine classes, or cache free_symbols values.
    """
    source = textwrap.dedent(inspect.getsource(func))
    tree = FreeSymbolsProbe(category).visit(ast.parse(source))
    ast.fix_missing_locations(tree)
    namespace = {}
    exec(
        compile(tree, inspect.getsourcefile(func) or "<qoo112>", "exec"),
        func.__globals__, namespace,
    )
    return namespace[func.__name__]


@contextlib.contextmanager
def instrument():
    targets = [
        (red, "apply_reduction"),
        (red, "reduce_expression"),
        (red, "match_Elim"),
        (red, "match_HH"),
        (red, "match_omega"),
        (red, "HH_reduction"),
        (red, "omega_reduction"),
        (match, "reduce_expression"),
    ]
    originals = [(module, attr, getattr(module, attr)) for module, attr in targets]
    sentinel = object()
    hook_globals = [red.__dict__, match.__dict__]
    old_hooks = [(g, g.get("_qoo112_timed_symbols", sentinel)) for g in hook_globals]
    free_symbols_functions = {
        "apply_reduction": "output",
        "match_Elim": "phase",
        "match_HH": "match_HH",
        "match_omega": "match_omega",
        "HH_reduction": "HH_reduction",
        "omega_reduction": "omega_reduction",
    }
    try:
        for g in hook_globals:
            g["_qoo112_timed_symbols"] = timed_free_symbols
        for module, attr, func in originals:
            if attr in free_symbols_functions:
                # Function globals are its original module; read symbols there.
                func = probe_function(func, free_symbols_functions[attr])
            label = ("pattern_" if module is match else "reduction_") + attr
            setattr(module, attr, wrapped(label, func))
        yield
    finally:
        for module, attr, func in reversed(originals):
            setattr(module, attr, func)
        for g, original in old_hooks:
            if original is sentinel:
                g.pop("_qoo112_timed_symbols", None)
            else:
                g["_qoo112_timed_symbols"] = original


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--cases", nargs="+", default=["qft16", "qaoa7", "grover4"])
    parser.add_argument("--solver", choices=["ganak", "gpmc"], default="gpmc")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--profile", action="store_true", help="Enable function timers; default measures uninstrumented baseline")
    args = parser.parse_args()
    from qiskit import qasm2
    from QuPRS import check_equivalence

    filenames = {
        "qft16": "qft_nativegates_ibm_qiskit_opt0_16.qasm",
        "qaoa7": "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
        "grover4": "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cases = []
    with (instrument() if args.profile else contextlib.nullcontext()):
        for case in args.cases:
            COUNTERS.clear()
            DEPTH.update(current=0, max=0, calls=0)
            if case not in filenames:
                raise ValueError(f"Unsupported benchmark: {case}")
            filename = filenames[case]
            left = args.case_root / filename
            right = args.case_root / "h,ry,rz,cx" / filename
            if not left.is_file() or not right.is_file():
                raise FileNotFoundError(f"Missing exact pair: {left}, {right}")
            a, b = qasm2.load(str(left)), qasm2.load(str(right))
            start = time.perf_counter()
            result = check_equivalence(
                a, b, method="hybrid", strategy="Proportional",
                tool_name=args.solver, backend="python", timeout=args.timeout
            )
            elapsed = time.perf_counter() - start
            status = result.equivalent
            cases.append({"case": case, "status": status, "elapsed_seconds": elapsed,
                          "timings": {key: dict(value) for key, value in COUNTERS.items()},
                          "recursion": dict(DEPTH)})
            print(case, status, f"{elapsed:.3f}s", flush=True)
    payload = {
        "schema": 1, "backend": "python", "solver": args.solver, "instrumented": args.profile,
        "cases": cases,
        "notes": [
            "Exclusive timers subtract instrumented child spans only.",
            "Real free_symbols attribute reads are timed through opt-in AST call-site probes.",
            "No cache, algorithm, threshold or solver behavior changed.",
            "The profiler adds overhead: compare an uninstrumented matched run."
        ],
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print("PROFILE_JSON", args.output)


if __name__ == "__main__":
    main()

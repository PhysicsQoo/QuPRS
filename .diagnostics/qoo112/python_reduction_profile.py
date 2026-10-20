#!/usr/bin/env python3
"""Opt-in, no-production-change Python Reduction attribution.

Run from an installed QuPRS checkout with Qiskit, SymEngine and real solvers.
Exclusive time subtracts instrumented child spans; this is NOT a zero-overhead timer.
"""
import argparse
import collections
import contextlib
import functools
import json
import os
from pathlib import Path
import statistics
import time

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
        if name == "apply_reduction":
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
            if name == "apply_reduction":
                DEPTH["current"] -= 1
    return inner


@contextlib.contextmanager
def instrument():
    targets = [
        (red, "apply_reduction"),
        (red, "reduce_expression"),
        (red, "match_Elim"),
        (red, "match_HH"),
        (red, "match_omega"),
        (match, "reduce_expression"),
    ]
    originals = [(module, attr, getattr(module, attr)) for module, attr in targets]
    # Wrap the free_symbols getter on SymEngine types only if its descriptor is writable.
    # This is deliberately NOT attempted: native extension types are often immutable.
    # Instead attribute its cost as an explicit stage in a separately measured diagnostic.
    try:
        for module, attr, func in originals:
            label = ("pattern_" if module is match else "reduction_") + attr
            setattr(module, attr, wrapped(label, func))
        yield
    finally:
        for module, attr, func in reversed(originals):
            setattr(module, attr, func)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--cases", nargs="+", default=["qft16", "qaoa7", "grover4"])
    parser.add_argument("--solver", choices=["ganak", "gpmc"], default="gpmc")
    parser.add_argument("--timeout", type=int, default=200)
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
    with instrument():
        for case in args.cases:
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
            cases.append({"case": case, "status": status, "elapsed_seconds": elapsed})
            print(case, status, f"{elapsed:.3f}s", flush=True)
    payload = {
        "schema": 1, "backend": "python", "solver": args.solver,
        "cases": cases, "recursion": DEPTH,
        "timings": dict(COUNTERS),
        "notes": [
            "Exclusive timers subtract instrumented child spans only.",
            "Python and SymEngine free_symbols are not independently timed by this version.",
            "No cache, algorithm, threshold or solver behavior changed.",
            "The profiler adds overhead: compare an uninstrumented matched run."
        ],
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print("PROFILE_JSON", args.output)


if __name__ == "__main__":
    main()

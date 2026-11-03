#!/usr/bin/env python3
"""Opt-in exclusive stage ledger: source-pinned, no production code changes.

This probe times actual Python boundary calls, including recursive reductions,
on one explicitly selected circuit and backend per isolated process. Native
Rust only exposes coarse *disjoint* stages; nested published timers remain
descriptive metadata and are never added to the ledger.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
from collections import defaultdict

SCHEMA = "quprs-exclusive-stage-ledger-v0"


def check_partition(total_seconds, components, *, tolerance_seconds=0.001):
    """Return disjoint ledger with explicit residual; reject overlap/negatives."""
    if total_seconds < 0 or not isinstance(total_seconds, (int, float)):
        raise ValueError("Invalid top-level monotonic walltime")
    parts = dict(components)
    if any(not isinstance(v, (int, float)) or v < 0 for v in parts.values()):
        raise ValueError("Invalid negative/non-numeric stage duration")
    total_assigned = sum(parts.values())
    residual = total_seconds - total_assigned
    if residual < -tolerance_seconds:
        raise AssertionError(
            "Overlapping stage intervals: assigned %.9f > total %.9f"
            % (total_assigned, total_seconds)
        )
    # Floating-point residuals within 1 ms are kept rather than silently
    # reclassified: instrumenting wrapper boundaries can add tiny overhead.
    parts["other_unattributed"] = residual
    return {
        "measured_wall_seconds": total_seconds,
        "exclusive_seconds": parts,
        "closure_error_seconds": total_seconds - sum(parts.values()),
        "unattributed_warning": residual < 0,
    }


class PythonProbe:
    """Temporary, in-process function wrappers. No global native type patches."""

    def __init__(self):
        self.durations_ns = defaultdict(int)
        self.calls = defaultdict(int)
        self.reduction_depth = 0
        self.reduction_max_depth = 0

    def wrap(self, label, fn, *, root_reduction=False):
        def timed(*args, **kwargs):
            if root_reduction:
                self.reduction_depth += 1
                self.reduction_max_depth = max(self.reduction_max_depth, self.reduction_depth)
            start = time.perf_counter_ns()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed = time.perf_counter_ns() - start
                self.calls[label] += 1
                if not root_reduction or self.reduction_depth == 1:
                    self.durations_ns[label] += elapsed
                if root_reduction:
                    self.reduction_depth -= 1
        return timed

    @contextlib.contextmanager
    def installed(self):
        from QuPRS.interface import load_qiskit as interface
        import QuPRS.pathsum.reduction as reduction
        import QuPRS.interface.ps2wmc as ps2wmc
        import QuPRS.utils.solver_process as solver_process
        import QuPRS.utils.precision_count as precision_count
        from QuPRS.utils.strategy import Strategy

        original_get = Strategy.get
        saved = []

        def patch(module, name, label, root_reduction=False):
            original = getattr(module, name)
            saved.append((module, name, original))
            setattr(module, name, self.wrap(label, original, root_reduction=root_reduction))

        @classmethod
        def traced_get(cls, name):
            instance = original_get(name)
            instance.run = self.wrap("strategy_total", instance.run)
            # Only normal, same-process operation is used; safe_run forks and
            # is explicitly outside the source-level Python attribution scope.
            return instance

        try:
            for name in ("load_circuit", "initialize", "get_gates"):
                patch(interface, name, "setup_" + name)
            patch(reduction, "apply_reduction", "reduction_roots", root_reduction=True)
            patch(ps2wmc, "to_DIMACS", "cnf_encode_and_write")
            patch(ps2wmc, "run_wmc", "wmc_dispatch_and_parse")
            patch(solver_process, "run", "solver_supervision")
            patch(precision_count, "classify_observed_distance", "wmc_classification")
            saved.append((Strategy, "get", Strategy.__dict__["get"]))
            Strategy.get = traced_get
            yield
        finally:
            for module, name, original in reversed(saved):
                setattr(module, name, original)
            if self.reduction_depth != 0:
                raise AssertionError("Unbalanced Reduction recursion profiling stack")

    def exclusive_ledger(self, wall_seconds):
        def sec(key):
            return self.durations_ns[key] / 1e9
        strategy = sec("strategy_total")
        reduction = sec("reduction_roots")
        dispatch = sec("wmc_dispatch_and_parse")
        supervise = sec("solver_supervision")
        if reduction - strategy > 0.001:
            raise AssertionError("Reduction roots exceed strategy time")
        if supervise - dispatch > 0.001:
            raise AssertionError("Solver subprocess exceeds WMC dispatch time")
        stages = {
            "setup_parse": (
                sec("setup_load_circuit") + sec("setup_initialize")
                + sec("setup_get_gates")
            ),
            "gate_processing_except_reduction": max(0.0, strategy - reduction),
            "reduction": reduction,
            "cnf_encode_serialize": sec("cnf_encode_and_write"),
            "solver_spawn_wait_output": supervise,
            "solver_control_resolution_output_parse": max(0.0, dispatch - supervise),
            "wmc_classification": sec("wmc_classification"),
        }
        ledger = check_partition(wall_seconds, stages)
        ledger["boundary_calls"] = dict(self.calls)
        ledger["reduction_max_depth"] = self.reduction_max_depth
        ledger["method_note"] = (
            "Exclusive non-overlap is enforced at measured Python wrapper boundaries; "
            "gate stage includes Strategy excluding recursively counted Reduction; "
            "run_wmc is split into supervised process and the residual lock, "
            "binary discovery, parsing and other control overhead. Setup includes "
            "only explicitly observed load/init/get_gates calls; remaining "
            "API/setup/classification/cleanup time stays Other."
        )
        ledger["fine_grained_missing"] = [
            "CNF encoding vs serialization individually",
            "solver CPU duration distinct from process supervision",
            "gate expansion separate from other Strategy work",
        ]
        return ledger


def circuit_pair(case, root):
    from qiskit import QuantumCircuit, qasm2
    if case == "qaoa7":
        name = "qaoa_nativegates_ibm_qiskit_opt0_7.qasm"
        left_path = root / name
        right_path = root / "h,ry,rz,cx" / name
        left, right = qasm2.load(str(left_path)), qasm2.load(str(right_path))
        evidence = {
            "qasm_paths": [str(left_path), str(right_path)],
            "qasm_sha256": [hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (left_path, right_path)],
        }
        return left, right, evidence
    if case == "ghz4_wmc_only":
        # A deterministic, small GHZ pair. Distinct circuit structures, equal
        # unitary matrices: Z^2 acts as identity. WMC-only must call GPMC.
        left = QuantumCircuit(4)
        left.h(0)
        for i in range(3):
            left.cx(i, i + 1)
        right = left.copy()
        right.z(0)
        right.z(0)
        evidence = {
            "generator": "4q GHZ H0 CX01 CX12 CX23; right adds Z0 Z0",
            "qasm_sha256": [
                hashlib.sha256(qasm2.dumps(q).encode()).hexdigest()
                for q in (left, right)
            ],
        }
        return left, right, evidence
    raise ValueError(case)


def independent_oracle(left, right):
    import numpy as np
    from qiskit.quantum_info import Operator
    a, b = Operator(left), Operator(right)
    if np.allclose(a.data, b.data, atol=1e-9, rtol=0):
        return "equivalent"
    if a.equiv(b, atol=1e-9, rtol=0):
        return "equivalent*"
    return "not_equivalent"


def result_properties(result):
    def compatible(value):
        if isinstance(value, (int, float, str, bool)) or value is None:
            return value
        return str(value)
    return {
        k: compatible(getattr(result, k, None)) for k in
        ("verification_time", "pathsum_time", "to_DIMACS_time",
         "wmc_time", "tool_time")
    }


def run_case(args):
    from QuPRS import check_equivalence, __version__
    root = args.case_root.resolve()
    left, right, inputs = circuit_pair(args.case, root)
    oracle = independent_oracle(left, right)
    method = "wmc_only" if args.case == "ghz4_wmc_only" else "hybrid"
    probe = PythonProbe() if args.backend == "python" else None
    from QuPRS.interface import load_qiskit

    start = time.perf_counter_ns()
    if probe is None:
        result = check_equivalence(
            left, right, backend="rust", tool_name="gpmc",
            method=method, strategy="Proportional", timeout=args.timeout,
        )
    else:
        with probe.installed():
            result = load_qiskit.check_equivalence(
                left, right, backend="python", tool_name="gpmc",
                method=method, strategy="Proportional", timeout=args.timeout,
            )
    wall = (time.perf_counter_ns() - start) / 1e9
    status = result.equivalent
    if oracle != status:
        raise AssertionError(
            "Operator oracle result %r != QuPRS result %r" % (oracle, status)
        )

    legacy = result_properties(result)
    if probe is not None:
        ledger = probe.exclusive_ledger(wall)
        solver_invoked = probe.calls["solver_supervision"] > 0
        if args.case == "ghz4_wmc_only" and not solver_invoked:
            raise AssertionError("WMC control did not actually invoke subprocess")
    else:
        # Rust's public API contains different nested timing boundaries.
        # Its pathsum_time and wmc_time are siblings; to_dimacs_time and
        # tool_time are children of wmc_time, so NEVER sum all of them.
        def value(key):
            v = legacy.get(key)
            return float(v) if isinstance(v, (int, float)) else None
        pathsum = value("pathsum_time")
        wmc = value("wmc_time")
        if pathsum is None:
            raise AssertionError("Rust pathsum_time is unavailable")
        if method == "wmc_only" and wmc is None:
            raise AssertionError("Rust WMC-only stage is unavailable")
        ledger = check_partition(wall, {
            "pathsum_strategy_combined": pathsum,
            "wmc_all_stages_combined": wmc or 0.0,
        })
        ledger["boundary_calls"] = {}
        ledger["method_note"] = (
            "Rust coarse ledger: native strategy including any reduction is "
            "one interval, WMC including encoding, serialization and solver "
            "is one interval, remaining outer wrapper/FFI/setup goes into Other. "
            "The nested to_dimacs_time and tool_time are NOT summed."
        )
        ledger["fine_grained_missing"] = [
            "gate expansion vs Reduction", "CNF encode vs serialization",
            "actual solver subprocess invocation", "WMC classification",
            "process supervision vs solver compute",
        ]
        solver_invoked = None  # not measured by Rust's public response

    return {
        "schema": SCHEMA, "case": args.case, "backend": args.backend,
        "method": method, "strategy": "Proportional", "solver": "gpmc",
        "result": status, "independent_operator_oracle": oracle,
        "actual_solver_invoked": solver_invoked,
        "measurement": ledger, "published_nested_legacy_fields": legacy,
        "inputs": inputs, "qubits": left.num_qubits,
        "gate_counts": [len(left.data), len(right.data)],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(), "quprs_version": __version__,
            "cpu_affinity": sorted(os.sched_getaffinity(0))
            if hasattr(os, "sched_getaffinity") else None,
            "module": str(sys.modules["QuPRS"].__file__),
        },
        "observation": (
            "One isolated, instrumented diagnostic execution, not a "
            "production performance comparison. Rust fine stages not measured."
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", choices=["qaoa7", "ghz4_wmc_only"], required=True)
    ap.add_argument("--backend", choices=["python", "rust"], required=True)
    ap.add_argument("--case-root", type=Path, default=Path("benchmarks/MQTBench"))
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = run_case(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        "LEDGER", args.case, args.backend, result["result"],
        "solver_invoked", result["actual_solver_invoked"],
        "wall", round(result["measurement"]["measured_wall_seconds"], 4),
        "closure", result["measurement"]["closure_error_seconds"],
        flush=True,
    )


if __name__ == "__main__":
    main()

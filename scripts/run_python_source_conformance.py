#!/usr/bin/env python3
"""Source-to-weighted-CNF cross-check using the independent Python PathSum.

The Rust-source-CNF invocation experiment runs separately; comparing two
transports of one native CNF must not be confused with source-encoding parity.
This diagnostic tests small source circuits against an independent dense
operator, not a general mathematical equivalence certificate.
"""
import argparse
from contextlib import ExitStack
import json
import math
from pathlib import Path
import platform
import sys

import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Operator

from QuPRS.interface.gate_library import gate_map
from QuPRS.interface.load_qiskit import get_gates, initialize
from QuPRS.interface.ps2wmc import to_DIMACS
from QuPRS.utils import WMC

from run_solver_cross_backend import count_from_python, sha256, compare, parse_emitted_dimacs

CASES = ("hh", "x", "t")
SOLVERS = ("gpmc", "ganak")


def unreduced_python_pathsum(circuit):
    pathsum = initialize(circuit)
    # Do not permit Reduction to hide the source encoder being checked.
    pathsum.set_reduction_switch(False)
    for name, qubits, parameters in get_gates(circuit):
        pathsum = gate_map(pathsum, name, qubits, parameters)
    return pathsum


def midpoint(interval):
    return complex(
        float((interval.real.lower + interval.real.upper) / 2),
        float((interval.imag.lower + interval.imag.upper) / 2),
    )


def execute(folder):
    records = []
    with ExitStack() as resources:
        selected = {name: Path(resources.enter_context(WMC(name))).resolve()
                    for name in SOLVERS}
        for name, binary in selected.items():
            if not binary.is_file():
                raise FileNotFoundError(f"{name} selected executable missing")

        for case in CASES:
            source_file = folder / f"{case}.qasm"
            if not source_file.is_file():
                raise FileNotFoundError(f"Source QASM missing: {case}")
            circuit = qasm2.loads(source_file.read_text())
            pathsum = unreduced_python_pathsum(circuit)
            expected = complex(np.trace(Operator(circuit).data)) / (2 ** circuit.num_qubits)
            # For a trace PathSum, each path variable contributes 1/sqrt(2).
            # Historical WMC scaling also divides by 2**num_qubits.
            exponent = pathsum.num_qubits + pathsum.num_pathvar / 2
            normalizer = math.exp2(exponent)
            if not math.isfinite(normalizer) or normalizer <= 0:
                raise AssertionError("Invalid Python PathSum trace normalization")

            for solver in SOLVERS:
                cnf = folder / f"{case}-python-{solver}.cnf"
                to_DIMACS(pathsum, str(cnf), tool_name=solver)
                parsed = parse_emitted_dimacs(cnf.read_text(), solver=solver)
                exact_printed = midpoint(parsed.count())
                observed, capture = count_from_python(cnf, solver, selected[solver])
                normalized = observed / normalizer
                passed = (
                    compare(observed, exact_printed)
                    and compare(normalized, expected)
                    and math.isfinite(normalized.real)
                    and math.isfinite(normalized.imag)
                )
                record = {
                    "case": case,
                    "solver": solver,
                    "source_qasm_sha256": sha256(source_file),
                    "python_emitted_cnf_sha256": sha256(cnf),
                    "rust_emitted_cnf_sha256": sha256(folder / f"{case}-{solver}.cnf"),
                    "cnf_bytes_equal": cnf.read_bytes() == (folder / f"{case}-{solver}.cnf").read_bytes(),
                    "selected_binary_sha256": sha256(selected[solver]),
                    "arguments": capture["solver_args"],
                    "exit_code": capture["returncode"],
                    "native_stdout": capture["stdout"],
                    "native_stderr": capture["stderr"],
                    "unreduced_path_variables": pathsum.num_pathvar,
                    "trace_normalizer": normalizer,
                    "python_count": {"real": observed.real, "imag": observed.imag},
                    "printed_rational_interval_center": {
                        "real": exact_printed.real, "imag": exact_printed.imag
                    },
                    "normalized_python_trace": {
                        "real": normalized.real, "imag": normalized.imag
                    },
                    "independent_dense_trace": {"real": expected.real, "imag": expected.imag},
                    "comparison_budget": "2e-6 * max(1, |reference|); diagnostic only",
                    "observational_pass": passed,
                    "formal_equivalence_certificate": False,
                }
                (folder / f"{case}-python-{solver}.json").write_text(
                    json.dumps(record, indent=2, sort_keys=True) + "\n"
                )
                records.append(record)

    passed = len(records) == 6 and all(item["observational_pass"] for item in records)
    summary = {
        "status": "PASS" if passed else "FAIL",
        "count": len(records),
        "python": sys.version,
        "platform": platform.platform(),
        "assertion": "Independent Python-emitted CNF trace matches printed decimal "
                     "reference and Qiskit dense trace for small source fixtures",
        "formal_certificate": False,
    }
    (folder / "python-source-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    if not passed:
        raise AssertionError("Python source weighted-CNF observational parity failed")
    print(f"PYTHON_SOURCE_CONFORMANCE PASS cases={len(records)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    folder = args.out.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    execute(folder)


if __name__ == "__main__":
    main()

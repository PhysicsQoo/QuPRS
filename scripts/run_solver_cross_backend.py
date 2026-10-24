#!/usr/bin/env python3
"""Compare Python and Rust invocations against identical Rust-emitted CNFs.

These are solver floating-point observations, not exact numerical certificates.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

from QuPRS.utils import WMC
from QuPRS.interface.ps2wmc import run_wmc
from QuPRS.utils import solver_process
from QuPRS.utils.wmc_solvers import SOLVER_ARGUMENTS

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / ".diagnostics" / "wmc_interval_reference"
sys.path.insert(0, str(REFERENCE))
from import_dimacs import parse_emitted_dimacs

CASES = ("hh", "x", "t")
SOLVERS = ("gpmc", "ganak")
LINE = re.compile(r"^WMC_CONFORMANCE\t(hh|x|t)\t(gpmc|ganak)\t(\S+)\t(\S+)$")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def count_from_python(path, solver, selected):
    captures = []
    original = solver_process.run

    def capture(command, **kwargs):
        record = original(command, **kwargs)
        if Path(command[-1]).resolve() == path.resolve():
            captures.append({
                "solver_args": list(command[1:-1]),
                "returncode": record.returncode,
                "stdout": record.stdout,
                "stderr": record.stderr,
                "selected_binary_sha256": sha256(Path(command[0])),
            })
        return record

    solver_process.run = capture
    try:
        re_part, im_part = run_wmc(str(path), solver, timeout=30)
    finally:
        solver_process.run = original
    if len(captures) != 1 or captures[0]["returncode"] != 0:
        raise AssertionError(f"{solver}: expected exactly one successful CNF subprocess")
    if captures[0]["solver_args"] != list(SOLVER_ARGUMENTS[solver]):
        raise AssertionError(f"{solver}: changed solver mode")
    if captures[0]["selected_binary_sha256"] != sha256(selected):
        raise AssertionError(f"{solver}: binary path did not match pinned chosen path")
    return complex(re_part, im_part), captures[0]


def compare(a, b):
    return abs(a - b) <= 2e-6 * max(1.0, abs(b))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    folder = args.out.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        paths = {solver: Path(stack.enter_context(WMC(solver))).resolve()
                 for solver in SOLVERS}
        for solver, path in paths.items():
            if not path.is_file():
                raise FileNotFoundError(f"{solver} executable absent")
        env = dict(os.environ)
        env["QUPRS_GPMC_PATH"] = str(paths["gpmc"])
        env["QUPRS_GANAK_PATH"] = str(paths["ganak"])
        command = [
            "cargo", "run", "--locked", "--release", "--manifest-path",
            str(ROOT / "rust" / "Cargo.toml"), "-p", "pathsum",
            "--example", "solver_conformance", "--", str(folder),
        ]
        result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                capture_output=True, timeout=300)
        (folder / "native-build-and-solve.stdout").write_text(result.stdout)
        (folder / "native-build-and-solve.stderr").write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(f"Native exporter exited {result.returncode}")
        native = {}
        for raw in result.stdout.splitlines():
            found = LINE.fullmatch(raw)
            if found is None:
                continue
            name, solver, real, imag = found.groups()
            key = (name, solver)
            if key in native:
                raise AssertionError(f"Duplicate native fixture: {key}")
            observed = complex(float(real), float(imag))
            if not (math.isfinite(observed.real) and math.isfinite(observed.imag)):
                raise ValueError("Nonfinite Rust native solver observation")
            native[key] = observed
        if set(native) != {(case,solver) for case in CASES for solver in SOLVERS}:
            raise AssertionError("Missing or extra Rust real-solver execution records")
        records = []
        for case in CASES:
            for solver in SOLVERS:
                cnf = folder / f"{case}-{solver}.cnf"
                original = cnf.read_bytes()
                parsed = parse_emitted_dimacs(original.decode(), solver=solver)
                exact_printed = parsed.count()
                center = complex(
                    float((exact_printed.real.lower+exact_printed.real.upper)/2),
                    float((exact_printed.imag.lower+exact_printed.imag.upper)/2),
                )
                py, capture = count_from_python(cnf, solver, paths[solver])
                rust = native[(case,solver)]
                parity = compare(py,rust) and compare(py,center) and compare(rust,center)
                rec = {
                    "case":case, "solver":solver, "source_qasm_sha256":sha256(folder/f"{case}.qasm"),
                    "same_rust_emitted_cnf_sha256":hashlib.sha256(original).hexdigest(),
                    "selected_binary_sha256":sha256(paths[solver]),
                    "arguments":list(SOLVER_ARGUMENTS[solver]),
                    "python_count":{"real":py.real,"imag":py.imag},
                    "rust_count":{"real":rust.real,"imag":rust.imag},
                    "printed_rational_reference_center":{"real":center.real,"imag":center.imag},
                    "native_stdout":capture["stdout"],"native_stderr":capture["stderr"],
                    "native_returncode":capture["returncode"],
                    "comparison_budget":"2e-6 * max(1, |reference|); observation only",
                    "observational_pass":parity,
                    "certified_solver_exactness":False,
                }
                (folder / f"{case}-{solver}.json").write_text(
                    json.dumps(rec,indent=2,sort_keys=True)+"\n")
                records.append(rec)
        complete = len(records)==6 and all(r["observational_pass"] for r in records)
        (folder/"summary.json").write_text(json.dumps({
            "status":"PASS" if complete else "FAIL",
            "case_count":len(records),
            "python":sys.version,"platform":platform.platform(),
            "rust_example_command_args":command[1:-1],
            "meaning":"same emitted CNF, each selected native solver called once by Python and once by Rust; observational not certification",
            "records":records,
        },indent=2,sort_keys=True)+"\n")
        print(f"CONFORMANCE {'PASS' if complete else 'FAIL'} cases={len(records)}")
        return 0 if complete else 1

if __name__=="__main__":
    raise SystemExit(main())

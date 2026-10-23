#!/usr/bin/env python3
"""Source-decimal diagonal-family certificate over actual Python emitted CNFs.

Each case is generated through the current source QuPRS gate mapper and
to_DIMACS. Both GPMC and Ganak run independently as *observations*.
The finite Boolean CNF and exact source weight intervals are checked without
trusting either solver's floating-point arithmetic.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback

from qiskit import qasm2

from QuPRS.interface.ps2wmc import P_to_wlogi, run_wmc, to_DIMACS
from QuPRS.utils import solver_process
from QuPRS.utils.wmc_solvers import SOLVER_ARGUMENTS

from import_dimacs import parse_emitted_dimacs, normalized_for_pathsum
from interval_wmc import serialize_interval
from python_diagonal_source_certificate import audit_diagonal_source_to_emitted_cnf
from run_encoded_bridge import source_pathsum


def sha256(data):
    return hashlib.sha256(data).hexdigest()


CASES = (
    ("rz_near", ("rz(0.001)",), "PROVED_NON_EQUIVALENT"),
    ("rz_far", ("rz(0.01)",), "PROVED_NON_EQUIVALENT"),
    ("rz_twice", ("rz(0.0006)", "rz(0.0004)"), "PROVED_NON_EQUIVALENT"),
    ("rz_p", ("rz(0.0004)", "p(0.0006)"), "PROVED_NON_EQUIVALENT"),
    ("p_only", ("p(0.001)",), "PROVED_NON_EQUIVALENT"),
    ("t_only", ("t",), "PROVED_NON_EQUIVALENT"),
    ("rz_t", ("rz(0.001)", "t"), "PROVED_NON_EQUIVALENT"),
    ("z_only", ("z",), "PROVED_NON_EQUIVALENT"),
    ("s_sdg_cancel", ("s", "sdg"), "INCONCLUSIVE"),
    ("rz_cancel", ("rz(0.001)", "rz(-0.001)"), "INCONCLUSIVE"),
    ("tiny_rz", ("rz(0.000000000001)",), "BOUNDARY_CONTROL"),
)


def make_qasm(gates):
    return (
        'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
        + "".join(f"{gate} q[0];\n" for gate in gates)
    )


def observe_native(dimacs_path, solver):
    captures = []
    original = solver_process.run
    def observed(cmd, **kwargs):
        response = original(cmd, **kwargs)
        is_target = Path(cmd[-1]).resolve() == dimacs_path.resolve()
        captures.append({
            "is_target": is_target,
            "args": list(cmd[1:-1]),
            "executable_sha256": sha256(Path(cmd[0]).read_bytes()),
            "exit": response.returncode,
            "stdout": response.stdout,
            "stderr": response.stderr,
        })
        return response
    solver_process.run = observed
    try:
        real, imag = run_wmc(str(dimacs_path), solver, timeout=60)
    finally:
        solver_process.run = original
    relevant = [x for x in captures if x["is_target"]]
    if len(relevant) != 1 or relevant[0]["exit"] != 0:
        raise ValueError("Did not run exactly one successful selected native solver")
    if relevant[0]["args"] != list(SOLVER_ARGUMENTS[solver]):
        raise ValueError("Native solver mode differs from selected independent adapter")
    return complex(real, imag), relevant[0]


def run_one(folder, label, gates, solver, expectation):
    source = make_qasm(gates)
    source_bytes = source.encode("utf-8")
    (folder/f"{label}.qasm").write_bytes(source_bytes)
    qc = qasm2.loads(source)
    ps = source_pathsum(qc)
    cnf_path = folder / f"{label}-{solver}.cnf"
    returned = to_DIMACS(ps, str(cnf_path), tool_name=solver)
    raw = cnf_path.read_bytes()
    if returned.strip().encode() != raw:
        raise ValueError("Actual Python emitted CNF mismatch")
    parsed = parse_emitted_dimacs(raw.decode("utf-8"), solver=solver)
    certificate = None
    unsupported = None
    try:
        certificate = audit_diagonal_source_to_emitted_cnf(
            source, ps, parsed, p_to_wlogi=P_to_wlogi
        )
    except (ValueError, TypeError, ArithmeticError) as exc:
        unsupported = f"{type(exc).__name__}: {exc}"
    # Even unsupported verification source material is preserved for audit.
    claimed = (
        "PROVED_NON_EQUIVALENT"
        if certificate and certificate["formal_source_wmc_non_equivalence_supported"]
        else "INCONCLUSIVE"
    )
    raw_solver, solver_meta = observe_native(cnf_path, solver)
    printed_exact = parsed.count()
    printed_norm = normalized_for_pathsum(
        printed_exact, num_qubits=ps.num_qubits, num_pathvar=ps.num_pathvar
    )
    numeric_ref = complex(
        float((printed_exact.real.lower + printed_exact.real.upper)/2),
        float((printed_exact.imag.lower + printed_exact.imag.upper)/2),
    )
    observed_error = abs(raw_solver - numeric_ref)
    observed_tolerance = 2e-6 * max(1, abs(numeric_ref))
    result = {
        "source_name":label, "source_gate_text":list(gates), "solver":solver,
        "expected_outcome":expectation, "claimed_outcome":claimed,
        "qasm_sha256":sha256(source_bytes), "cnf_sha256":sha256(raw),
        "python_emitter_file_sha256":sha256(Path("src/QuPRS/interface/ps2wmc.py").read_bytes()),
        "python_gate_file_sha256":sha256(Path("src/QuPRS/pathsum/gates/single_qubit.py").read_bytes()),
        "native_executable_sha256":solver_meta["executable_sha256"],
        "native_stdout":solver_meta["stdout"],
        "native_stderr":solver_meta["stderr"],
        "native_solver_arguments":solver_meta["args"],
        "actual_native_float_count":{"real":raw_solver.real,"imag":raw_solver.imag},
        "printed_weight_count_normalized":serialize_interval(printed_norm),
        "native_vs_printed_count_float_error":observed_error,
        "native_observational_budget":observed_tolerance,
        "native_observational_only":True,
        "native_observational_agreement":math.isfinite(observed_error) and observed_error <= observed_tolerance,
        "num_qubits":ps.num_qubits,"num_pathvar":ps.num_pathvar,
        "cnf_variables":len(parsed.weights),"cnf_clauses":len(parsed.clauses),
        "source_certificate":certificate,
        "certificate_unsupported_reason":unsupported,
    }
    result["check_passed"] = (
        (claimed == expectation or expectation == "BOUNDARY_CONTROL")
        and result["native_observational_agreement"]
        and (certificate is not None or expectation in ("INCONCLUSIVE", "BOUNDARY_CONTROL"))
    )
    (folder/f"{label}-{solver}.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    print("PYTHON_SOURCE",label,solver,claimed,
          "PASS" if result["check_passed"] else "FAIL",flush=True)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("python-source-certificate-results"))
    args=parser.parse_args()
    folder=args.output.resolve()
    folder.mkdir(parents=True,exist_ok=True)
    results=[]
    for label,gates,expectation in CASES:
        for solver in ("gpmc","ganak"):
            try:
                result=run_one(folder,label,gates,solver,expectation)
            except Exception as exc:
                result={"source_name":label,"solver":solver,"expected_outcome":expectation,
                        "check_passed":False,"exception":repr(exc),
                        "traceback":traceback.format_exc()}
                (folder/f"{label}-{solver}.json").write_text(
                    json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
                )
            results.append(result)
    passed=sum(bool(x["check_passed"]) for x in results)
    summary={
        "schema":"python-source-diagonal-emitted-cnf-rational-certificate-v1",
        "case_count":len(CASES),
        "native_comparisons":len(results),
        "passed":passed,
        "status":"PASS" if passed==len(results) else "FAIL",
        "certificate_scope":"only validated canonical one-qubit diagonal source QASM",
        "solver_certified":False,
        "source_compiler_general_certificate":False,
        "observations":results,
    }
    (folder/"summary.json").write_text(
        json.dumps(summary,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    print("PYTHON_SOURCE_SUMMARY",
          json.dumps({"status":summary["status"],"passed":passed,
                      "total":len(results)}),flush=True)
    return 0 if summary["status"]=="PASS" else 2

if __name__=="__main__":
    sys.exit(main())

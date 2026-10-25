#!/usr/bin/env python3
"""Scoped native Python WMC-CNF observational probe for six pure-RZ pairs.

Uses the existing source-native QuPRS to_DIMACS and both independent selected
GPMC/Ganak invocations. A CNF magnitude upper <1 is accepted only with the
existing source-to-actual-CNF Boolean/weight audit. Exact source equality
is NOT a compiled-circuit equivalence certificate; native float is never one.
"""
import argparse
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import sys
import traceback

SOURCE_REF = Path(__file__).resolve().parents[1] / "wmc_interval_reference"
sys.path.insert(0,str(SOURCE_REF))
from run_python_source_certificate import run_one
from rz_sequence_oracle import CASES, compare_sources, make_qasm


def opposite(token):
    return token[1:] if token.startswith("-") else "-" + token


def relative_gates(left, right):
    # For pure RZ, U^dagger V is the reversed inverse of U followed by V.
    return tuple("rz("+s+")" for s in (
        tuple(opposite(x) for x in reversed(left)) + tuple(right)
    ))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    folder=args.output.resolve()
    folder.mkdir(parents=True,exist_ok=True)
    reports=[]
    for label,left,right,expected in CASES:
        theorem=compare_sources(make_qasm(left),make_qasm(right))
        if theorem["source_global_phase_verdict"]!=expected:
            raise ValueError("Incorrect source theorem for "+label)
        gates=relative_gates(left,right)
        for solver in ("gpmc","ganak"):
            item={"case":label,"solver":solver,"relative_gates":list(gates),
                  "source_theorem":theorem,"expected_source_outcome":expected}
            try:
                # BOUNDARY_CONTROL asks the pre-existing runner to preserve
                # numerical observations regardless of their exact verdict.
                native=run_one(folder,label,gates,solver,"BOUNDARY_CONTROL")
                item["native_report"]=native
                certificate=native["source_certificate"]
                strict_negative=bool(certificate and
                    certificate["formal_source_wmc_non_equivalence_supported"]
                    and certificate["source_boolean_encoding_proof"]
                        ["weighted_literal_activation_verified"]
                    and certificate["source_non_equivalent_up_to_global_phase_proved"])
                if expected=="EQUIVALENT" and strict_negative:
                    raise ValueError("False negative CNF proof on exact source cancellation")
                item["source_cnf_negative_proved"]=strict_negative
                item["source_cnf_verdict"]=(
                    "BOUNDED_NON_EQUIVALENT" if strict_negative else "INCONCLUSIVE")
                item["compiled_exact_equivalence_certified"]=False
                item["native_solver_float_certified"]=False
                item["native_observation_pass"]=bool(
                    native["native_observational_agreement"]
                    and native["native_observational_only"]
                    and native["qasm_sha256"]==sha256(
                        make_qasm(tuple(s[3:-1] for s in gates)).encode()).hexdigest()
                    and native["native_executable_sha256"]
                    and native["cnf_sha256"]
                    and native["native_stdout"])
                item["check_passed"]=item["native_observation_pass"]
            except Exception as exc:
                item["check_passed"]=False
                item["error"]=repr(exc)
                item["traceback"]=traceback.format_exc()
            (folder/f"probe-{label}-{solver}.json").write_text(
                json.dumps(item,sort_keys=True,indent=2)+"\n")
            reports.append(item)
            print("NATIVE_RZ_PYTHON",label,solver,
                  "OK" if item["check_passed"] else "FAILED",
                  item.get("source_cnf_verdict","UNKNOWN"),flush=True)
    result={
        "schema":"pure-rz-six-pair-native-python-actual-cnf-probe-v1",
        "source_pairs":len(CASES),
        "emitted_cnf_observations":len(reports),
        "passed":sum(bool(r["check_passed"]) for r in reports),
        "status":"PASS" if all(r["check_passed"] for r in reports) else "FAIL",
        "native_solver_arithmetic_certified":False,
        "general_python_compiler_certified":False,
        "source_positive_not_promoted":True,
        "observations":reports,
    }
    (folder/"summary.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("NATIVE_RZ_PYTHON_SUMMARY",result["status"],
          result["passed"],"/",len(reports),flush=True)
    return 0 if result["status"]=="PASS" else 2


if __name__=="__main__":
    sys.exit(main())

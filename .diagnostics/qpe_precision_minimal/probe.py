#!/usr/bin/env python3
"""Real-gate minimal counterexamples for decimal-angle finite-rational aliasing.

No production reducer or numeric threshold is modified. Independent Qiskit
unitary truth precedes all QuPRS calls; unknown/timeouts are INCONCLUSIVE.
"""
import hashlib
import json
import math
import os
from fractions import Fraction
from pathlib import Path
import platform
import subprocess
import sys
import argparse

import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Operator
from QuPRS import check_equivalence, _pathsum_rust
from QuPRS.utils import WMC

OUT = Path("angle-minimal-counterexample-results")
METHODS = ("reduction_rules", "hybrid", "wmc_only")
STRATEGIES = ("Naive", "Proportional")
BACKENDS = ("rust", "python")
CASES = {
    "qpe_decimal_double": {"kind": "add", "a": -2.5802058126763807,
                           "b": -2.5802058126763807, "oracle": "equivalent"},
    "qpe_decimal_cross": {"kind": "add", "a": 1.6198837120072371,
                          "b": -2.5802058126763807, "oracle": "equivalent"},
    "qpe_decimal_mixed": {"kind": "add", "a": 1.3499030933393643,
                          "b": 0.125, "oracle": "equivalent"},
    "exact_symbolic_pi": {"kind": "pi", "oracle": "equivalent"},
    "genuine_unequal_rz": {"kind": "unequal_rz", "oracle": "not_equivalent"},
    "genuine_unequal_x": {"kind": "unequal_x", "oracle": "not_equivalent"},
}
KNOWN_SOURCE_ANGLE = -2.5802058126763807
CHILD_TIMEOUT = 25
NATIVE_TIMEOUT = 18

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def qasm(*lines):
    return "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\n" + "".join(
        f"{gate} q[0];\n" for gate in lines)

def circuits(case):
    cfg = CASES[case]
    if cfg["kind"] == "add":
        a,b = cfg["a"],cfg["b"]
        # Use exactly round-trippable decimal numbers, not symbolic PathSum.
        return qasm(f"rz({a:.17g})",f"rz({b:.17g})"), qasm(f"rz({a+b:.17g})")
    if cfg["kind"] == "pi":
        return qasm("rz(pi/8)","rz(pi/8)"),qasm("rz(pi/4)")
    if cfg["kind"] == "unequal_rz":
        return qasm("rz(0.125)"), qasm("rz(0.126)")
    if cfg["kind"] == "unequal_x":
        return qasm(), qasm("x")
    raise KeyError(case)

def cf_1e10(value):
    """Port of rust/pathsum/src/rational.rs FreeRational::from_f64.
    The two finite bounds are diagnostic source-specific invariants, not
    an independent numeric-correctness oracle.
    """
    epsilon=1e-10
    max_denom=1_000_000_000
    if abs(value)<epsilon:return Fraction(0)
    sign=-1 if value<0 else 1
    val=abs(value)
    x=val
    n0,n1,d0,d1=0,1,1,0
    for _ in range(128):
        a=math.floor(x)
        n2=a*n1+n0;d2=a*d1+d0
        if d2>max_denom:break
        n0,n1=n1,n2;d0,d1=d1,d2
        if abs(val-n1/d1)<epsilon:break
        frac=x-a
        if frac<epsilon:break
        x=1.0/frac
    return Fraction(sign*n1,d1)

def parser_projection(case):
    cfg=CASES[case]
    if cfg["kind"]=="add":
        a,b=cfg["a"],cfg["b"]
        u,v,w=(cf_1e10(z/math.pi) for z in (a,b,a+b))
        diff=u+v-w
        return {"rust_source_rule":"Angle::from_qasm_str -> FreeRational::from_f64",
                "rational_left_angles":[str(u),str(v)],
                "rational_right_angles":[str(w)],
                "rational_pi_units_nonconstant_delta":str(diff),
                "rational_pi_units_delta_float":float(diff),
                "angle_literals":[format(a,".17g"),format(b,".17g"),
                                  format(a+b,".17g")]}
    if cfg["kind"]=="pi":
        return {"rational_left_angles":["1/8","1/8"],
                "rational_right_angles":["1/4"],
                "rational_pi_units_nonconstant_delta":"0",
                "rational_pi_units_delta_float":0}
    return {"rational_pi_units_nonconstant_delta":None}

def oracle(case):
    left,right=circuits(case)
    U=Operator(qasm2.loads(left)).data
    V=Operator(qasm2.loads(right)).data
    z=np.vdot(V.reshape(-1),U.reshape(-1))
    if abs(z)<1e-14:raise RuntimeError("no global phase estimate")
    ph=z/abs(z)
    err=float(np.max(np.abs(U-ph*V)))
    rel=float(np.linalg.norm(U-ph*V)/np.linalg.norm(U))
    truth=("equivalent" if err<1e-10 and rel<1e-10 else "not_equivalent")
    if truth != CASES[case]["oracle"]:
        raise RuntimeError(f"independent oracle truth changed: {case} {truth}")
    return {"truth":truth,"max_phase_aligned_element_error":err,
            "relative_frobenius":rel,
            "qubits":1,
            "gate_counts":[len(qasm2.loads(left).data),len(qasm2.loads(right).data)]}

def one(case,method,strategy,backend):
    left,right=circuits(case)
    os.environ["QUPRS_STAGE_LEDGER"]="1"
    os.environ["QUPRS_FFI_PHASE_TIMING"]="1"
    with WMC("gpmc") as binary:
        if Path(os.environ["QUPRS_GPMC_PATH"]).resolve() != binary.resolve():
            raise RuntimeError("GPMC solver path changed")
        try:
            if backend=="rust":
                r=_pathsum_rust.check_equivalence(
                    left,right,method=method,strategy=strategy,
                    tool_name="gpmc",timeout=NATIVE_TIMEOUT)
                label={"Equivalent":"equivalent",
                       "Equivalent (Up to Global Phase)":"equivalent",
                       "Not Equivalent":"not_equivalent",
                       "Unknown":"unknown","Timeout":"timeout",
                       "MemoryOut":"memory_out"}.get(r["status"],"unrecognized")
                result={"status":label,"native_status":r["status"],
                        "stats":r.get("stats"),
                        "stage_ledger":r.get("stage_ledger"),
                        "ffi_phase_timings":r.get("ffi_phase_timings"),
                        "final_pathsum":str(r.get("final_ps",""))[:14000],
                        "qubits":r.get("qubits"),
                        "gate_counts":[r.get("gates1"),r.get("gates2")],
                        "wmc_solver_seconds":r.get("wmc_solver_time_sec")}
            else:
                r=check_equivalence(
                    left,right,backend="python",method=method,
                    strategy=strategy,tool_name="gpmc",timeout=NATIVE_TIMEOUT)
                result={"status":("equivalent" if r.equivalent in ("equivalent","equivalent*")
                                  else r.equivalent),
                        "python_status":r.equivalent,
                        "gate_counts":[r.gate_num,r.gate_num2],
                        "final_pathsum":str(r.final_pathsum)[:14000],
                        "wmc_solver_seconds":r.tool_time,
                        "statistics":str(r.Statistics)}
            return {"case":case,"backend":backend,"method":method,
                    "strategy":strategy,**result,"error":None}
        except Exception as exc:
            return {"case":case,"backend":backend,"method":method,
                    "strategy":strategy,"status":"error","error":repr(exc)}

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    if abs(KNOWN_SOURCE_ANGLE-CASES["qpe_decimal_double"]["a"])>0:
        raise RuntimeError("QPE literal changed")
    with WMC("gpmc") as binary:
        os.environ["QUPRS_GPMC_PATH"]=str(binary.resolve())
        environment={"schema":"quprs-angle-counterexample-v1",
                     "source_sha":subprocess.check_output(
                          ["git","rev-parse","HEAD"],text=True).strip(),
                     "script_sha256":sha(__file__),"python":sys.version,
                     "platform":platform.platform(),
                     "qiskit_version":__import__("qiskit").__version__,
                     "numpy_version":np.__version__,
                     "gpmc_sha256":sha(binary),
                     "rust_extension":str(Path(_pathsum_rust.__file__).resolve()),
                     "methods":METHODS,"strategies":STRATEGIES,"backends":BACKENDS,
                     "timeout_native":NATIVE_TIMEOUT,
                     "timeout_child":CHILD_TIMEOUT,
                     "rationalizer_epsilon":1e-10,"rationalizer_max_denom":1_000_000_000}
        results=[];errors=[];oracles={}
        for case in CASES:
            lhs,rhs=circuits(case)
            local=OUT/"qasm"/case
            local.mkdir(parents=True,exist_ok=True)
            (local/"left.qasm").write_text(lhs)
            (local/"right.qasm").write_text(rhs)
            oracles[case]={"oracle":oracle(case),
                           "rational_probe":parser_projection(case),
                           "qasm_sha256":[sha(local/"left.qasm"),sha(local/"right.qasm")]}
        environment["cases"]=oracles
        dump(OUT/"environment.json",environment)
        with (OUT/"samples.jsonl").open("w",buffering=1) as fp:
            for case in CASES:
                for method in METHODS:
                    for strategy in STRATEGIES:
                        for backend in BACKENDS:
                            key=f"{case}_{method}_{strategy}_{backend}"
                            command=[sys.executable,"-u",str(Path(__file__).resolve()),
                                     "--one","--case",case,"--method",method,
                                     "--strategy",strategy,"--backend",backend]
                            try:
                                p=subprocess.run(command,text=True,capture_output=True,
                                                 timeout=CHILD_TIMEOUT,env=os.environ.copy())
                                if p.returncode!=0:raise RuntimeError(f"child exit {p.returncode}: {p.stderr[-1000:]}")
                                data=json.loads(p.stdout)
                            except Exception as exc:
                                data={"case":case,"method":method,"strategy":strategy,
                                      "backend":backend,"status":"error","error":repr(exc)}
                            row={"key":key,"data":data}
                            dump(OUT/"individual"/(key+".json"),row)
                            fp.write(json.dumps(row,sort_keys=True)+"\n")
                            results.append(row)
                            truth=oracles[case]["oracle"]["truth"]
                            status=data["status"]
                            if status in ("unknown","timeout","memory_out","error","unrecognized"):
                                errors.append({"key":key,"kind":"INCONCLUSIVE","status":status})
                            elif status!=truth:
                                errors.append({"key":key,"kind":"SEMANTIC_MISMATCH",
                                               "truth":truth,"observed":status})
                            if data.get("gate_counts")!=oracles[case]["oracle"]["gate_counts"]:
                                errors.append({"key":key,"kind":"GATE_COUNT_DIFFERENCE"})
                            print("ANGLE_PROBE",key,status,flush=True)
        mismatch=[x for x in errors if x["kind"]=="SEMANTIC_MISMATCH"]
        summary={"schema":environment["schema"],
                 "status":"SCIENCE_BLOCKED" if errors else "PASS_SEMANTIC_PARITY",
                 "raw_records":len(results),"expected_records":len(CASES)*len(METHODS)*len(STRATEGIES)*len(BACKENDS),
                 "cases":list(CASES),"errors":errors,
                 "semantic_mismatch_count":len(mismatch),
                 "sample_mismatch_cases":sorted(set(x["key"].split("_reduction")[0]
                    for x in mismatch)),
                 "cautions":["The predicted Python continued-fraction input is a port of Rust source, not a direct introspection of its internal rational value.",
                             "A proven finite-rational mismatch is not by itself proof of a particular QPE gate's contribution.",
                             "A no-false-positive result on the explicit RZ/X controls is required before considering any production fix.",
                             "Qiskit dense-unitary oracle is independent of PathSum and GPMC.",
                             "Data may intentionally yield SCIENCE_BLOCKED; do not use continue-on-error.",
                             "No production verification logic, tolerances, solver or scheduling changes."]}
        dump(OUT/"summary.json",summary)
        print(json.dumps({"status":summary["status"],"records":len(results),
                          "mismatches":len(mismatch),"other_errors":len(errors)-len(mismatch)}))
        return 2 if errors or len(results)!=summary["expected_records"] else 0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--one",action="store_true")
    ap.add_argument("--case",choices=CASES)
    ap.add_argument("--method",choices=METHODS)
    ap.add_argument("--strategy",choices=STRATEGIES)
    ap.add_argument("--backend",choices=BACKENDS)
    args=ap.parse_args()
    if args.one:
        print(json.dumps(one(args.case,args.method,args.strategy,args.backend),
                         sort_keys=True,default=str))
        return 0
    return run()

if __name__=="__main__":sys.exit(main())

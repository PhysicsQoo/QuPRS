#!/usr/bin/env python3
"""Independent WMC near-unity numerical decision audit (no policy changes).

GPMC and Ganak remain separate exact solver selections. The independent
operator oracle does not derive truth from their weighted counts.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
from mpmath import mp
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
import numpy as np

from QuPRS import check_equivalence, config
from QuPRS.utils import WMC
from QuPRS.utils import solver_process
from QuPRS.utils.wmc_solvers import parse_count_line

OUT=Path("wmc-numerical-policy-results")
DELTAS=("0","0.000001","0.0001","0.001","0.01","0.2")
CASES=DELTAS+("global_phase",)
BACKENDS=("python","rust")
SOLVERS=("gpmc","ganak")
EXPECTED=len(CASES)*len(BACKENDS)*len(SOLVERS)

def hbytes(raw):
    return hashlib.sha256(raw).hexdigest()

def digest(p):
    return hbytes(Path(p).read_bytes())

def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,sort_keys=True,indent=2,default=str)+"\n")

def circuits(case):
    lhs=QuantumCircuit(1)
    rhs=QuantumCircuit(1)
    if case=="global_phase":
        for gate in ("x","z","x","z"):
            getattr(rhs,gate)(0)
    else:
        rhs.rz(float(case),0)
    return lhs,rhs

def independent_oracle(case):
    a,b=circuits(case)
    u,v=Operator(a).data,Operator(b).data
    overlap=np.vdot(v.ravel(),u.ravel())
    phase=overlap/abs(overlap) if abs(overlap)>1e-14 else 1.+0.j
    max_error=float(np.abs(u-phase*v).max())
    with mp.workdps(100):
        if case=="global_phase":
            mag=mp.mpf(1)
        else:
            mag=abs(mp.cos(mp.mpf(case)/2))
        defect=mp.mpf(1)-mag
        normalized_frobenius=mp.sqrt(2*defect)
        analytic={"m_high_precision":mp.nstr(mag,100),
                  "defect_high_precision":mp.nstr(defect,100),
                  "best_phase_frobenius_high_precision":mp.nstr(normalized_frobenius,100)}
    return {"truth":"equivalent*" if case=="global_phase" else
                     "equivalent" if case=="0" else "not_equivalent",
            "matrix_max_residual":max_error,
            "qasm_gate_counts":[len(a.data),len(b.data)],
            "analytic":analytic}

def one(case,backend,solver):
    from QuPRS.utils import wmc_solvers
    a,b=circuits(case)
    oracle=independent_oracle(case)
    captures=[]
    actual_run=solver_process.run
    def instrumented_run(command, timeout):
        output=actual_run(command,timeout)
        file=Path(command[-1])
        captures.append({
            "args_without_binary":list(command[1:-1]),
            "executable_sha256":digest(command[0]),
            "cnf_sha256":digest(file) if file.is_file() else None,
            "cnf_bytes":file.stat().st_size if file.is_file() else None,
            "exit":output.returncode,
            "solver_stdout":output.stdout,
            "solver_stderr":output.stderr,
        })
        return output
    solver_process.run=instrumented_run
    try:
        with WMC(solver) as binary:
            solver_info={"name":solver,"sha256":digest(binary),
                         "executable":str(binary)}
        result=check_equivalence(a,b,method="wmc_only",strategy="Naive",
                                 backend=backend,tool_name=solver,timeout=60)
        normalized_count=None
        if captures and backend=="python":
            count_lines=[]
            for line in captures[0]["solver_stdout"].splitlines():
                c=parse_count_line(line)
                if c is not None: count_lines.append({"raw":line,"real":c.real,"imag":c.imag})
            if len(count_lines)==1 and result.expect is not None:
                normalized_count=math.ldexp(abs(complex(count_lines[0]["real"],count_lines[0]["imag"])),
                                            -int(result.expect)) if float(result.expect).is_integer() else (
                    abs(complex(count_lines[0]["real"],count_lines[0]["imag"])) /
                    (2**result.expect)
                )
            captures[0]["parsed_count_lines"]=count_lines
        record={"case":case,"backend":backend,"solver":solver,
                "source_oracle":oracle,"outcome":result.equivalent,
                "solver_info":solver_info,"solver_child_capture":captures,
                "normalized_count_float":normalized_count,
                "expected_log2":result.expect,
                "log_count":result.log_wmc,
                "solver_time":result.tool_time,
                "python_gate_counts":[result.gate_num,result.gate_num2],
                "error":None}
    except Exception as err:
        record={"case":case,"backend":backend,"solver":solver,
                "source_oracle":oracle,"outcome":"ERROR",
                "solver_child_capture":captures,"error":repr(err)}
    finally:
        solver_process.run=actual_run
    return record

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--one",action="store_true")
    p.add_argument("--case",choices=CASES)
    p.add_argument("--solver",choices=SOLVERS)
    p.add_argument("--backend",choices=BACKENDS)
    opts=p.parse_args()
    if opts.one:
        print(json.dumps(one(opts.case,opts.backend,opts.solver),sort_keys=True,default=str))
        return 0
    OUT.mkdir(parents=True,exist_ok=True)
    environment={
        "schema":"quprs-wmc-actual-solver-numeric-boundary-v1",
        "git_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        "source_sha256":digest(__file__),"python":sys.version,
        "platform":platform.platform(),"qiskit":__import__("qiskit").__version__,
        "numpy":np.__version__,
        "existing_magnitude_tolerance":config.WMC_MAGNITUDE_TOLERANCE,
        "existing_phase_tolerance":config.WMC_PHASE_TOLERANCE,
        "solvers":SOLVERS,"backends":BACKENDS,"cases":CASES,
        "policy":"report-only: no numerical threshold or production verdict modified"}
    write(OUT/"environment.json",environment)
    entries=[]
    with (OUT/"samples.jsonl").open("w",buffering=1) as fh:
        for case in CASES:
            for solver in SOLVERS:
                for backend in BACKENDS:
                    cmd=[sys.executable,"-u",str(Path(__file__).resolve()),"--one",
                         "--case",case,"--solver",solver,"--backend",backend]
                    key=f"{case.replace('.','p')}_{solver}_{backend}"
                    try:
                        done=subprocess.run(cmd,capture_output=True,text=True,timeout=85)
                        record=json.loads(done.stdout) if done.returncode==0 else {
                            "case":case,"solver":solver,"backend":backend,
                            "outcome":"ERROR","error":done.stderr[-4000:]}
                    except Exception as exc:
                        record={"case":case,"solver":solver,"backend":backend,
                                "outcome":"ERROR","error":repr(exc)}
                    write(OUT/"individual"/f"{key}.json",record)
                    fh.write(json.dumps(record,sort_keys=True,default=str)+"\n")
                    entries.append(record)
                    print("NUMERIC_SAMPLE",key,record["outcome"],flush=True)
    mismatches=[]
    for row in entries:
        truth=row.get("source_oracle",{}).get("truth")
        actual=row.get("outcome")
        is_true=truth in ("equivalent","equivalent*")
        is_claim=actual in ("equivalent","equivalent*")
        if actual=="ERROR" or actual in ("Timeout","MemoryOut","unknown"):
            mismatches.append({"case":row["case"],"backend":row["backend"],
                               "solver":row["solver"],"kind":"INCONCLUSIVE","actual":actual})
        elif is_true!=is_claim:
            mismatches.append({"case":row["case"],"backend":row["backend"],
                               "solver":row["solver"],"kind":"STRICT_SEMANTIC_MISMATCH","actual":actual})
    status="SCIENCE_BLOCKED" if mismatches or len(entries)!=EXPECTED else "PASS"
    summary={"schema":environment["schema"],"status":status,
             "records":len(entries),"expected":EXPECTED,
             "discrepancies":mismatches,
             "constraints":[
                "Very-close-to-1 may be floating error OR genuine inequivalence.",
                "High-precision analytic mpmath controls are an independent oracle for this RZ family, NOT certified solver arithmetic intervals.",
                "Python raw solver stdout captured from the actual selected binary; Rust raw stdout is not exposed by this FFI and is marked unavailable.",
                "Do not treat agreement of two solver verdicts as a certificate.",
                "No tolerance change, solver substitution, scheduler change, or proposed new approximate-equivalence API."
             ]}
    write(OUT/"summary.json",summary)
    print(json.dumps({"status":status,"records":len(entries),
                      "blockers":len(mismatches)}),flush=True)
    return 2 if status!="PASS" else 0

if __name__=="__main__":
    sys.exit(main())

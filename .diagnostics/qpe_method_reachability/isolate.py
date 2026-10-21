#!/usr/bin/env python3
"""Fail-closed QPEexact8 method/backend isolation, without production changes.

Qiskit matrix is the independent semantic oracle. A known false-negative
must remain SCIENCE_BLOCKED, even if the run and artifact upload succeed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from qiskit import qasm2
from qiskit.quantum_info import Operator
import numpy as np

from QuPRS import check_equivalence, _pathsum_rust
from QuPRS.utils import WMC

ROOT=Path("benchmarks/MQTBench").resolve()
OUT=Path("qpe-method-isolation-results").resolve()
CASES={
 "qpeexact8":"qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
 "qpeinexact8":"qpeinexact_nativegates_ibm_qiskit_opt0_8.qasm",
}
BACKENDS=("rust","python")
METHODS=("reduction_rules","hybrid","wmc_only")
STRATEGIES=("Naive","Proportional")
CHILD_TIMEOUT=60
NATIVE_TIMEOUT=40
EXPECTED_QPE8_HASHES=(
 "8d514d06f7c9e81abda1042796cc34227624c9ed66097bee1ce5e97a87884dda",
 "227ab45a4eb033889aa57bb53e54938e74d757fea30eaa3d276b495048dc6141",
)

def filehash(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def emit(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,sort_keys=True,indent=2,default=str)+"\n")

def pair(case):
 f=CASES[case]
 return ROOT/f,ROOT/"h,ry,rz,cx"/f

def oracle(case):
 a,b=pair(case)
 u,v=Operator(qasm2.load(str(a))).data,Operator(qasm2.load(str(b))).data
 z=np.vdot(v.reshape(-1),u.reshape(-1))
 if abs(z)<1e-14:raise ValueError("Cannot determine global phase")
 phase=z/abs(z)
 delta=np.abs(u-phase*v)
 global_equiv=bool(float(delta.max())<1e-8 and
                   float(np.linalg.norm(delta)/np.linalg.norm(u))<1e-8)
 exact=bool(float(np.max(np.abs(u-v)))<1e-8)
 return {"classification":"equivalent" if exact else "equivalent*" if global_equiv else "not_equivalent",
         "equivalent_up_to_phase":global_equiv,
         "best_phase":[float(phase.real),float(phase.imag)],
         "max_residual":float(delta.max()),
         "relative_frobenius":float(np.linalg.norm(delta)/np.linalg.norm(u)),
         "input_qasm_sha256":[filehash(a),filehash(b)],
         "qasm_qiskit_gate_counts":[len(qasm2.load(str(a)).data),
                                     len(qasm2.load(str(b)).data)],
         "qubits":int(qasm2.load(str(a)).num_qubits)}

def one(case,backend,method,strategy):
 os.environ["QUPRS_STAGE_LEDGER"]="1"
 os.environ["QUPRS_FFI_PHASE_TIMING"]="1"
 a,b=pair(case)
 with WMC("gpmc") as binary:
  assert Path(os.environ["QUPRS_GPMC_PATH"]).resolve()==binary.resolve()
  start=time.perf_counter_ns()
  try:
   if backend=="rust":
    r=_pathsum_rust.check_equivalence(
     str(a),str(b),method=method,strategy=strategy,tool_name="gpmc",
     timeout=NATIVE_TIMEOUT)
    st=r["status"]
    status={"Equivalent":"equivalent",
            "Equivalent (Up to Global Phase)":"equivalent*",
            "Not Equivalent":"not_equivalent",
            "Unknown":"unknown","Timeout":"Timeout","MemoryOut":"MemoryOut"}.get(st,st)
    ps=str(r.get("final_ps",""))
    metrics={
      "native_status":st,"stats":r.get("stats"),"stage_ledger":r.get("stage_ledger"),
      "ffi_phase_timings":r.get("ffi_phase_timings"),
      "gate_counts":[r.get("gates1"),r.get("gates2")],
      "qubits":r.get("qubits"),"native_seconds":r.get("verification_time_sec"),
      "pathsum_seconds":r.get("pathsum_time_sec"),
      "wmc_solver_seconds":r.get("wmc_solver_time_sec"),
      "wmc_dimacs_seconds":r.get("wmc_dimacs_time_sec"),
    }
   else:
    r=check_equivalence(str(a),str(b),backend="python",method=method,
                       strategy=strategy,tool_name="gpmc",timeout=NATIVE_TIMEOUT)
    status=r.equivalent
    ps=str(r.final_pathsum)
    metrics={
      "gate_counts":[r.gate_num,r.gate_num2],
      "qubits":r.qubit_num,
      "pathsum_seconds":r.pathsum_time,
      "native_seconds":r.verification_time,
      "wmc_solver_seconds":r.tool_time,
      "wmc_dimacs_seconds":r.to_DIMACS_time,
      "python_statistics":str(r.Statistics),
    }
   outcome={"status":status,"error":None,"elapsed_ns":time.perf_counter_ns()-start,
            "final_pathsum_sha256":hashlib.sha256(ps.encode()).hexdigest(),
            "final_pathsum_excerpt":ps[:10000],"metrics":metrics}
  except Exception as e:
   outcome={"status":"EXCEPTION","error":repr(e),
            "elapsed_ns":time.perf_counter_ns()-start,"metrics":{}}
 return {"case":case,"backend":backend,"method":method,"strategy":strategy,
         "solver":"gpmc","input_qasm_sha256":[filehash(a),filehash(b)],
         "extension":str(Path(_pathsum_rust.__file__).resolve()),**outcome}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--one",action="store_true")
 ap.add_argument("--case",choices=CASES)
 ap.add_argument("--backend",choices=BACKENDS)
 ap.add_argument("--method",choices=METHODS)
 ap.add_argument("--strategy",choices=STRATEGIES)
 args=ap.parse_args()
 if args.one:
  print(json.dumps(one(args.case,args.backend,args.method,args.strategy),sort_keys=True,default=str))
  return 0
 OUT.mkdir(parents=True,exist_ok=True)
 manifest={"schema":"qpeexact8-independent-method-backend-isolation-v1",
           "source_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
           "python":sys.version,"platform":platform.platform(),
           "source_sha256":filehash(__file__),
           "gpmc":None,"oracles":{},
           "methods":METHODS,"strategies":STRATEGIES,"backends":BACKENDS,
           "native_timeout_seconds":NATIVE_TIMEOUT,"child_timeout_seconds":CHILD_TIMEOUT}
 with WMC("gpmc") as binary:
  manifest["gpmc"]={"sha256":filehash(binary),"path":str(binary.resolve())}
  os.environ["QUPRS_GPMC_PATH"]=str(binary.resolve())
  errors=[]
  for name in CASES:
   info=oracle(name)
   manifest["oracles"][name]=info
  if tuple(manifest["oracles"]["qpeexact8"]["input_qasm_sha256"])!=EXPECTED_QPE8_HASHES:
   errors.append("QPEexact8 input SHA differs from accepted independent oracle")
  emit(OUT/"environment.json",manifest)
  results=[]
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
        sub=subprocess.run(command,capture_output=True,text=True,
                           timeout=CHILD_TIMEOUT,env=os.environ.copy())
        try:data=json.loads(sub.stdout)
        except Exception:data={"status":"UNPARSEABLE","error":sub.stdout[-2000:],
                              "stderr":sub.stderr[-2000:]}
        entry={"key":key,"exit":sub.returncode,"stderr":sub.stderr[-4000:],
               "data":data}
       except subprocess.TimeoutExpired as e:
        entry={"key":key,"exit":None,"data":{"status":"HARD_TIMEOUT","error":repr(e)}}
       emit(OUT/"individual"/f"{key}.json",entry)
       fp.write(json.dumps(entry,sort_keys=True,default=str)+"\n")
       results.append(entry)
       print("QPE_METHOD",key,entry["data"]["status"],flush=True)
  anomaly=[]
  for e in results:
   d=e["data"]
   case=d.get("case")
   if e["exit"]!=0 or d.get("error") or d.get("status") in ("HARD_TIMEOUT","UNPARSEABLE"):
    anomaly.append({"key":e["key"],"kind":"RUN_INCONCLUSIVE_OR_ERROR","status":d.get("status")})
    continue
   oracle_st=manifest["oracles"][case]["classification"]
   status=d["status"]
   # A genuine global-phase equivalence may be reported as exact equality
   # by a method normalizing phase. Either equivalent status is valid.
   if oracle_st in ("equivalent","equivalent*") and status=="not_equivalent":
    anomaly.append({"key":e["key"],"kind":"FALSE_NEGATIVE","status":status})
   elif oracle_st=="not_equivalent" and status in ("equivalent","equivalent*"):
    anomaly.append({"key":e["key"],"kind":"FALSE_POSITIVE","status":status})
   if d["input_qasm_sha256"]!=manifest["oracles"][case]["input_qasm_sha256"]:
    anomaly.append({"key":e["key"],"kind":"INPUT_IDENTITY_MISMATCH"})
   if d["backend"]=="rust" and d["metrics"].get("gate_counts") != manifest["oracles"][case]["qasm_qiskit_gate_counts"]:
    anomaly.append({"key":e["key"],"kind":"RUST_QASM_PARSER_GATE_COUNT_MISMATCH",
                    "observed":d["metrics"].get("gate_counts")})
  blockers=errors+anomaly
  summary={"status":"SCIENCE_BLOCKED" if blockers else "PASS_METHOD_PARITY",
           "schema":manifest["schema"],"expected_records":len(CASES)*len(METHODS)*len(STRATEGIES)*len(BACKENDS),
           "raw_records":len(results),"issues":blockers,
           "result_matrix":[{"case":e["data"].get("case"),
                             "method":e["data"].get("method"),
                             "backend":e["data"].get("backend"),
                             "strategy":e["data"].get("strategy"),
                             "status":e["data"].get("status"),
                             "spawns":(e["data"].get("metrics",{}).get("stage_ledger") or {}).get("solver_child_spawns")}
                            for e in results],
           "limitations":["An unknown or timeout is an INCONCLUSIVE result, not equivalence.",
                          "The independent Qiskit unitary oracle is not influenced by native PathSum or WMC.",
                          "This experiment does not modify semantic thresholds or fallback behavior.",
                          "A diagnostic job may fail SCIENCE_BLOCKED while preserving all original JSON and digests."]}
  emit(OUT/"summary.json",summary)
  print(json.dumps({"status":summary["status"],"records":len(results),
                    "blocking":len(blockers)}),flush=True)
  return 2 if blockers else 0

if __name__=="__main__":sys.exit(main())

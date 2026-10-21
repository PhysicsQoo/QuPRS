#!/usr/bin/env python3
"""Find native, actual-QASM successful Elim and evaluate family-held-out costs.

Research discovery, not a production scheduler. Timeout/inconclusive counted,
not silently imputed as zero cost or a successful equivalence proof.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time

from QuPRS import _pathsum_rust
from QuPRS.utils import WMC

ROOT=Path("benchmarks/MQTBench").resolve()
OUT=Path("independent-family-cost-results").resolve()
# Eleven distinct real circuit families/case configurations not in the
# previously reported six-family pilot. One source input and one transformed
# equivalent input per case, without constructing synthetic PathSum fixtures.
FAMILIES={
 "qnn":("qnn_nativegates_ibm_qiskit_opt0_4.qasm",False),
 "wstate":("wstate_nativegates_ibm_qiskit_opt0_4.qasm",False),
 "qwalk":("qwalk-noancilla_nativegates_ibm_qiskit_opt0_3.qasm",False),
 "qpeexact":("qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",True),
 "qpeinexact":("qpeinexact_nativegates_ibm_qiskit_opt0_8.qasm",True),
 "qaoa":("qaoa_nativegates_ibm_qiskit_opt0_9.qasm",False),
 "qft":("qft_nativegates_ibm_qiskit_opt0_20.qasm",True),
 "ghz":("ghz_nativegates_ibm_qiskit_opt0_64.qasm",True),
 "vqe":("vqe_nativegates_ibm_qiskit_opt0_8.qasm",False),
 "grover":("grover-noancilla_nativegates_ibm_qiskit_opt0_5.qasm",True),
 "graphstate":("graphstate_nativegates_ibm_qiskit_opt0_32.qasm",False),
}
STRATEGIES=("Naive","Proportional")
RULES=("candidate_discovery","hh","omega")
SEED=112071

def sha(p):
 return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
def cmd(args):
 try:
  p=subprocess.run(args,capture_output=True,text=True,timeout=45)
  return {"exit":p.returncode,"stdout":p.stdout[-10000:],"stderr":p.stderr[-10000:]}
 except Exception as e: return {"error":repr(e)}
def pairs(family):
 name,rev=FAMILIES[family]
 pair=(ROOT/name,ROOT/"h,ry,rz,cx"/name)
 if not all(p.is_file() for p in pair): raise FileNotFoundError(str(pair))
 return pair[::-1] if rev else pair

def one(family,strategy):
 pair=pairs(family)
 os.environ["QUPRS_STAGE_LEDGER"]="1"
 os.environ["QUPRS_ELIM_TIMING"]="1"
 os.environ["QUPRS_OTHER_RULE_TIMING"]="1"
 with WMC("gpmc") as binary:
  if binary.resolve()!=Path(os.environ["QUPRS_GPMC_PATH"]).resolve():
   raise RuntimeError("GPMC identity mismatch")
  begin=time.perf_counter_ns()
  native=_pathsum_rust.check_equivalence(
   str(pair[0]),str(pair[1]),method="hybrid",
   strategy=strategy,tool_name="gpmc",timeout=25)
  wrapper_ns=time.perf_counter_ns()-begin
 ledger=native.get("stage_ledger")
 errs=[]
 if not isinstance(ledger,dict): errs.append("missing stage ledger")
 else:
  if ledger["has_stage_overlap"] or abs(ledger["closure_error_seconds"])>1e-6:
   errs.append("exclusive native stage closure/overlap")
  if abs(sum(ledger["exclusive_seconds"].values())-ledger["total_native_wall_seconds"])>1e-6:
   errs.append("invalid mutually exclusive native accounting")
  structural=ledger.get("structural_elim_attempts",[])
  elim=ledger.get("elim_attempt_timings",[])
  other=ledger.get("other_rule_timings",[])
  if len(structural)!=len(elim): errs.append("Elim structural sample alignment mismatch")
  for i,x in enumerate(elim):
   if x["structural_index"]!=i or type(x["success"]) is not bool or x["elapsed_ns"]<0:
    errs.append("bad Elim index/outcome/time")
  for x in other:
   if x["rule"] not in RULES or type(x["success"]) is not bool or x["elapsed_ns"]<0:
    errs.append("bad HH/Omega/discovery index/outcome/time")
  # Native Engine: every rule call is inside full_reduce() in this path.
  nested=(sum(x["elapsed_ns"] for x in elim)+sum(
    x["elapsed_ns"] for x in other if x["within_reduction"]))/1e9
  if nested>ledger["exclusive_seconds"]["reduction"]+1e-5:
   errs.append("nested rule time exceeds root Reduction")
 if native["status"]=="Not Equivalent":errs.append("unexpected inequivalence in MQTBench pair")
 return {
  "schema":"quprs-independent-real-circuit-rule-cost-v1",
  "family":family,"strategy":strategy,
  "source_files":[str(x.relative_to(ROOT)) for x in pair],
  "source_sha256":[sha(x) for x in pair],
  "extension":str(Path(_pathsum_rust.__file__).resolve()),
  "status":native["status"],"stats":native["stats"],
  "phase_sha256":hashlib.sha256(native["final_ps"].encode()).hexdigest(),
  "ffi_ns":wrapper_ns,"engine_sec":native["verification_time_sec"],
  "stage_ledger":ledger,"errors":errs,
 }

def models(rows,record_type,subset=None):
 # Each family is a real independent circuit FAMILY, both strategies are
 # correlated replicates; keep the entire family in only one fold.
 import numpy as np
 if record_type=="elim":
  table=[{"family":v["family"],"success":int(t["success"]),
     "elapsed_ns":t["elapsed_ns"],"k":s["k_r"],"l":s["l_r"],
     "v":s["v_r"],"d":s["d_r"]}
     for v in rows if v["status"].startswith("Equivalent") for s,t in
     zip(v["stage_ledger"]["structural_elim_attempts"],
         v["stage_ledger"]["elim_attempt_timings"])]
  variants={"constant":[],"L":["l"],"K+L":["k","l"],"K+L+V+D":["k","l","v","d"]}
 else:
  table=[{"family":v["family"],"success":int(t["success"]),
      "elapsed_ns":t["elapsed_ns"],"k":t["candidate_count"]}
      for v in rows if v["status"].startswith("Equivalent")
      for t in v["stage_ledger"]["other_rule_timings"]
      if t["rule"]==record_type]
  variants={"constant":[],"candidate_count":["k"],"candidate_count+success":["k","success"]}
 if subset is not None:
  table=[v for v in table if v["success"]==subset]
 families=sorted({t["family"] for t in table})
 if len(families)<4 or len(table)<30:
  return {"status":"INSUFFICIENT_INDEPENDENT_FAMILIES",
          "family_count":len(families),"events":len(table),
          "families":families}
 errors={m:{} for m in variants}
 for held in families:
  train=[x for x in table if x["family"]!=held]
  test=[x for x in table if x["family"]==held]
  weights=np.asarray([1/sum(y["family"]==x["family"] for y in train)
                      for x in train],dtype=float)
  weights/=weights.sum()
  y=np.log(np.maximum(1,np.array([x["elapsed_ns"] for x in train])))
  true=np.log(np.maximum(1,np.array([x["elapsed_ns"] for x in test])))
  mean=float(weights@y)
  for label,fs in variants.items():
   if not fs:
    pred=np.full(len(test),mean)
   else:
    train_x=np.array([[math.log1p(x[f]) for f in fs] for x in train],dtype=float)
    test_x=np.array([[math.log1p(x[f]) for f in fs] for x in test],dtype=float)
    mu=weights@train_x
    sd=np.sqrt(weights@((train_x-mu)**2))
    sd[sd<1e-8]=1
    z=(train_x-mu)/sd
    zt=(test_x-mu)/sd
    alpha=.02
    beta=np.linalg.solve(z.T@(weights[:,None]*z)+alpha*np.eye(len(fs)),
                         z.T@(weights*(y-mean)))
    pred=mean+zt@beta
   errors[label][held]=float(np.mean(np.abs(true-pred)))
 macro={m:statistics.mean(errors[m].values()) for m in variants}
 return {"status":"EXPLORATORY_POST_HOC_LOFO","families":families,
         "events":len(table),"macro_mae_log_ns":macro,
         "per_family_mae_log_ns":errors,
         "model_selection":"post hoc; not independent preregistered validation",
         "fit":"family-equal weighted ridge alpha 0.02; log1p predictors, train-fold scaling",
         "target":"log rule elapsed_ns; direct event observations, within-family correlated"}

def experiment():
 OUT.mkdir(parents=True,exist_ok=True)
 affinity=sorted(os.sched_getaffinity(0))
 os.sched_setaffinity(0,{affinity[0]})
 os.environ.update(PYTHONHASHSEED="0",OMP_NUM_THREADS="1",
                   OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1")
 with WMC("gpmc") as binary:
  binary=binary.resolve()
  os.environ["QUPRS_GPMC_PATH"]=str(binary)
  manifest={
   "schema":"quprs-independent-real-circuit-rule-cost-v1",
   "git_head":cmd(["git","rev-parse","HEAD"]),
   "gpmc_gitlink":cmd(["git","rev-parse","HEAD:GPMC"]),
   "gpmc_binary_sha256":sha(binary),"runner_sha256":sha(Path(__file__)),
   "cpu":cmd(["lscpu"]),"affinity_original":affinity,
   "affinity_used":affinity[0],"python":sys.version,"host":platform.platform(),
   "packages":cmd([sys.executable,"-m","pip","freeze"]),
   "cases":{f:[sha(p) for p in pairs(f)] for f in FAMILIES},
   "strategies":STRATEGIES,"native_timeout_sec":25,"hard_timeout_sec":40,
  }
  write(OUT/"environment.json",manifest)
  schedule=[(f,s) for f in FAMILIES for s in STRATEGIES]
  random.Random(SEED).shuffle(schedule)
  observed,errors=[],[]
  with (OUT/"samples.jsonl").open("w",buffering=1) as fp:
   for index,(family,strategy) in enumerate(schedule):
    path=OUT/"individual"/f"{index:02d}_{family}_{strategy}.json"
    p=subprocess.run([sys.executable,"-u",str(Path(__file__).resolve()),
                     "--one","--family",family,"--strategy",strategy],
                     capture_output=True,text=True,timeout=40,env=os.environ.copy())
    row={"family":family,"strategy":strategy,"idx":index,
         "raw_file":str(path.relative_to(OUT)),"returncode":p.returncode,
         "stderr":p.stderr[-4000:]}
    if p.returncode==0:
     try:
      data=json.loads(p.stdout)
      row["data"]=data
      write(path,data)
      if data["errors"]:errors.append({"idx":index,"errors":data["errors"]})
     except ValueError as e:
      errors.append({"idx":index,"error":repr(e)})
    else:
     # Native timeout/unknown is INCONCLUSIVE, not a fabricated success,
     # but a subprocess crash or invalid JSON is a hard collection error.
     errors.append({"idx":index,"error":"PROCESS_FAILURE","stderr":row["stderr"]})
    fp.write(json.dumps(row,sort_keys=True)+"\n")
    observed.append(row)
    print("DISCOVERY",index,family,strategy,row["returncode"],flush=True)
    if errors:break
  data=[x["data"] for x in observed if "data" in x]
  qualified=[x for x in data if x["status"].startswith("Equivalent")]
  coverage={r:{
     "attempts":sum(len(x["stage_ledger"]["other_rule_timings"])
                if r!="elim" else len(x["stage_ledger"]["elim_attempt_timings"])
                for x in qualified) if r=="elim" else
                sum(sum(t["rule"]==r for t in x["stage_ledger"]["other_rule_timings"]) for x in qualified),
     "successes":sum(sum(t["success"] for t in (x["stage_ledger"]["elim_attempt_timings"]
                   if r=="elim" else [s for s in x["stage_ledger"]["other_rule_timings"] if s["rule"]==r]))
                   for x in qualified)}
    for r in ("elim","hh","omega","candidate_discovery")}
  success_families=sorted({x["family"] for x in qualified
     if any(t["success"] for t in x["stage_ledger"]["elim_attempt_timings"])})
  analysis={}
  if not errors:
   for rule in ("elim","hh","omega"):
    analysis[rule]={"overall":models(qualified,rule),
                    "successful_only":models(qualified,rule,1),
                    "failed_only":models(qualified,rule,0)}
  summary={"schema":manifest["schema"],
   "status":"PASS_DISCOVERY_NO_SUCCESSFUL_ELIM" if not success_families and not errors
      else "PASS_DISCOVERY_WITH_SUCCESSFUL_ELIM" if not errors else "INCOMPLETE",
   "samples":len(observed),"equivalent_samples":len(qualified),
   "families":list(FAMILIES),"genuine_successful_elim_families":success_families,
   "coverage":coverage,"comparisons":analysis,"errors":errors,
   "limits":["Only genuine existing MQTBench QASM pair tests (no synthetic PathSum fixtures).",
     "Multiple strategies per family share a circuit structure and must remain in same fold.",
     "Independent test families fewer than 4 or successful events sparse => no supported model generalization.",
     "Elim, HH, Omega rule clocks include Instant/RAII observer cost and correlated calls.",
     "Prospective out-of-sample verification not possible on families selected after past runs.",
     "A run with zero successful Elim must be reported explicitly, not silently merged with synthetic successes.",
     "Results are scientific discovery, not permission to change production scheduler or solver."]}
  write(OUT/"summary.json",summary)
  (OUT/"summary.md").write_text(
     f"# Genuine-QASM Elim success discovery\n\nStatus: {summary['status']}\n\n"
     f"Samples: {len(observed)} / {len(schedule)}.\n"
     f"Equivalent: {len(qualified)}.\n"
     f"Genuine successful Elim families: {', '.join(success_families) or 'NONE'}.\n\n"
     f"Rule coverage: {json.dumps(coverage,sort_keys=True)}\n\n"
     "Models are exploratory leave-one-entire-family-out, not deployed or prospective validation.\n")
  print(json.dumps({"status":summary["status"],"successful_elim_families":success_families,
                    "coverage":coverage,"samples":len(observed)},sort_keys=True),flush=True)
  return 0 if not errors else 2

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--one",action="store_true")
 p.add_argument("--family",choices=FAMILIES)
 p.add_argument("--strategy",choices=STRATEGIES)
 a=p.parse_args()
 if a.one:
  r=one(a.family,a.strategy)
  print(json.dumps(r,sort_keys=True))
  return 0 if not r["errors"] else 2
 return experiment()
if __name__=="__main__":
 sys.exit(main())

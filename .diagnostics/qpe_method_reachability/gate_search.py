#!/usr/bin/env python3
"""Observe actual successful Elim from valid gate-QASM, not synthetic PathSum.

Seeded 2/3-qubit unitary-equivalent circuit pairs, proven by independent
Qiskit matrices before native reduction_rules execution. No scheduler edits.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
import numpy as np
from QuPRS import _pathsum_rust

OUT=Path("qasm-gate-elim-reachability-results")
STRATEGIES=("Naive","Proportional","Straightforward")
PATTERNS=("inverse_pair","sandwich","clifford_inverse","phase_global",
          "cz_decomposed","s_as_t2")
DEPTHS=(4,8,12)
QUBITS=(2,3)
SEEDS=(112134,112135)
EXPECTED_CASES=len(PATTERNS)*len(DEPTHS)*len(QUBITS)*len(SEEDS)

def save(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")

def sha(data):
 return hashlib.sha256(data.encode()).hexdigest()

def random_body(n,depth,seed,clifford=False):
 rng=random.Random(seed)
 qc=QuantumCircuit(n)
 for _ in range(depth):
  gate=rng.choice(("h","s","x","z","cx","cz")
                  if clifford else ("h","s","sdg","t","tdg","x","z","cx","cz"))
  if gate in ("cx","cz"):
   c=rng.randrange(n);t=(c+1+rng.randrange(n-1))%n
   getattr(qc,gate)(c,t)
  else:getattr(qc,gate)(rng.randrange(n))
 return qc

def create(n,depth,pattern,seed):
 body=random_body(n,depth,seed,clifford=(pattern=="clifford_inverse"))
 lhs=QuantumCircuit(n)
 rhs=QuantumCircuit(n)
 if pattern in ("inverse_pair","clifford_inverse"):
  rhs.compose(body,inplace=True);rhs.compose(body.inverse(),inplace=True)
 elif pattern=="sandwich":
  lhs.compose(body,inplace=True)
  rhs.compose(body,inplace=True);rhs.compose(body.inverse(),inplace=True);rhs.compose(body,inplace=True)
 elif pattern=="phase_global":
  lhs.compose(body,inplace=True)
  rhs.compose(body,inplace=True)
  for gate in ("x","z","x","z"):
   getattr(rhs,gate)(0)
 elif pattern=="cz_decomposed":
  lhs.compose(body,inplace=True);lhs.cz(0,1)
  rhs.compose(body,inplace=True);rhs.h(1);rhs.cx(0,1);rhs.h(1)
 elif pattern=="s_as_t2":
  lhs.compose(body,inplace=True);lhs.s(0)
  rhs.compose(body,inplace=True);rhs.t(0);rhs.t(0)
 else:raise ValueError(pattern)
 return qasm2.dumps(lhs),qasm2.dumps(rhs)

def certify(lhs,rhs):
 a=Operator(qasm2.loads(lhs)).data
 b=Operator(qasm2.loads(rhs)).data
 z=np.vdot(b.reshape(-1),a.reshape(-1))
 if abs(z)<1e-14: raise RuntimeError("phase vanishes")
 phi=z/abs(z)
 residual=float(np.abs(a-phi*b).max())
 if residual>1e-10:raise RuntimeError("not unitary equivalent: "+str(residual))
 return residual

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 os.environ["QUPRS_STAGE_LEDGER"]="1"
 os.environ["QUPRS_ELIM_TIMING"]="1"
 os.environ["QUPRS_OTHER_RULE_TIMING"]="1"
 manifest={"schema":"quprs-genuine-quantum-gate-qasm-elim-reachability-v2",
           "source_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
           "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "seed_values":SEEDS,"strategies":STRATEGIES,"qubits":QUBITS,
           "depths":DEPTHS,"patterns":PATTERNS,
           "python":sys.version,"platform":platform.platform(),
           "extension":str(Path(_pathsum_rust.__file__).resolve())}
 save(OUT/"environment.json",manifest)
 entries=[];positive=[];anomalies=[];idx=0
 with (OUT/"samples.jsonl").open("w",buffering=1) as f:
  for n in QUBITS:
   for depth in DEPTHS:
    for pattern in PATTERNS:
     for seed in SEEDS:
      lhs,rhs=create(n,depth,pattern,seed+n*101+depth*17)
      independent_error=certify(lhs,rhs)
      key=f"{idx:03d}_{n}q_{depth}_{pattern}_{seed}"
      dest=OUT/"qasm"/key
      dest.mkdir(parents=True,exist_ok=True)
      (dest/"left.qasm").write_text(lhs)
      (dest/"right.qasm").write_text(rhs)
      for strategy in STRATEGIES:
       try:
        r=_pathsum_rust.check_equivalence(
          lhs,rhs,method="reduction_rules",strategy=strategy,timeout=20)
        stage=r.get("stage_ledger")
        stats=r.get("stats",{})
        status=r.get("status")
        issue=[]
        if not stage:issue.append("MISSING_DIAGNOSTICS")
        if status not in ("Equivalent","Equivalent (Up to Global Phase)"):
         issue.append("NATIVE_DISAGREES_WITH_QISKIT_OR_UNDECIDED")
        elapsed=(stage or {}).get("elim_attempt_timings",[])
        if len(elapsed)!=(stats.get("elim_attempts") or 0):
         issue.append("ELIM_ATTEMPT_INDEX_MISMATCH")
        hits=sum(int(t["success"]) for t in elapsed)
        if hits!=(stats.get("elim_hits") or 0):issue.append("ELIM_SUCCESS_COUNT_MISMATCH")
        row={"case":key,"n":n,"depth":depth,"pattern":pattern,"seed":seed,
             "strategy":strategy,"status":status,"stats":stats,"qasm_max_unitary_error":independent_error,
             "qasm_sha256":[sha(lhs),sha(rhs)],
             "gates_reference":len(qasm2.loads(lhs).data),
             "gates_candidate":len(qasm2.loads(rhs).data),
             "rust_gate_counts":[r.get("gates1"),r.get("gates2")],
             "stage_ledger":stage,"elapsed_seconds":r.get("verification_time_sec"),
             "problems":issue}
        if row["rust_gate_counts"]!=[row["gates_reference"],row["gates_candidate"]]:
         row["problems"].append("RUST_QASM_GATE_COUNT_MISMATCH")
        if hits:positive.append({"case":key,"strategy":strategy,"elim_hits":hits})
       except Exception as exc:
        row={"case":key,"strategy":strategy,"status":"EXCEPTION",
             "problems":["EXCEPTION: "+repr(exc)]}
       if row["problems"]:anomalies.append({"case":key,"strategy":strategy,"errors":row["problems"]})
       save(OUT/"individual"/f"{key}_{strategy}.json",row)
       f.write(json.dumps(row,sort_keys=True)+"\n")
       entries.append(row)
       print("QASM_ELIM",key,strategy,row["status"],
             row.get("stats",{}).get("elim_hits"),flush=True)
      idx+=1
 summary={"schema":manifest["schema"],
          "status":"SCIENCE_BLOCKED_SEMANTIC_PARITY" if anomalies else
                   "PASS_DISCOVERY_WITH_GENUINE_GATE_ELIM" if positive else
                   "PASS_DISCOVERY_NO_GENUINE_GATE_ELIM",
          "independent_engineered_qasm_pairs":idx,
          "native_calls":len(entries),"expected_native_calls":EXPECTED_CASES*len(STRATEGIES),
          "positive_witnesses":positive,"anomalies":anomalies,
          "totals":{gate:sum(r.get("stats",{}).get(gate+"_hits",0) for r in entries)
                   for gate in ("elim","hh","omega")},
          "limitations":["All inputs are syntactically valid gates and pass Qiskit dense-unitary equality.",
                         "Engineered identities/sandwiches are NOT independent natural circuit algorithm families.",
                         "No successes does NOT mathematically establish Elim is unreachable.",
                         "Uses direct reduction_rules, not full hybrid WMC.",
                         "No adaptive scheduling or performance thresholds changed."]}
 save(OUT/"summary.json",summary)
 print("GATE_REACHABILITY",summary["status"],len(entries),len(positive),flush=True)
 if len(entries)!=EXPECTED_CASES*len(STRATEGIES):return 2
 return 2 if anomalies else 0

if __name__=="__main__":raise SystemExit(main())

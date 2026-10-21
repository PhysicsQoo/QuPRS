#!/usr/bin/env python3
"""Search real quantum-gate QASM, not synthetic PathSum, for native Elim hits.

Seeded short Clifford/T inverse/sandwich circuits are certified by dense
Qiskit unitaries up to global phase before calling actual Rust reduction.
Engineered identities are NOT independent natural algorithm families.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import sys

import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
from QuPRS import _pathsum_rust

OUT=Path("real-gate-elim-search-results").resolve()
SEED=112071
COUNTS=(2,3,4,5)
DEPTHS=(4,8,12)
PATTERNS=("inverse","sandwich","bell_inverse","ghz_inverse","clifford_inverse")

def dump(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")

def sha(data):
 return hashlib.sha256(data.encode()).hexdigest()

def generate(n,depth,pattern,seed):
 rng=random.Random(seed)
 body=QuantumCircuit(n)
 if pattern=="bell_inverse":
  body.h(0);body.cx(0,1)
 elif pattern=="ghz_inverse":
  body.h(0)
  for i in range(n-1):body.cx(i,i+1)
 else:
  for i in range(depth):
   gate=rng.choice(["h","x","s","z","cx","t"]
                   if pattern!="clifford_inverse" else ["h","x","s","z","cx"])
   if gate=="cx":
    c=rng.randrange(n);t=(c+1+rng.randrange(n-1))%n;body.cx(c,t)
   else:getattr(body,gate)(rng.randrange(n))
 if pattern=="sandwich":
  candidate=body.compose(body.inverse()).compose(body)
  reference=body
 else:
  candidate=body.compose(body.inverse())
  reference=QuantumCircuit(n)
 return qasm2.dumps(reference),qasm2.dumps(candidate)

def check_unitary(original,candidate):
 a=Operator(qasm2.loads(original)).data
 b=Operator(qasm2.loads(candidate)).data
 z=np.vdot(a.reshape(-1),b.reshape(-1))
 if abs(z)<1e-14:raise ValueError("no phase for comparison")
 phase=z/abs(z)
 error=float(np.max(np.abs(b-phase*a)))
 if error>=1e-9:raise ValueError(f"Qiskit independently finds unequal {error}")
 return error

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 os.environ["QUPRS_STAGE_LEDGER"]="1"
 os.environ["QUPRS_ELIM_TIMING"]="1"
 os.environ["QUPRS_OTHER_RULE_TIMING"]="1"
 rows=[];positives=[];anomalies=[]
 for n in COUNTS:
  for depth in DEPTHS:
   for pattern in PATTERNS:
    idx=len(rows)
    original,transformed=generate(n,depth,pattern,SEED+idx*101)
    external_residual=check_unitary(original,transformed)
    dest=OUT/"qasm"/f"{idx:03d}_{n}q_{pattern}_{depth}"
    dest.mkdir(parents=True,exist_ok=True)
    (dest/"reference.qasm").write_text(original)
    (dest/"candidate.qasm").write_text(transformed)
    native=_pathsum_rust.check_equivalence(
      original,transformed,method="reduction_rules",
      strategy="Proportional",timeout=12
    )
    stage=native.get("stage_ledger")
    if stage is None:raise RuntimeError("Missing native stage ledger")
    state=native["status"]
    hh=native["stats"]["hh_hits"]
    omega=native["stats"]["omega_hits"]
    elim=native["stats"]["elim_hits"]
    if state=="Not Equivalent":
     anomalies.append({"index":idx,"kind":"NATIVE_REJECTS_QISKIT_EQUIVALENT_QASM"})
    if elim:
     positives.append({"index":idx,"qubits":n,"depth":depth,
                       "pattern":pattern,"elim_hits":elim,"status":state})
    row={"index":idx,"n":n,"depth":depth,"pattern":pattern,
         "status":state,"qiskit_max_unitary_residual":external_residual,
         "sha256_qasm":[sha(original),sha(transformed)],
         "stats":native["stats"],"elim_successes":elim,
         "hh_successes":hh,"omega_successes":omega,
         "native_elapsed_seconds":native["verification_time_sec"],
         "stage_ledger":stage,"qasm_dir":str(dest.relative_to(OUT))}
    dump(OUT/"individual"/f"{idx:03d}.json",row)
    rows.append(row)
    print("GATE_ELIM",idx,n,depth,pattern,state,elim,flush=True)
 with (OUT/"samples.jsonl").open("w") as f:
  for row in rows:f.write(json.dumps(row,sort_keys=True)+"\n")
 result={"schema":"quprs-valid-gate-qasm-elim-discovery-v1",
         "status":"INCOMPLETE_REFERENCE_PARITY" if anomalies else
                  "PASS_DISCOVERY_WITH_ELIM" if positives else
                  "PASS_DISCOVERY_NO_ELIM",
         "seed":SEED,"expected":len(COUNTS)*len(DEPTHS)*len(PATTERNS),
         "collected":len(rows),"positives":positives,"anomalies":anomalies,
         "rust":str(Path(_pathsum_rust.__file__).resolve()),
         "python":platform.python_version(),
         "max_qiskit_unitary_residual":max(x["qiskit_max_unitary_residual"] for x in rows),
         "total_rule_successes":{
           name:sum(r[name+"_successes"] for r in rows) for name in ("elim","hh","omega")},
         "limitations":["Engineered genuine QASM gate sequences, not natural algorithm benchmark families.",
           "Each reference pair was independently certified with Qiskit Operator modulo global phase.",
           "All cases include inverse/sandwich identity structures; population is intentionally biased.",
           "A successful Elim is an observed reachability fixture, not evidence of natural frequency or predictive generalization.",
           "Native reduction_rules is not the same as full hybrid solver completion.",
           "No production solver/scheduler modifications or speedup claims."]}
 dump(OUT/"summary.json",result)
 (OUT/"summary.md").write_text("# Real-gate QASM Elim discovery\n\n"
   f"Status: {result['status']}.\n\n"
   f"Valid Qiskit-certified pairs: {len(rows)}. Native Elim-positive cases: {len(positives)}.\n\n"
   f"Total hits: {result['total_rule_successes']}.\n\n"
   "Engineered physical circuits are not independent algorithm families.\n")
 print(json.dumps({"status":result["status"],"positives":len(positives),
                   "collected":len(rows),"anomalies":len(anomalies)}),flush=True)
 return 0 if not anomalies else 2

if __name__=="__main__":sys.exit(main())

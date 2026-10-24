#!/usr/bin/env python3
"""Report repeated QAOA7 native Rust walltimes for one pinned installation."""
import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path
from QuPRS import check_equivalence
p=argparse.ArgumentParser()
p.add_argument("--label",required=True)
p.add_argument("--batch",type=int,required=True)
p.add_argument("--output",type=Path,required=True)
a=p.parse_args()
name="qaoa_nativegates_ibm_qiskit_opt0_7.qasm"
inputs=(Path("benchmarks/MQTBench")/name,
        Path("benchmarks/MQTBench/h,ry,rz,cx")/name)
hashes=[hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs]
records={}
for solver in ("gpmc","ganak"):
    sample=[]
    verdicts=set()
    for i in range(23):
        before=time.perf_counter_ns()
        result=check_equivalence(str(inputs[0]),str(inputs[1]),
                                 backend="rust",method="hybrid",
                                 strategy="proportional",tool_name=solver,
                                 timeout=60)
        wall=(time.perf_counter_ns()-before)/1e9
        verdicts.add(str(result.equivalent))
        if i>=3: sample.append(wall)
    if len(verdicts)!=1: raise ValueError("Nondeterministic native verdict")
    records[solver]={"wall_seconds":sample,"verdict":next(iter(verdicts)),
                     "median":statistics.median(sample)}
output={"label":a.label,"batch":a.batch,"input_sha256":hashes,"solvers":records}
a.output.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
print(a.label,a.batch,{k:v["median"] for k,v in records.items()})

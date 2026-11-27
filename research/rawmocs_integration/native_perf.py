"""P4.4 bounded paired transport study; no algorithm-speedup inference."""
import argparse
from contextlib import nullcontext
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

import rawmocs
from QuPRS import check_equivalence
from QuPRS.interface.ps2wmc import run_wmc
from QuPRS.utils import solver_process
from rawmocs_quprs import registered_rawmocs, RawAdapter
from native_adapter import registered_native
from benchmarks.codspeed.case_registry import SOLVER_CPU_CASES

ROOT = Path(".p4-native-evidence").resolve()
RAW = Path(".rawmocs-candidate/crates/rawmocs-cli/target/release/rawmocs").resolve()
GPMC = Path(".gpmc/build/gpmc").resolve()
ARMS = ("gpmc", "rawmocs", "rawmocs_native")
LIMIT = 2
DIGITS = 30
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def save(report):
    (ROOT/"performance.json").write_text(json.dumps(report,indent=2)+"\n")
def setup():
    os.environ["QUPRS_GPMC_PATH"]=str(GPMC)
def context(arm):
    return (registered_native(DIGITS) if arm=="rawmocs_native" else
            registered_rawmocs(RAW,digits=DIGITS,timeout_ms=LIMIT*1000,address_space_bytes=None)
            if arm=="rawmocs" else nullcontext())
def signature(row):
    return {k:row[k] for k in ("sat","real","imag","route")}
def measure(arm,path):
    external=[];native=[]
    original=solver_process.run
    original_native=rawmocs.solve_file
    def observe(cmd,timeout):
        result=original(cmd,timeout)
        external.append(result)
        return result
    def observe_native(*args,**kwargs):
        result=original_native(*args,**kwargs)
        native.append(result)
        return result
    with context(arm),patch.object(solver_process,"run",observe),patch.object(rawmocs,"solve_file",observe_native):
        start=time.perf_counter_ns()
        value=run_wmc(path,arm,timeout=LIMIT,preserve_count=True,
                      precision_digits=DIGITS if arm=="gpmc" else None)
        elapsed=time.perf_counter_ns()-start
    row=dict(wall_ns=elapsed,real=str(value.real),imag=str(value.imag),route=None,core_ns=None)
    if arm=="rawmocs_native":
        assert not external and len(native)==1
        n=native[0];assert n.digits==30 and n.precision_bits==100
        row.update(sat=n.sat,route=n.route,core_ns=n.solve_ns)
    else:
        assert not native and len(external)==1
        result=external[0];assert result.returncode==0
        if arm=="rawmocs":
            sat,count=RawAdapter.parse_protocol(result.stdout);assert count==value
            (route,ns),=re.findall(r"^RAWMOCS_COMPLETE route=(\w+) digits=30 bits=100 solve_ns=(\d+)",result.stderr,re.M)
            row.update(sat=sat,route=route,core_ns=int(ns))
        else:
            assert re.findall(r"^c o precision (\d+)\s*$",result.stdout,re.M)==["30"]
            sat,=re.findall(r"^s (SATISFIABLE|UNSATISFIABLE)\s*$",result.stdout,re.M)
            row["sat"]=sat=="SATISFIABLE"
    if row["core_ns"] is not None:
        row["non_core_wall_ns"]=elapsed-row["core_ns"]
    return row
def same(rows):
    g,c,n=(rows[a] for a in ARMS)
    assert signature(c)==signature(n),(c,n)
    assert g["sat"]==c["sat"]
    scale=max(Fraction(1),abs(Fraction(c["real"])),abs(Fraction(c["imag"])))
    assert max(abs(Fraction(g[k])-Fraction(c[k])) for k in ("real","imag"))<=scale*Fraction(1,10**24)
def export(name,path):
    _,filename,strategy,reverse,_,_=next(c for c in SOLVER_CPU_CASES if c[0]==name+"-gpmc-rust")
    root=Path("benchmarks/MQTBench")
    lhs,rhs=root/filename,root/"h,ry,rz,cx"/filename
    if reverse:lhs,rhs=rhs,lhs
    original=solver_process.run
    def observe(cmd,timeout):
        assert not path.exists()
        path.write_bytes(Path(cmd[-1]).read_bytes())
        return original(cmd,min(timeout,LIMIT))
    with patch.object(solver_process,"run",observe):
        result=check_equivalence(str(lhs),str(rhs),method="hybrid",strategy=strategy,
                                 backend="python",tool_name="gpmc",timeout=15)
    return dict(source=[str(lhs),str(rhs)],source_sha256=[digest(lhs),digest(rhs)],
                verdict=str(result.equivalent),invoked=bool(result.wmc_solver_invoked))
def prepare():
    setup();ROOT.mkdir(exist_ok=True)
    report=dict(status="IN_PROGRESS",digits=DIGITS,limit_s=LIMIT,cases={},
                quprs_sha=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
                rawmocs_sha=subprocess.check_output(["git","-C",".rawmocs-candidate","rev-parse","HEAD"],text=True).strip(),
                binaries={"rawmocs":digest(RAW),"gpmc":digest(GPMC),"native":digest(Path(rawmocs._native.__file__))})
    config=["options:",'  max-time: "3s"',"benchmarks:"]
    save(report)
    for name in ("complex","wide","vqe4","grover4"):
        path=ROOT/f"perf-{name}.cnf"
        case={"status":"PENDING"};report["cases"][name]=case
        if name=="complex":path.write_text("p cnf 1 1\nc t wmc\nc p weight 1 0.1 -0.3 0\n1 0\n")
        elif name=="wide":path.write_text("p cnf 10 1\nc t wmc\n1 2 3 4 5 6 7 8 9 10 0\n")
        else:
            try:case.update(export(name,path))
            except solver_process.SolverTimeout:
                case["status"]="EXPORT_CENSORED";save(report);continue
            if case["verdict"] not in ("equivalent","equivalent*") or not case["invoked"] or not path.exists():
                case["status"]="NOT_ADMITTED";save(report);continue
        case["cnf_sha256"]=digest(path)
        try:rows={a:measure(a,path) for a in ARMS}
        except solver_process.SolverTimeout:
            case["status"]="SCOUT_CENSORED";save(report);continue
        same(rows);case["scout"]=rows
        if max(v["wall_ns"] for v in rows.values())>500_000_000:
            case["status"]="TOO_LONG_FOR_SIMULATION";save(report);continue
        case["trials"]=[]
        for i in range(6):
            order=ARMS[i%3:]+ARMS[:i%3]
            if i>=3:order=order[::-1]
            assert digest(path)==case["cnf_sha256"]
            trial={a:measure(a,path) for a in order};same(trial)
            assert all(signature(trial[a])==signature(rows[a]) for a in ARMS)
            case["trials"].append(dict(order=list(order),rows=trial));save(report)
        case["p50"]={a:{k:statistics.median(t["rows"][a][k] for t in case["trials"])
                         for k in ("wall_ns","core_ns","non_core_wall_ns") if k in rows[a] and rows[a][k] is not None} for a in ARMS}
        case["status"]="ADMITTED";save(report)
        for arm in ARMS:
            wrapper=ROOT/f"perf-{name}-{arm}.sh"
            out=ROOT/f"perf-{name}-{arm}.simulation.json"
            cmd=[sys.executable,str(Path(__file__).resolve()),"sample",name,arm]
            wrapper.write_text("#!/bin/sh\nset -eu\nexec "+shlex.join(cmd)+" >"+shlex.quote(str(out))+"\n")
            wrapper.chmod(0o755)
            config.extend([f'  - name: "rawmocs_python_transport/{name}/{arm}_mpfr100"',f'    exec: "{wrapper}"'])
    assert all(report["cases"][n]["status"]=="ADMITTED" for n in ("complex","wide"))
    report["status"]="WALLTIME_PASS";save(report)
    Path("codspeed-p4-transport.generated.yml").write_text("\n".join(config)+"\n")
    print("P4_TRANSPORT_WALLTIME",json.dumps({n:{"status":c["status"],"p50":c.get("p50")} for n,c in report["cases"].items()}),flush=True)
def sample(name,arm):
    setup()
    # Three actual run_wmc calls per command; Python startup is included,
    # and child processes are tracked by CodSpeed. Not a solver-only metric.
    rows=[signature(measure(arm,ROOT/f"perf-{name}.cnf")) for _ in range(3)]
    print(json.dumps(rows))
def verify():
    report=json.loads((ROOT/"performance.json").read_text())
    assert report["status"]=="WALLTIME_PASS"
    for name,case in report["cases"].items():
        if case["status"]!="ADMITTED":continue
        assert digest(ROOT/f"perf-{name}.cnf")==case["cnf_sha256"]
        for arm in ARMS:
            rows=json.loads((ROOT/f"perf-{name}-{arm}.simulation.json").read_text())
            assert rows==[signature(case["scout"][arm])]*3
        case["simulation_parity"]="PASS"
    report["status"]="SIMULATION_OUTPUT_PARITY_PASS";save(report)
    print("P4_TRANSPORT_SIMULATION_PARITY_PASS",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("prepare","sample","verify"))
    p.add_argument("name",nargs="?");p.add_argument("arm",nargs="?")
    a=p.parse_args()
    if a.stage=="prepare":prepare()
    elif a.stage=="sample":sample(a.name,a.arm)
    else:verify()

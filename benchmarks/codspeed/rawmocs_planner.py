"""Bounded solver-only planner Simulation on captured native QuPRS residuals.

Keep the long/failed QFT22 workload out of Simulation. Capture once using the
actual native verifier, prove same source and compare native/Simulation output.
A successful run is evidence, not admission of a planning heuristic.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
from fractions import Fraction
from types import SimpleNamespace
import expanded_cohort as cohort
from expanded_cohort import digest, inspect, parity, save
from benchmarks.codspeed.case_registry import SOLVER_CPU_CASES

ROOT=Path(".rawmocs-planner-simulation").resolve()
CONFIG=Path("codspeed-rawmocs-planner.generated.yml")
RAW=Path(".rawmocs/crates/rawmocs-cli/target/release/rawmocs").resolve()
CANDIDATE=Path(".rawmocs-candidate/crates/rawmocs-cli/target/release/rawmocs").resolve()
GPMC=Path(".gpmc/build/gpmc").resolve()
BIN=Path("rust/target/release/examples/rawmocs_cohort").resolve()
ARMS=("baseline","candidate","gated","refine")
QFT16_HASH="c35ee4e3ce77faf21ae6c8cd39d2fe14d8cba9958abffb8f18857e4357c9ea22"

def command(arm,cnf):
    return [str(RAW if arm=="baseline" else CANDIDATE),"--digits","30",
            "--solver","prejoin","--timeout-ms","300000",str(cnf)]

def mode(arm):
    return {"gated":"2","refine":"3"}.get(arm)

def env_for(arm):
    env=os.environ.copy()
    for key in ("RAWMOCS_RESEARCH_PEAK_FIRST","RAWMOCS_RESEARCH_THREE_CUT","RAWMOCS_RESEARCH_RECYCLE_MOVE","RAWMOCS_RESEARCH_SUPPORT_FIRST"):
        env.pop(key,None)
    if mode(arm):env["RAWMOCS_RESEARCH_PEAK_FIRST"]=mode(arm)
    return env

def binaries():
    return {"baseline":digest(RAW),"candidate":digest(CANDIDATE),"gpmc":digest(GPMC),"verifier":digest(BIN)}

def prepare():
    ROOT.mkdir(exist_ok=True)
    report={"status":"PREPARING","digits":30,"bits":100,"binaries":binaries(),"cases":{}}
    config=["options:",'  max-time: "5s"',"benchmarks:"]
    def persist():save(ROOT/"report.json",report)
    for name in ("vqe4","qft16"):
        _,filename,_,reverse,_,_=next(c for c in SOLVER_CPU_CASES if c[0]==name+"-gpmc-rust")
        lhs=Path("benchmarks/MQTBench")/filename
        rhs=lhs.parent/"h,ry,rz,cx"/filename
        if reverse:lhs,rhs=rhs,lhs
        case_dir=ROOT/name;case_dir.mkdir(exist_ok=True)
        case={"source_sha256":[digest(lhs),digest(rhs)],"rows":{},"status":"PREPARING"}
        report["cases"][name]=case
        # Keep the source capture bounded; the fixture is already known short.
        cohort.LIMIT=2
        args=SimpleNamespace(raw=RAW,gpmc=GPMC,bin=BIN,out=case_dir)
        g=cohort.run(args,"gpmc",lhs,rhs,"gpmc-capture",True)
        case["gpmc"]=g;persist()
        assert g["status"]=="COMPLETED" and g["wall_s"]<=2,g
        cnf=case_dir/"gpmc-capture.cnf"
        case["cnf_sha256"]=digest(cnf)
        assert case["cnf_sha256"]==g["cnf_sha256"]
        if name=="qft16":assert case["cnf_sha256"]==QFT16_HASH
        for arm in ARMS:
            start=time.monotonic()
            proc=subprocess.run(["timeout","-k","1s","2s","prlimit","--as=3221225472","--",
                *command(arm,cnf)],env=env_for(arm),text=True,capture_output=True,timeout=5)
            row={"wall_s":time.monotonic()-start,"exit":proc.returncode,
                 "stdout":proc.stdout,"stderr":proc.stderr}
            case["rows"][arm]=row;persist()
            assert proc.returncode==0 and row["wall_s"]<=2,row
            row.update(inspect("rawmocs",proc.stdout,proc.stderr))
            assert row["route"]=="prejoin" and parity(g,row),row
            if arm in ("candidate","refine"):
                b=case["rows"]["gated" if arm=="refine" else "baseline"]
                assert row["sat"]==b["sat"] and all(Fraction(row[k])==Fraction(b[k]) for k in ("real","imag")),row
            assert digest(cnf)==case["cnf_sha256"]
            row["status"]="PREFLIGHT_PASS"
            runner=case_dir/(arm+".simulation.sh")
            stdout=case_dir/(arm+".simulation.stdout")
            stderr=case_dir/(arm+".simulation.stderr")
            runner.write_text("#!/bin/sh\nset -eu\nunset RAWMOCS_RESEARCH_PEAK_FIRST RAWMOCS_RESEARCH_THREE_CUT RAWMOCS_RESEARCH_RECYCLE_MOVE RAWMOCS_RESEARCH_SUPPORT_FIRST\n"
                + (f"export RAWMOCS_RESEARCH_PEAK_FIRST={mode(arm)}\n" if mode(arm) else "")
                + "exec "+shlex.join(command(arm,cnf))+" >"+shlex.quote(str(stdout))+" 2>"+shlex.quote(str(stderr))+"\n")
            runner.chmod(0o755)
            config.extend([f'  - name: "quprs_planner/{name}/{arm}_mpfr100"',f'    exec: "{runner}"'])
            persist()
        case["status"]="ADMITTED";persist()
    CONFIG.write_text("\n".join(config)+"\n")
    report["status"]="PREFLIGHT_COMPLETE";persist()
    print("PLANNER_SIMULATION_PREFLIGHT",json.dumps(report),flush=True)

def verify():
    report=json.loads((ROOT/"report.json").read_text())
    assert report["status"]=="PREFLIGHT_COMPLETE" and report["binaries"]==binaries()
    for name,case in report["cases"].items():
        case_dir=ROOT/name
        assert digest(case_dir/"gpmc-capture.cnf")==case["cnf_sha256"]
        for arm in ARMS:
            out=(case_dir/(arm+".simulation.stdout")).read_text()
            err=(case_dir/(arm+".simulation.stderr")).read_text()
            row=inspect("rawmocs",out,err)
            native=case["rows"][arm]
            assert out==native["stdout"] and row["route"]==native["route"],(name,arm,row)
            # Require the same chosen plan (ignore nondeterministic time fields).
            def plan(stderr):
                line,=[s for s in stderr.splitlines() if s.startswith("PREJOIN_COMPLETE ")]
                return line.split(" plan_ns=")[0]
            assert plan(err)==plan(native["stderr"]),(name,arm)
            native["simulation_plan"]=plan(err)
            native["simulation_status"]="PASS"
        case["status"]="SIMULATION_COUNT_AND_PLAN_PARITY_PASS"
    report["status"]="PASS"
    save(ROOT/"report.json",report)
    print("PLANNER_SIMULATION_FINAL",json.dumps(report),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("prepare","verify"))
    (prepare if p.parse_args().stage=="prepare" else verify)()

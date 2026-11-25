"""Native Rust Hybrid, paired on existing source cases, with CNF/count admission."""
import argparse
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
from benchmarks.codspeed.case_registry import SOLVER_CPU_CASES
from codspeed_existing import inspect, same_count, RAW, GPMC

ROOT = Path(".rawmocs-native-codspeed").resolve()
BIN = Path("rust/target/release/examples/rawmocs_native_pair").resolve()
ARMS = ("gpmc", "rawmocs")

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def save(report):
    (ROOT/"report.json").write_text(json.dumps(report, indent=2)+"\n")

def write_exec(path, content):
    path.write_text("#!/bin/sh\nset -eu\n"+content+"\n")
    path.chmod(0o755)

def prepare():
    ROOT.mkdir(exist_ok=True)
    report={"status":"PREPARING","working_bits":100,"binary_sha256":{a:digest(b) for a,b in zip(ARMS,(GPMC,RAW))},"verifier_sha256":digest(BIN),"cases":{}}
    config=["options:",'  max-time: "5s"',"benchmarks:"]
    for name in ("vqe4","grover4","qaoa7","qft16"):
        _,filename,_,reverse,_,_=next(c for c in SOLVER_CPU_CASES if c[0]==name+"-gpmc-rust")
        lhs=Path("benchmarks/MQTBench")/filename
        rhs=lhs.parent/"h,ry,rz,cx"/filename
        if reverse: lhs,rhs=rhs,lhs
        case={"source_sha256":[digest(lhs),digest(rhs)],"rows":{},"status":"PENDING"}
        report["cases"][name]=case
        for arm,exe in zip(ARMS,(GPMC,RAW)):
            prefix=ROOT/f"{name}-{arm}"
            cnf=prefix.with_suffix(".cnf")
            stdout=prefix.with_suffix(".solver.stdout")
            stderr=prefix.with_suffix(".solver.stderr")
            wrapper=prefix.with_suffix(".capture.sh")
            # Native qualification only. Simulation launches the actual binary
            # directly, so copying / hashing and shell capture are not timed.
            write_exec(wrapper,'for last do :; done\ncp -- "$last" '+shlex.quote(str(cnf))+
                '\n'+shlex.quote(str(exe))+' "$@" >'+shlex.quote(str(stdout))+' 2>'+shlex.quote(str(stderr))+
                '\ncat '+shlex.quote(str(stdout))+'\ncat '+shlex.quote(str(stderr))+' >&2')
            env={**os.environ,"QUPRS_GPMC_PATH":str(GPMC),"QUPRS_RAWMOCS_PATH":str(RAW)}
            env["QUPRS_"+arm.upper()+"_PATH"]=str(wrapper)
            cmd=[str(BIN),str(lhs),str(rhs),arm]
            start=time.monotonic()
            try:
                proc=subprocess.run(["timeout","-k","1s","2s","prlimit","--as=3221225472","--",*cmd],
                                    env=env,text=True,capture_output=True,timeout=5)
                row={"wall_s":time.monotonic()-start,"stdout":proc.stdout,"stderr":proc.stderr,"exit":proc.returncode}
                if proc.returncode==0 and cnf.exists() and row["wall_s"]<=2:
                    row.update(inspect(arm,stdout.read_text(),stderr.read_text()),cnf_sha256=digest(cnf),status="PASS")
                else: row["status"]="NOT_ADMITTED"
            except Exception as e:
                row={"status":"ERROR","error":str(e)}
            case["rows"][arm]=row
            save(report)
        g,r=(case["rows"][a] for a in ARMS)
        if not (g["status"]==r["status"]=="PASS"):
            case["status"]="NOT_ADMITTED";continue
        if not (g["cnf_sha256"]==r["cnf_sha256"] and g["stdout"]==r["stdout"] and same_count(g,r)):
            case["status"]="MISMATCH";continue
        case["status"]="ADMITTED"
        for arm in ARMS:
            wrapper=ROOT/f"{name}-{arm}.simulation.sh"
            output=ROOT/f"{name}-{arm}.simulation.stdout"
            write_exec(wrapper,"export QUPRS_GPMC_PATH="+shlex.quote(str(GPMC))+
                "\nexport QUPRS_RAWMOCS_PATH="+shlex.quote(str(RAW))+"\nexec "+
                shlex.join([str(BIN),str(lhs),str(rhs),arm])+" >"+shlex.quote(str(output)))
            config.extend([f'  - name: "quprs_native_hybrid/{name}/{arm}_mpfr100"',f'    exec: "{wrapper}"'])
        save(report)
    report["status"]="PREFLIGHT_COMPLETE";save(report)
    assert any(c["status"]=="ADMITTED" for c in report["cases"].values()),"no native pairs admitted"
    assert all(c["status"]!="MISMATCH" for c in report["cases"].values()),"native CNF/verdict/count mismatch"
    Path("codspeed-rawmocs-native.generated.yml").write_text("\n".join(config)+"\n")
    print("NATIVE_PREFLIGHT",json.dumps(report),flush=True)

def verify():
    report=json.loads((ROOT/"report.json").read_text())
    assert report["status"]=="PREFLIGHT_COMPLETE"
    assert report["verifier_sha256"]==digest(BIN)
    assert report["binary_sha256"]=={a:digest(b) for a,b in zip(ARMS,(GPMC,RAW))}
    for name,case in report["cases"].items():
        if case["status"]!="ADMITTED":continue
        for arm in ARMS:
            assert (ROOT/f"{name}-{arm}.simulation.stdout").read_text()==case["rows"][arm]["stdout"]
        case["status"]="SIMULATION_VERDICT_PARITY_PASS"
    report["status"]="PASS";save(report)
    print("NATIVE_CODSPEED_FINAL",json.dumps(report),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("prepare","verify"))
    (prepare if p.parse_args().stage=="prepare" else verify)()

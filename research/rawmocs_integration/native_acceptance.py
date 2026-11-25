"""Admission-bound paired native WallTime and public Python/Rust transport checks."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
from codspeed_native import ROOT, BIN, ARMS, RAW, GPMC, digest, save
from benchmarks.codspeed.case_registry import SOLVER_CPU_CASES


def wall():
    report=json.loads((ROOT/"report.json").read_text())
    assert report["status"]=="PREFLIGHT_COMPLETE"
    assert report["verifier_sha256"]==digest(BIN)
    assert report["binary_sha256"]=={a:digest(b) for a,b in zip(ARMS,(GPMC,RAW))}
    evidence={"status":"RUNNING","scope":"native process start through exit; no CNF capture in measured path",
              "order":["gpmc","rawmocs","rawmocs","gpmc","rawmocs","gpmc","gpmc","rawmocs"],"cases":{}}
    out=ROOT/"walltime.json"
    def persist():
        out.write_text(json.dumps(evidence,indent=2)+"\n")
    env={**os.environ,"QUPRS_GPMC_PATH":str(GPMC),"QUPRS_RAWMOCS_PATH":str(RAW)}
    for name,case in report["cases"].items():
        if case["status"]!="ADMITTED":continue
        _,filename,_,reverse,_,_=next(c for c in SOLVER_CPU_CASES if c[0]==name+"-gpmc-rust")
        lhs=Path("benchmarks/MQTBench")/filename
        rhs=lhs.parent/"h,ry,rz,cx"/filename
        if reverse:lhs,rhs=rhs,lhs
        assert [digest(lhs),digest(rhs)]==case["source_sha256"]
        rows=[]
        group={"rows":rows,"status":"RUNNING"}
        evidence["cases"][name]=group
        for i,arm in enumerate(evidence["order"]):
            rss=ROOT/f"wall-{name}-{i}.rss"
            start=time.perf_counter_ns()
            proc=subprocess.run(["timeout","-k","2s","5s","prlimit","--as=3221225472","--",
                "/usr/bin/time","-f","%M","-o",str(rss),str(BIN),str(lhs),str(rhs),arm],
                env=env,text=True,capture_output=True,timeout=9)
            elapsed=(time.perf_counter_ns()-start)/1e9
            row={"arm":arm,"position":i,"wall_s":elapsed,"exit":proc.returncode,"stdout":proc.stdout,
                 "stderr":proc.stderr,"status":"PASS" if proc.returncode==0 and proc.stdout==case["rows"][arm]["stdout"] else "CENSORED_OR_MISMATCH"}
            if rss.exists():
                try:row["maxrss_kib"]=int(rss.read_text().strip().splitlines()[-1])
                except (ValueError,IndexError):pass
            rows.append(row);persist()
        if all(r["status"]=="PASS" for r in rows):
            group["status"]="PASS"
            group["median_s"]={a:statistics.median(r["wall_s"] for r in rows if r["arm"]==a) for a in ARMS}
            group["min_s"]={a:min(r["wall_s"] for r in rows if r["arm"]==a) for a in ARMS}
            group["speedup"]=group["median_s"]["gpmc"]/group["median_s"]["rawmocs"]
        else:group["status"]="INCONCLUSIVE"
        persist()
    evidence["status"]="PASS" if len(evidence["cases"])==4 and all(c["status"]=="PASS" for c in evidence["cases"].values()) else "INCONCLUSIVE"
    persist()
    print("NATIVE_WALLTIME_FINAL",json.dumps(evidence),flush=True)
    assert evidence["status"]=="PASS"


def api():
    from QuPRS import check_equivalence
    from QuPRS.utils import WMC
    out=ROOT/"public-api.json"
    report={"status":"RUNNING","rows":[]}
    def save_api():
        out.write_text(json.dumps(report,indent=2)+"\n")
    os.environ.update(QUPRS_GPMC_PATH=str(GPMC),QUPRS_RAWMOCS_PATH=str(RAW))
    lhs=Path("benchmarks/MQTBench/vqe_nativegates_ibm_qiskit_opt0_4.qasm").resolve()
    rhs=lhs.parent/"h,ry,rz,cx"/lhs.name
    idq=ROOT/"identity.qasm";xq=ROOT/"x.qasm";hq=ROOT/"h.qasm"
    header='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    for path,body in ((idq,""),(xq,"x q[0];\n"),(hq,"h q[0];\n")):
        path.write_text(header+body)
    def verify(a,b,arm,safe,method):
        return check_equivalence(str(a),str(b),backend="rust",tool_name=arm,
            strategy="Proportional" if method=="hybrid" else "Naive",method=method,
            safe_mode=safe,timeout=20)
    for safe in (False,True):
        for name,a,b,method,expected in (("vqe4",lhs,rhs,"hybrid","equivalent*"),
                                        ("x",idq,xq,"wmc_only","not_equivalent"),
                                        ("h",idq,hq,"wmc_only","not_equivalent")):
            for arm in ARMS:
                r=verify(a,b,arm,safe,method)
                row={"safe_mode":safe,"case":name,"solver":arm,"verdict":r.equivalent,"invoked":r.wmc_solver_invoked}
                report["rows"].append(row);save_api()
                assert r.equivalent==expected and r.wmc_solver_invoked is True,row
                assert os.environ["QUPRS_RAWMOCS_PATH"]==str(RAW)
        for name,body,expect in (("bad_count","printf 's SATISFIABLE\\nc r mpfr NaN 0\\n'","invalid decimal"),
                                 ("resource","exit 5","status="),
                                 ("partial","printf 's SATISFIABLE\\n'","exactly two"),
                                 ("internal_timeout","exit 4","Timeout")):
            stub=ROOT/f"fault-{name}.sh";stub.write_text("#!/bin/sh\n"+body+"\n");stub.chmod(0o755)
            os.environ["QUPRS_RAWMOCS_PATH"]=str(stub)
            try:
                if name=="internal_timeout":
                    r=verify(lhs,rhs,"rawmocs",safe,"hybrid")
                    assert r.equivalent=="Timeout" and r.wmc_solver_invoked is True
                    observed=r.equivalent
                else:
                    try:verify(lhs,rhs,"rawmocs",safe,"hybrid")
                    except ValueError as e:
                        observed=str(e)
                        assert expect.lower() in observed.lower(),observed
                    else:raise AssertionError("fault returned a numerical verdict")
                assert os.environ["QUPRS_RAWMOCS_PATH"]==str(stub)
                report["rows"].append({"safe_mode":safe,"fault":name,"observed":observed,"status":"PASS"});save_api()
            finally:os.environ["QUPRS_RAWMOCS_PATH"]=str(RAW)
        os.environ.pop("QUPRS_RAWMOCS_PATH")
        try:
            try:verify(lhs,rhs,"rawmocs",safe,"hybrid")
            except ValueError as e:assert "QUPRS_RAWMOCS_PATH" in str(e)
            else:raise AssertionError("missing path unexpectedly accepted")
            report["rows"].append({"safe_mode":safe,"fault":"missing_path","status":"PASS"});save_api()
        finally:os.environ["QUPRS_RAWMOCS_PATH"]=str(RAW)
    report["status"]="PASS";save_api()
    print("NATIVE_PUBLIC_API_FINAL",json.dumps(report),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("wall","api"))
    (wall if p.parse_args().stage=="wall" else api)()

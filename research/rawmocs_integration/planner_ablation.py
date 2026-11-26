"""Paired bounded research-only solver ablation on pinned native QuPRS CNFs."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from fractions import Fraction
from expanded_cohort import run, inspect, parity, save, digest, bounded
from release_transfer import check_count

HASHES={16:"c35ee4e3ce77faf21ae6c8cd39d2fe14d8cba9958abffb8f18857e4357c9ea22",
        22:"b5b91071244384159f33dc81f9ac43c573be7dc2e19baf813d1d152556e5b56b",
        20:"29fea8d65f63dd282cc740e8cac5439b071f618780b04541e4412bfbd39462c5",
        8:"24dbcd5b6f270fd39f92b739e55446da7c14e7e2c28ed5032b70cf34bc0f786c"}
AS="3221225472"

def trial(a,cnf,label,arm):
    exe=a.raw if arm=="baseline" else a.candidate
    env=os.environ.copy()
    env.pop("RAWMOCS_RESEARCH_PEAK_FIRST",None)
    env.pop("RAWMOCS_RESEARCH_THREE_CUT",None)
    if arm=="peak":env["RAWMOCS_RESEARCH_PEAK_FIRST"]="1"
    if arm=="gated":env["RAWMOCS_RESEARCH_PEAK_FIRST"]="2"
    if arm=="three":env["RAWMOCS_RESEARCH_THREE_CUT"]="1"
    prefix=a.out/label
    rss=prefix.with_suffix(".rss")
    start=time.monotonic()
    proc=subprocess.run(["timeout","-k","2s","95s","prlimit","--as="+AS,"--",
        "/usr/bin/time","-f","%M","-o",str(rss),str(exe),"--digits","30",
        "--solver","prejoin","--timeout-ms","90000",str(cnf)],env=env,
        capture_output=True,text=True,timeout=100)
    row={"arm":arm,"exit":proc.returncode,"wall_s":time.monotonic()-start,
        "binary_sha256":digest(exe),"cnf_sha256":digest(cnf),
        "stderr":proc.stderr[-5000:],"empty_numeric_stdout":not proc.stdout.strip()}
    prefix.with_suffix(".stdout").write_text(proc.stdout)
    prefix.with_suffix(".stderr").write_text(proc.stderr)
    if rss.exists():
        try:row["rss_kib"]=int(rss.read_text().splitlines()[-1])
        except (ValueError,IndexError):pass
    if proc.returncode==0:
        row.update(inspect("rawmocs",proc.stdout,proc.stderr))
        row["status"]="COMPLETED"
    else:
        row["status"]="ROUTE_REJECTED" if proc.returncode==6 else "CENSORED_TIMEOUT" if proc.returncode in (4,124) else "ERROR"
        assert row["empty_numeric_stdout"],row
    save(prefix.with_suffix(".json"),row)
    return row

def witness(a,cnf,rows):
    result={"status":"UNAVAILABLE","attempts":[]}
    for name in ("original_exact_prejoin.py","original_fixed_interval.py"):
        proc=bounded([sys.executable,a.oracle/name,cnf,digest(cnf)],120)
        (a.out/(name+".stdout")).write_text(proc.stdout)
        (a.out/(name+".stderr")).write_text(proc.stderr)
        result["attempts"].append({"script":name,"exit":proc.returncode,"stderr":proc.stderr[-500:]})
        if proc.returncode:continue
        ref=json.loads(proc.stdout)
        assert ref["source_sha256"]==digest(cnf) and ref["bits"]==550
        assert ref["width"]<=19 and ref["work"]<=40000000 and ref["peak"]<=2000000
        if name=="original_exact_prejoin.py":assert ref["status"]=="INDEPENDENT_INTERVAL_COMPLETE"
        else:assert ref["order_policy"] in ("fill-reverse","degree-reverse")
        save(a.out/"witness.json",ref)
        result["relative_upper"]=[check_count(r,ref,30) for r in rows]
        result["status"]="PASS"
        break
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--n",type=int,choices=(8,16,20,22),required=True)
    for name in ("raw","candidate","gpmc","bin","oracle","out"):
        p.add_argument("--"+name,required=True,type=lambda x:Path(x).resolve())
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    family="qnn" if a.n==8 else "qft"
    filename=f"{family}_nativegates_ibm_qiskit_opt0_{a.n}.qasm"
    root=Path("benchmarks/MQTBench")
    lhs,rhs=root/"h,ry,rz,cx"/filename,root/filename
    if a.n==8:lhs,rhs=rhs,lhs
    report={"status":"RUNNING","n":a.n,"source_sha256":[digest(lhs),digest(rhs)],
        "cnf_sha256_expected":HASHES[a.n],"digits":30,"bits":100,"limit_s":90,"rows":[]}
    def persist():save(a.out/"ablation.json",report)
    try:
        g=run(a,"gpmc",lhs,rhs,"gpmc-capture",True)
        report["gpmc"]=g;persist()
        # The exact source CNF is captured before solving, even when GPMC
        # is censored. QFT22 rejection classification needs only those bytes.
        assert g["status"]=="COMPLETED" or (a.n==22 and g["status"] in ("CENSORED_TIMEOUT","CENSORED_WATCHDOG")),g
        cnf=a.out/"gpmc-capture.cnf"
        assert digest(cnf)==HASHES[a.n]
        if g["status"]=="COMPLETED":assert g["cnf_sha256"]==HASHES[a.n]
        order=("baseline","candidate","peak","gated","gated","peak","candidate","baseline") if a.n!=22 else ("baseline","candidate","three")
        for i,arm in enumerate(order):
            row=trial(a,cnf,f"trial-{i}-{arm}",arm)
            if row["status"]=="COMPLETED" and g["status"]=="COMPLETED":
                row["gpmc_parity"]=parity(g,row)
                assert row["gpmc_parity"],row
            report["rows"].append(row);persist()
        if a.n!=22:
            assert all(r["status"]=="COMPLETED" for r in report["rows"])
            b=report["rows"][0]
            assert all(all(Fraction(r[k])==Fraction(b[k]) for k in ("real","imag")) and r["sat"]==b["sat"] for r in report["rows"] if r["arm"]=="candidate")
            report["median"]={arm:{k:statistics.median(r[k] for r in report["rows"] if r["arm"]==arm)
                        for k in ("wall_s","rss_kib")} for arm in ("baseline","candidate","peak","gated")}
            report["witness"]=witness(a,cnf,[g,*report["rows"]])
            report["status"]="GATED_PEAK_ABLATION_COMPLETE" if report["witness"]["status"]=="PASS" else "GATED_PEAK_UNWITNESSED"
        else:
            b,c,t=report["rows"]
            assert b["status"]=="ROUTE_REJECTED" and c["status"]=="ROUTE_REJECTED", (b,c)
            assert t["status"] in ("COMPLETED","ROUTE_REJECTED","CENSORED_TIMEOUT"),t
            assert "leaf_rejections=Rejections" in c["stderr"] and "cuts=3" in t["stderr"],(c,t)
            if t["status"]=="COMPLETED":
                report["witness"]=witness(a,cnf,[r for r in (g,t) if r["status"]=="COMPLETED"])
                report["status"]="THREE_CUT_CANDIDATE_COMPLETED"
            else:report["status"]="REJECTION_DIAGNOSTIC_COMPLETE"
    except Exception as exc:
        report.update(status="ERROR",error=f"{type(exc).__name__}: {str(exc)[:2000]}")
        raise
    finally:
        persist()
        print("PLANNER_ABLATION_FINAL",json.dumps(report),flush=True)

if __name__=="__main__":main()

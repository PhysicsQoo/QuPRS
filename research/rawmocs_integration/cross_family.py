"""Frozen-candidate cross-family admission using actual QuPRS Native Hybrid.

Source expectations, RR-only outcomes, timeouts, numerical disagreements and
performance comparisons are separate evidence classes. No tuning per family.
"""
import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace
import statistics
from fractions import Fraction
from expanded_cohort import run, fallback, parity, digest, save
from planner_ablation import witness

CASES=json.loads("{\"qaoa9\":[\"qaoa\",9,false],\"vqe8\":[\"vqe\",8,false],\"wstate16\":[\"wstate\",16,false],\"qpeexact16\":[\"qpeexact\",16,false],\"qpeinexact20\":[\"qpeinexact\",20,false],\"grover5\":[\"grover-noancilla\",5,true],\"qwalk4\":[\"qwalk-noancilla\",4,false],\"graphstate16\":[\"graphstate\",16,false],\"ghz32\":[\"ghz\",32,false],\"qnn12\":[\"qnn\",12,false]}")
ARMS=("baseline","gated","refine")
FLAGS=("RAWMOCS_RESEARCH_PEAK_FIRST","RAWMOCS_RESEARCH_THREE_CUT",
       "RAWMOCS_RESEARCH_RECYCLE_MOVE","RAWMOCS_RESEARCH_SUPPORT_FIRST")

def select(a,arm,out):
    for key in FLAGS:os.environ.pop(key,None)
    if arm in ("gated","refine"):os.environ[FLAGS[0]]="2" if arm=="gated" else "3"
    return SimpleNamespace(raw=a.raw if arm=="baseline" else a.candidate,
                           gpmc=a.gpmc,bin=a.bin,oracle=a.oracle,out=out)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--case",choices=[*CASES,"fallback"],required=True)
    for key in ("raw","candidate","gpmc","bin","oracle","out"):
        p.add_argument("--"+key,type=lambda x:Path(x).resolve(),required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    report={"case":a.case,"status":"RUNNING","bits":100,"digits":30,"limit_s":90,
            "binary_sha256":{k:digest(getattr(a,k)) for k in ("raw","candidate","gpmc","bin")}}
    def persist():save(a.out/"report.json",report)
    try:
        if a.case=="fallback":
            report["arms"]={}
            os.environ["QUPRS_GPMC_PATH"]=str(a.gpmc)
            for arm in ARMS:
                out=a.out/arm;out.mkdir(exist_ok=True)
                r={};report["arms"][arm]=r
                fallback(select(a,arm,out),r)
                assert r["status"]=="FALLBACK_ORACLE_PASS"
                persist()
            report["status"]="FALLBACK_ALL_PASS"
            return
        family,n,reverse=CASES[a.case]
        root=Path("benchmarks/MQTBench")
        filename=f"{family}_nativegates_ibm_qiskit_opt0_{n}.qasm"
        lhs,rhs=root/filename,root/"h,ry,rz,cx"/filename
        if reverse:lhs,rhs=rhs,lhs
        report.update(family=family,n=n,source_sha256=[digest(lhs),digest(rhs)],expected="EQ")
        g=run(select(a,"baseline",a.out),"gpmc",lhs,rhs,"gpmc-capture",True)
        report["gpmc"]=g;report["rows"]=[];persist()
        # Each arm gets one sample before repeats. Keep censoring, never turn it
        # into a numeric count or infinite speedup. Skip a second censored arm.
        for i,arm in enumerate(("baseline","gated","refine","refine","gated","baseline")):
            if any(r["arm"]==arm and r["status"]!="COMPLETED" for r in report["rows"]):continue
            r=run(select(a,arm,a.out),"rawmocs",lhs,rhs,f"trial-{i}-{arm}",True)
            r["arm"]=arm;report["rows"].append(r);persist()
        rows=report["rows"]
        allrows=[g,*rows]
        completed=[r for r in allrows if r["status"]=="COMPLETED"]
        if all(r["status"]=="RR_OR_ANALYTIC_ONLY" for r in allrows):
            assert len({r["verdict"] for r in allrows})==1,allrows
            report["status"]="RR_ONLY" if g["verdict"] in ("equivalent","equivalent*") else "RR_SOURCE_EXPECTATION_MISMATCH"
            return
        captured={r["captured_cnf_sha256"] for r in allrows if "captured_cnf_sha256" in r}
        assert len(captured)<=1,allrows
        assert all(r["status"] not in ("ERROR","EXECUTION_ERROR") for r in allrows),allrows
        if completed:
            base=completed[0]
            assert all(r["cnf_sha256"]==base["cnf_sha256"] and
                       r["normalization_twice_log2"]==base["normalization_twice_log2"] and
                       r["verdict"]==base["verdict"] and parity(base,r) for r in completed),allrows
        if not all(r["status"]=="COMPLETED" for r in allrows):
            report["status"]="CENSORED_OR_MIXED"
            baseline_ok=any(r["arm"]=="baseline" and r["status"]=="COMPLETED" for r in rows)
            if baseline_ok and any(r["arm"]!="baseline" and r["status"]!="COMPLETED" for r in rows):
                report["status"]="CANDIDATE_COVERAGE_REGRESSION"
                raise AssertionError("candidate failed on baseline-completed case")
            return
        cnf=a.out/"gpmc-capture.cnf"
        assert digest(cnf)==g["cnf_sha256"]
        report["witness"]=witness(a,cnf,allrows)
        report["median"]={arm:{k:statistics.median(r[k] for r in rows if r["arm"]==arm)
                            for k in ("wall_s","tool_s","maxrss_kib")} for arm in ARMS}
        report["baseline_relative"]={arm:{k:report["median"][arm][k]/max(1e-12,report["median"]["baseline"][k])
                                          for k in ("wall_s","tool_s","maxrss_kib")} for arm in ("gated","refine")}
        # The expectation is independent of cross-solver agreement.
        report["status"]=("SOURCE_EXPECTATION_MISMATCH" if g["verdict"] not in ("equivalent","equivalent*")
            else "CROSS_FAMILY_WITNESS_PASS" if report["witness"]["status"]=="PASS"
            else "CROSS_FAMILY_PARITY_UNWITNESSED")
    except Exception as e:
        report["error"]=f"{type(e).__name__}: {str(e)[:2000]}"
        if report["status"]=="RUNNING":report["status"]="ERROR"
        raise
    finally:
        persist();print("CROSS_FAMILY_FINAL",json.dumps(report),flush=True)
        for key in FLAGS:os.environ.pop(key,None)

if __name__=="__main__":main()

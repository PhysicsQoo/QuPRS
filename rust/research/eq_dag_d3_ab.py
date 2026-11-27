#!/usr/bin/env python3
"""D3 matched solver-only A/B. No production modifications or re-encoding.
Two reversed periods, all twelve sealed D2a pairs, original GPMC SHA/args,
60 s hard solver cap and 4096 MiB per-process virtual address space cap.
"""
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import statistics
import subprocess
import sys
import time
from eq_dag_phase_screen import read_snapshot
from eq_dag_d2a_rewrite import replay

BASE="8811544a462338569bc5a375e3df41fdd18ea3b8"
DAG="9c62004793c91f99213f782f3518f84267efb385"
CAP=60
# Diagnostic printed-center agreement, not a certified numerical bound.
DELTA=Fraction(1,10**20)

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def git(*args):
    return subprocess.check_output(["git",*args],text=True).strip()

def run(solver,reader,cnf,arm,k):
    arm.mkdir()
    rss=arm/"rss.txt"
    cmd=["prlimit","--as=4294967296","--","/usr/bin/time","-f","%M","-o",str(rss),"timeout","--kill-after=2s",str(CAP),str(solver),"-mode=1",str(cnf)]
    start=time.monotonic()
    with (arm/"stdout.txt").open("wb") as out,(arm/"stderr.txt").open("wb") as err:
        p=subprocess.run(cmd,stdout=out,stderr=err)
    elapsed=time.monotonic()-start
    raw=(arm/"stdout.txt").read_text(errors="replace")
    digits=[x.split()[-1] for x in raw.splitlines() if x.startswith("c o precision ")]
    result=dict(status="TIMEOUT" if p.returncode in (124,137) else "SOLVER_ERROR" if p.returncode else "COMPLETE",returncode=p.returncode,wall_s=elapsed,rss_individual_kib=rss.read_text().strip() if rss.exists() else None,reported_precision=digits,cnf_sha256=sha(cnf))
    if p.returncode:
        return result
    if digits and set(digits)!={"30"}:
        result["status"]="PRECISION_MISMATCH"
        return result
    parsed=subprocess.run([str(reader),str(arm/"stdout.txt"),str(k)],capture_output=True,text=True)
    (arm/"count_parser_stderr.txt").write_text(parsed.stderr)
    if parsed.returncode:
        result["status"]="COUNT_PARSE_ERROR"
        return result
    re,im,verdict,fmt=parsed.stdout.strip().split("\t")
    Fraction(re);Fraction(im)
    result.update(real=re,imag=im,verdict=verdict,format=fmt)
    return result

def compare(a,b,k):
    if a["status"]!="COMPLETE" or b["status"]!="COMPLETE":
        return dict(status="INCOMPLETE")
    d=(Fraction(a["real"])-Fraction(b["real"]))**2+(Fraction(a["imag"])-Fraction(b["imag"]))**2
    norm_sq=Fraction(2)**k
    return dict(status="PASS" if d<=norm_sq*DELTA**2 and a["verdict"]==b["verdict"] else "DISAGREEMENT",normalized_delta_squared=str(d/norm_sq),same_verdict=a["verdict"]==b["verdict"])

def controls():
    a=dict(status="COMPLETE",real="16",imag="0",verdict="equivalent")
    assert compare(a,a,8)["status"]=="PASS"
    assert compare(a,dict(a,imag="1"),8)["status"]=="DISAGREEMENT"
    assert compare(a,dict(a,verdict="equivalent*"),8)["status"]=="DISAGREEMENT"
    assert compare(a,dict(status="TIMEOUT"),8)["status"]=="INCOMPLETE"

def main():
    controls()
    src,dag,solver,reader,out=map(lambda p:Path(p).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    assert (src/"head.txt").read_text().strip()==BASE
    assert (dag/"head.txt").read_text().strip()==DAG
    assert (dag/"tree.txt").read_text().strip()=="4ab682e34d8b748fbdbae3e20380fa28cb4d3f0d"
    prov=json.loads((src/"provenance.json").read_text())
    assert prov["head"]==BASE and prov["gpmc_sha256"]==sha(solver)
    rows={r["case"]:r for r in map(json.loads,(src/"rows.jsonl").read_text().splitlines())}
    receipts=json.loads((dag/"rewrite_receipts.json").read_text())["rows"]
    assert len(receipts)==12 and len({r["case"] for r in receipts})==12
    provenance=dict(head=git("rev-parse","HEAD"),flat_head=BASE,dag_head=DAG,gpmc_sha256=sha(solver),reader_sha256=sha(reader),args=["-mode=1"],requested_default_precision=30,timeout_s=CAP,address_space_mib=4096,normalized_count_delta=str(DELTA),scope="solver-only discovery; no certified arithmetic or end-to-end speed claim")
    (out/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
    # Costly and large-reduction families first; full original cohort retained.
    priority=["wstate_16","grover-noancilla_negative_5","qwalk-noancilla_negative_5","qnn_12","vqe_16"]
    receipts.sort(key=lambda r:(priority.index(r["case"]) if r["case"] in priority else len(priority),r["case"]))
    reports=[]
    for r in receipts:
        case=r["case"]
        baseline=rows[case]
        arm=src/(case+"-hybrid")
        flat=arm/"actual.cnf"
        candidate=dag/(case+".cnf")
        assert sha(flat)==r["flat_sha256"]==baseline["cnf"]["sha256"]
        assert sha(candidate)==r["dag_sha256"]
        assert sha(arm/"residual.tsv")==r["residual_sha256"]==baseline["residual_sha256"]
        n,h,phase,outputs=read_snapshot(arm/"residual.tsv")
        k=2*n+h
        verified=replay(flat.read_text(),candidate.read_text())
        assert all(r[x]==verified[x] for x in verified)
        samples={}
        pairs=[]
        for period,order in enumerate((("flat","dag"),("dag","flat")),1):
            current={}
            for mode in order:
                res=run(solver,reader,flat if mode=="flat" else candidate,out/f"{case}-{period}-{mode}",k)
                current[mode]=res
                print("D3_ARM",json.dumps(dict(case=case,period=period,mode=mode,**res)),flush=True)
            comparison=compare(current["flat"],current["dag"],k)
            pairs.append(dict(period=period,comparison=comparison,**current))
            samples.update({(period,m):r for m,r in current.items()})
        complete=[p for p in pairs if p["comparison"]["status"]=="PASS"]
        # Repeatability checked within each encoding as well as cross encoding.
        within={m:compare(samples[(1,m)],samples[(2,m)],k) for m in ("flat","dag")}
        all_runs=list(samples.values())
        expected_wrong=[x["verdict"] for x in all_runs if x["status"]=="COMPLETE" and ((baseline["expected"]=="EQ" and x["verdict"]=="not_equivalent") or (baseline["expected"]=="NEQ" and x["verdict"] in ("equivalent","equivalent*")))]
        record=dict(case=case,expected=baseline["expected"],normalization_twice_log2=k,flat_clauses=r["flat_clauses"],dag_clauses=r["dag_clauses"],pairs=pairs,within=within,expected_disagreements=expected_wrong,flat_complete=sum(samples[(i,"flat")]["status"]=="COMPLETE" for i in (1,2)),dag_complete=sum(samples[(i,"dag")]["status"]=="COMPLETE" for i in (1,2)))
        if len(complete)==2 and all(x["status"]=="PASS" for x in within.values()) and not expected_wrong:
            record["paired_median_solver_speedup"]=statistics.median(p["flat"]["wall_s"] for p in complete)/statistics.median(p["dag"]["wall_s"] for p in complete)
        reports.append(record)
        with (out/"cases.jsonl").open("a") as f:
            f.write(json.dumps(record)+"\n")
        print("D3_CASE",json.dumps({k:v for k,v in record.items() if k!="pairs"}),flush=True)
    summary=dict(cases=len(reports),arms=sum(4 for r in reports),flat_complete=sum(r["flat_complete"] for r in reports),dag_complete=sum(r["dag_complete"] for r in reports),paired_pass=sum(p["comparison"]["status"]=="PASS" for r in reports for p in r["pairs"]),paired_incomplete=sum(p["comparison"]["status"]=="INCOMPLETE" for r in reports for p in r["pairs"]),paired_disagreements=sum(p["comparison"]["status"]=="DISAGREEMENT" for r in reports for p in r["pairs"]),within_disagreements=sum(x["status"]=="DISAGREEMENT" for r in reports for x in r["within"].values()),expected_disagreements=sum(len(r["expected_disagreements"]) for r in reports),speedups={r["case"]:r["paired_median_solver_speedup"] for r in reports if "paired_median_solver_speedup" in r},completion_gains=[r["case"] for r in reports if r["dag_complete"]>r["flat_complete"]],completion_losses=[r["case"] for r in reports if r["dag_complete"]<r["flat_complete"]])
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("D3_SUMMARY",json.dumps(summary),flush=True)
    assert summary["arms"]==48 and summary["paired_disagreements"]==summary["within_disagreements"]==summary["expected_disagreements"]==0
    assert summary["paired_pass"]>0

if __name__=="__main__":
    main()

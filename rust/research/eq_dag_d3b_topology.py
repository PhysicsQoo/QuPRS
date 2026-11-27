#!/usr/bin/env python3
"""D3b: one predeclared balanced-partition challenger vs flat and deep DAG.
No extra weighted literals, phase arithmetic, solver or production changes.
Same sealed residuals and binary; cyclic order across three periods.
"""
import itertools
import json
import statistics
import sys
from pathlib import Path
from eq_dag_d2a_rewrite import parse,blocks,render,replay,models,tests
from eq_dag_phase_screen import read_snapshot
from eq_dag_d3_ab import BASE,DAG,CAP,DELTA,sha,git,run,compare,controls

CASES=("wstate_16","grover-noancilla_negative_5","qwalk-noancilla_negative_5","vqe_16")
MODES=("flat","deep","balanced")

def balanced(flat):
    n,w,ids,c=parse(flat)
    old,tail=blocks(ids,c)
    support={tuple(sorted(ops)):z for z,ops in old.items()}
    assert len(support)==len(ids)
    weighted=set(ids)
    assert all(not (set(ops)&weighted) for ops in old.values())
    new={}
    reused=0
    for z,ops in old.items():
        if len(ops)<3:
            new[z]=ops
            continue
        # Single deterministic split in sorted DIMACS-primary order.
        # Each child is a proper disjoint subset. Use its existing weighted
        # root if present, otherwise leave that half as primary operands.
        s=tuple(sorted(ops))
        mid=len(s)//2
        out=[]
        for part in (s[:mid],s[mid:]):
            if len(part)>=2 and part in support:
                out.append(support[part])
                reused+=1
            else:
                out.extend(part)
        new[z]=tuple(out)
    candidate=render(n,w,new,tail)
    receipt=replay(flat,candidate)
    max_degree=max(map(len,old.values()),default=0)
    # Flat depth is one. Each reused root has at most ceil(d/2) inputs.
    depth_bound=max(1,(max_degree-1).bit_length()) if max_degree else 1
    assert receipt["max_chain_depth"]<=depth_bound
    assert receipt["dag_clauses"]<=receipt["flat_clauses"]
    return candidate,dict(receipt,reused_children=reused,depth_bound=depth_bound,max_degree=max_degree)

def local_controls():
    tests()
    controls()
    # Both halves reused, all original weighted variables and weights retained.
    w=["c t wmc"]
    for z in (5,6,7):
        w.extend((f"c p weight {z} 0.5 -0.5 0",f"c p weight -{z} 1.0 0.0 0"))
    flat=render(7,w,{5:(1,2),6:(3,4),7:(1,2,3,4)},[(1,-4)])
    cand,r=balanced(flat)
    assert r["dag_clauses"]==r["flat_clauses"]-2 and r["max_chain_depth"]==2
    assert r["reused_children"]==2 and models(flat)==models(cand)
    flat=render(7,w,{5:(1,3),6:(2,4),7:(1,2,3,4)},[])
    cand,r=balanced(flat)
    assert r["reused_children"]==0 and r["dag_clauses"]==r["flat_clauses"]
    assert models(flat)==models(cand)

def rss(x):
    # SIGKILL wrapper RSS is not a valid solver observation.
    if x["returncode"] not in (0,124):
        return None
    s=x.get("rss_individual_kib")
    if not s:
        return None
    token=s.strip().splitlines()[-1]
    return int(token) if token.isdigit() else None

def main():
    local_controls()
    src,dag,solver,reader,out=map(lambda p:Path(p).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    assert (src/"head.txt").read_text().strip()==BASE
    assert (src/"tree.txt").read_text().strip()=="b7ebfdcf3cfdac115bf971fddc92306bc66adde8"
    assert (dag/"head.txt").read_text().strip()==DAG
    assert (dag/"tree.txt").read_text().strip()=="4ab682e34d8b748fbdbae3e20380fa28cb4d3f0d"
    prov=json.loads((src/"provenance.json").read_text())
    assert prov["head"]==BASE and prov["gpmc_sha256"]==sha(solver)
    rows={r["case"]:r for r in map(json.loads,(src/"rows.jsonl").read_text().splitlines())}
    receipts={r["case"]:r for r in json.loads((dag/"rewrite_receipts.json").read_text())["rows"]}
    (out/"provenance.json").write_text(json.dumps(dict(head=git("rev-parse","HEAD"),flat_head=BASE,deep_head=DAG,gpmc_sha256=sha(solver),reader_sha256=sha(reader),cases=CASES,modes=MODES,periods=3,solver_cap=CAP,precision=30,address_space_mib=4096,count_delta=str(DELTA),policy="single sorted DIMACS midpoint, each half reused only if existing weighted root; no tuning"),indent=2)+"\n")
    reports=[]
    for case in CASES:
        b=rows[case];r=receipts[case]
        arm=src/(case+"-hybrid")
        flat=arm/"actual.cnf";deep=dag/(case+".cnf")
        assert sha(flat)==r["flat_sha256"]==b["cnf"]["sha256"]
        assert sha(deep)==r["dag_sha256"]
        assert sha(arm/"residual.tsv")==r["residual_sha256"]==b["residual_sha256"]
        n,h,_,_=read_snapshot(arm/"residual.tsv")
        k=2*n+h
        f=flat.read_text()
        check=replay(f,deep.read_text())
        assert all(r[x]==check[x] for x in check)
        text,structure=balanced(f)
        target=out/(case+"-balanced.cnf")
        target.write_text(text)
        structure.update(case=case,flat_sha256=sha(flat),deep_sha256=sha(deep),balanced_sha256=sha(target),deep_clauses=check["dag_clauses"],deep_depth=check["max_chain_depth"])
        print("D3B_STRUCTURE",json.dumps(structure),flush=True)
        files=dict(flat=flat,deep=deep,balanced=target)
        samples={m:[] for m in MODES}
        comparisons=[]
        errors=[]
        for p in range(3):
            order=MODES[p:]+MODES[:p]
            current={}
            for m in order:
                x=run(solver,reader,files[m],out/f"{case}-{p+1}-{m}",k)
                if x["returncode"]==137:
                    x["status"]="KILLED_137"
                if x["status"]=="COMPLETE" and x["reported_precision"]!=["30"]:
                    x["status"]="PRECISION_UNVERIFIED"
                x["rss_valid_kib"]=rss(x)
                current[m]=x
                samples[m].append(x)
                if x["status"]=="COMPLETE" and ((b["expected"]=="EQ" and x["verdict"]=="not_equivalent") or (b["expected"]=="NEQ" and x["verdict"] in ("equivalent","equivalent*"))):
                    errors.append(dict(period=p+1,mode=m,verdict=x["verdict"]))
                print("D3B_ARM",json.dumps(dict(case=case,period=p+1,mode=m,**x)),flush=True)
            for a,z in itertools.combinations(MODES,2):
                comparisons.append(dict(period=p+1,a=a,b=z,**compare(current[a],current[z],k)))
        within=[]
        for m in MODES:
            for i,j in itertools.combinations(range(3),2):
                within.append(dict(mode=m,i=i+1,j=j+1,**compare(samples[m][i],samples[m][j],k)))
        summary={}
        for m,seq in samples.items():
            done=[x for x in seq if x["status"]=="COMPLETE"]
            timed=[x["rss_valid_kib"] for x in seq if x["status"]=="TIMEOUT" and x["rss_valid_kib"] is not None]
            finished=[x["rss_valid_kib"] for x in done if x["rss_valid_kib"] is not None]
            summary[m]=dict(complete=len(done),statuses=[x["status"] for x in seq],median_complete_wall_s=statistics.median(x["wall_s"] for x in done) if done else None,median_complete_rss_kib=statistics.median(finished) if finished else None,median_timeout_rss_kib=statistics.median(timed) if timed else None)
        bad=sum(x["status"]=="DISAGREEMENT" for x in comparisons+within)+len(errors)
        ratios={}
        for m in ("deep","balanced"):
            if not bad and all(summary[x]["complete"]==3 for x in ("flat",m)):
                ratios[m]=summary["flat"]["median_complete_wall_s"]/summary[m]["median_complete_wall_s"]
        record=dict(case=case,structure=structure,summary=summary,solver_speedups=ratios,disagreements=bad,comparisons=comparisons,within=within,expected_errors=errors,samples=samples)
        reports.append(record)
        with (out/"cases.jsonl").open("a") as f:
            f.write(json.dumps(record)+"\n")
        print("D3B_CASE",json.dumps({k:v for k,v in record.items() if k not in ("samples","comparisons","within")}),flush=True)
    summary=dict(cases=len(reports),arms=len(reports)*9,disagreements=sum(r["disagreements"] for r in reports),complete={m:sum(r["summary"][m]["complete"] for r in reports) for m in MODES},scope="three-period exploratory topology comparison, not final performance gate")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("D3B_SUMMARY",json.dumps(summary),flush=True)
    assert summary["arms"]==36 and summary["disagreements"]==0
    assert sum(summary["complete"].values())>0

if __name__=="__main__":
    main()

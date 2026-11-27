#!/usr/bin/env python3
"""Offline D1c structural cost screen. No solver calls or phase rewrites."""
import ast
from collections import defaultdict
from itertools import combinations
import hashlib
import json
from pathlib import Path
import sys

BASE="e744768dc3ed8b2b86a65295da1000ed4d0431c9"
TREE="4189183f6ff4bc04fed22ad9a5a246e9c2512b53"

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read_snapshot(p):
    meta,phase,outputs={},{},{}
    for line in p.read_text().splitlines():
        a=line.split("\t")
        if a[0]=="p":
            m=tuple(ast.literal_eval(a[1]))
            assert m==tuple(sorted(set(m))) and m not in phase
            phase[m]=tuple(a[2:])
        elif a[0]=="output":
            i=int(a[1])
            assert i not in outputs
            outputs[i]=[]
        elif a[0]=="f":
            m=tuple(ast.literal_eval(a[2]))
            assert m==tuple(sorted(set(m)))
            outputs[int(a[1])].append(m)
        else:
            assert len(a)==2 and a[0] not in meta
            meta[a[0]]=a[1]
    n,h=int(meta["n"]),int(meta["h"])
    assert set(outputs)==set(range(n))
    domain=set(ast.literal_eval(meta["vars"]))
    assert len(domain)==n+h
    for m in list(phase)+[m for f in outputs.values() for m in f]:
        assert set(m)<=domain
    return n,h,phase,outputs

def flat_counts(n,h,phase,outputs):
    # Exact structural model of the original flat encoder.
    v=n+h+len(phase)
    c=sum(len(m)+1 for m in phase)
    for f in outputs.values():
        assert len(set(f))==len(f)
        if not f:
            v+=1
            c+=1
        else:
            for m in f:
                if len(m)!=1:
                    v+=1
                    c+=len(m)+1
            v+=len(f)-1
            c+=4*(len(f)-1)
        c+=2
    return v,c

def plan(phase,reuse):
    # At most one pair per high-degree monomial. Neutral pair: 3 clauses;
    # replacing two operands saves one clause per d>=3 AND. An existing
    # quadratic weighted root may be referenced without adding weight.
    high=sorted(m for m in phase if len(m)>=3)
    roots={m for m in phase if len(m)==2} if reuse else set()
    work=sum(len(m)*(len(m)-1)//2 for m in high)
    if work>200000:
        return dict(status="WORK_CAP",pair_work=work)
    pairs=defaultdict(set)
    for i,m in enumerate(high):
        for p in combinations(m,2):
            pairs[p].add(i)
    available=set(range(len(high)))
    chosen=[]
    for p,ids in sorted(pairs.items(),key=lambda kv:(-len(kv[1])+(0 if kv[0] in roots else 3),kv[0])):
        eligible=sorted(ids&available)
        cost=0 if p in roots else 3
        gain=len(eligible)-cost
        if gain<=0:
            continue
        available.difference_update(eligible)
        chosen.append(dict(pair=list(p),root_kind="existing_weighted" if not cost else "new_neutral",occurrences=len(eligible),clause_saving=gain))
    return dict(status="OK",high_degree=len(high),candidate_pairs=len(pairs),pair_work=work,covered=len(high)-len(available),new_neutral=sum(x["root_kind"]=="new_neutral" for x in chosen),reused_weighted_roots=sum(x["root_kind"]=="existing_weighted" for x in chosen),clause_saving=sum(x["clause_saving"] for x in chosen),chosen=chosen)

def tests():
    x={(0,1,k):None for k in range(2,6)}
    assert plan(x,False)["clause_saving"]==1
    assert plan(x,False)["new_neutral"]==1
    y={(0,1):None,(0,1,2):None}
    assert plan(y,False)["clause_saving"]==0
    assert plan(y,True)["clause_saving"]==1
    assert plan({(i,j):None for i,j in combinations(range(8),2)},True)["clause_saving"]==0
    assert plan({(0,1,k):None for k in range(2,5)},False)["clause_saving"]==0

def main():
    tests()
    src,out=map(Path,sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    assert (src/"head.txt").read_text().strip()==BASE
    assert (src/"tree.txt").read_text().strip()==TREE
    provenance=json.loads((src/"provenance.json").read_text())
    assert provenance["head"]==BASE and provenance["tree"]==TREE
    rows=[json.loads(x) for x in (src/"rows.jsonl").read_text().splitlines()]
    assert len(rows)==34 and len({(r["case"],r["mode"]) for r in rows})==34
    results=[]
    for r in rows:
        arm=src/(r["case"]+"-"+r["mode"])
        snap=arm/"residual.tsv"
        assert sha(snap)==r["residual_sha256"]
        if r["cnf"] is None:
            continue
        assert sha(arm/"actual.cnf")==r["cnf"]["sha256"]
        n,h,phase,outputs=read_snapshot(snap)
        v,c=flat_counts(n,h,phase,outputs)
        assert (v,c)==(r["cnf"]["variables"],r["cnf"]["clauses"]),(r["case"],r["mode"],v,c,r["cnf"])
        record=dict(case=r["case"],mode=r["mode"],status=r["status"],n=n,h=h,phase_terms=len(phase),baseline_variables=v,baseline_clauses=c,solver_time=r["result"]["tool_s"],neutral=plan(phase,False),weighted_root_reuse=plan(phase,True))
        results.append(record)
        slim={k:v for k,v in record.items() if k not in ("neutral","weighted_root_reuse")}
        for name in ("neutral","weighted_root_reuse"):
            slim[name]={k:v for k,v in record[name].items() if k!="chosen"}
            if "clause_saving" in slim[name]:
                slim[name]["saving_fraction"]=slim[name]["clause_saving"]/c
        print("D1C_ARM",json.dumps(slim),flush=True)
    assert len(results)==26 and sum(r["mode"]=="hybrid" for r in results)==9
    summary=dict(arms=len(results),hybrid=9,baseline_count_parity=26,solver_calls=0)
    for name in ("neutral","weighted_root_reuse"):
        eligible=[r for r in results if r[name]["status"]=="OK"]
        summary[name]=dict(eligible=len(eligible),positive_saving=sum(r[name]["clause_saving"]>0 for r in eligible),hybrid_positive=sum(r["mode"]=="hybrid" and r[name]["clause_saving"]>0 for r in eligible),max_saving_fraction=max(r[name]["clause_saving"]/r["baseline_clauses"] for r in eligible))
    (out/"phase_pair_screen.json").write_text(json.dumps(dict(provenance=provenance,rows=results,summary=summary),indent=2)+"\n")
    print("D1C_SUMMARY",json.dumps(summary),flush=True)

if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""D1e: existing weighted proper-subset roots, bounded offline cost model.
Every original weighted literal remains; only the conjunction operands change.
No solver, weight arithmetic, new variables, or production code.
"""
import hashlib
import itertools
import json
from pathlib import Path
import sys
from eq_dag_phase_screen import read_snapshot,flat_counts,tests

BASE="8811544a462338569bc5a375e3df41fdd18ea3b8"
TREE="b7ebfdcf3cfdac115bf971fddc92306bc66adde8"
# Count tuple membership probes, not wall time. Cap applies separately per arm.
CAP=3000000

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def plan(phase,cap=CAP):
    # One root of strictly lower degree per weighted monomial. Probe
    # immediate subsets first, then quadratic roots only if none exists.
    # No powerset enumeration. Acyclic by decreasing degree; all root
    # literals already have exactly one original weight and full definition.
    roots=set(phase)
    choices={}
    probes=0
    for m in sorted(roots,key=lambda m:(len(m),m)):
        if len(m)<3:
            continue
        root=None
        candidates=(m[:i]+m[i+1:] for i in range(len(m)))
        for p in candidates:
            probes+=1
            if probes>cap:
                return dict(status="WORK_CAP",probes=probes,cap=cap)
            if p in roots:
                root=p
                break
        if root is None and len(m)>3:
            for p in itertools.combinations(m,2):
                probes+=1
                if probes>cap:
                    return dict(status="WORK_CAP",probes=probes,cap=cap)
                if p in roots:
                    root=p
                    break
        if root is not None:
            assert len(root)>=2 and len(root)<len(m) and set(root)<set(m)
            choices[m]=root
    saving=sum(len(r)-1 for r in choices.values())
    depth={}
    for m in sorted(roots,key=lambda m:(len(m),m)):
        depth[m]=1+depth[choices[m]] if m in choices else 1
    return dict(status="OK",probes=probes,cap=cap,covered=len(choices),immediate=sum(len(m)==len(r)+1 for m,r in choices.items()),distinct_roots=len(set(choices.values())),max_chain_depth=max(depth.values(),default=0),clause_saving=saving,literal_saving=3*saving,new_variables=0,choices=[dict(monomial=list(m),root=list(r)) for m,r in choices.items()])

def controls():
    tests()
    p={(0,1):1,(0,1,2):2,(0,1,2,3):3,(0,1,2,3,4):4}
    a=plan(p)
    assert a["clause_saving"]==6 and a["literal_saving"]==18
    assert a["new_variables"]==0 and a["max_chain_depth"]==4
    assert plan(p,0)["status"]=="WORK_CAP"
    assert plan({(0,1):1,(0,1,2,3,4):2})["clause_saving"]==1
    assert plan({(0,1,2,3):1})["clause_saving"]==0
    # Exhaustive Boolean evaluation of this small chained weighted DAG.
    # Check each original truth value, not merely the sum or a sign parity.
    choices={tuple(x["monomial"]):tuple(x["root"]) for x in a["choices"]}
    for bits in itertools.product((False,True),repeat=5):
        values={}
        for m in sorted(p,key=lambda m:(len(m),m)):
            r=choices.get(m)
            values[m]=(values[r] and all(bits[i] for i in m if i not in r)) if r else all(bits[i] for i in m)
            assert values[m]==all(bits[i] for i in m)

def main():
    controls()
    src,out=map(Path,sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    assert (src/"head.txt").read_text().strip()==BASE
    assert (src/"tree.txt").read_text().strip()==TREE
    prov=json.loads((src/"provenance.json").read_text())
    assert prov["head"]==BASE and prov["tree"]==TREE
    rows=[json.loads(x) for x in (src/"rows.jsonl").read_text().splitlines()]
    assert len(rows)==19 and len({r["case"] for r in rows})==19
    reports=[]
    for r in rows:
        arm=src/(r["case"]+"-"+r["mode"])
        assert r["mode"]=="hybrid"
        if r["residual_sha256"]:
            assert sha(arm/"residual.tsv")==r["residual_sha256"]
        if r["cnf"]:
            assert sha(arm/"actual.cnf")==r["cnf"]["sha256"]
        if not (r["cnf"] and r["residual_sha256"]):
            continue
        n,h,p,f=read_snapshot(arm/"residual.tsv")
        v,c=flat_counts(n,h,p,f)
        assert (v,c)==(r["cnf"]["variables"],r["cnf"]["clauses"])
        a=plan(p)
        if a["status"]=="OK":
            a["predicted_clauses"]=c-a["clause_saving"]
            a["predicted_literals"]=r["cnf"]["literals"]-a["literal_saving"]
            a["saving_fraction"]=a["clause_saving"]/c
        record=dict(case=r["case"],status=r["status"],solver_time=r["result"]["tool_s"],phase_terms=len(p),baseline_variables=v,baseline_clauses=c,baseline_literals=r["cnf"]["literals"],residual_sha256=r["residual_sha256"],cnf_sha256=r["cnf"]["sha256"],plan=a)
        reports.append(record)
        print("D1E_ARM",json.dumps(dict(record,plan={k:v for k,v in a.items() if k!="choices"})),flush=True)
    assert len(reports)==12
    eligible=[r for r in reports if r["plan"]["status"]=="OK"]
    positive=[r for r in eligible if r["plan"]["clause_saving"]>0]
    summary=dict(arms=len(reports),eligible=len(eligible),positive=len(positive),baseline_count_parity=len(reports),solver_calls=0,costly_positive=[r["case"] for r in positive if r["status"]=="Timeout" or (r["solver_time"].startswith("Some(") and float(r["solver_time"][5:-1])>=10)])
    (out/"subset_root_screen.json").write_text(json.dumps(dict(provenance=prov,rows=reports,summary=summary),indent=2)+"\n")
    print("D1E_SUMMARY",json.dumps(summary),flush=True)

if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""D1d held-out residual cost census; reuse original validated D1c model."""
import hashlib
import json
import sys
from pathlib import Path
from eq_dag_phase_screen import read_snapshot, flat_counts, plan, tests

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def main():
    tests()
    src, manifest, out=map(Path,sys.argv[1:])
    m=json.loads(manifest.read_text())
    prov=json.loads((src/"provenance.json").read_text())
    assert prov["baseline"]==m["baseline"] and prov["manifest_sha256"]==sha(manifest)
    assert prov["head"]==(src/"head.txt").read_text().strip()
    assert prov["tree"]==(src/"tree.txt").read_text().strip()
    assert prov["modes"]==["hybrid"] and prov["address_space_mib"]==4096
    rows=[json.loads(x) for x in (src/"rows.jsonl").read_text().splitlines()]
    assert len(rows)==len(m["cases"])==19
    assert {(r["case"],r["mode"]) for r in rows}=={(c["id"],"hybrid") for c in m["cases"]}
    reports=[]
    for r in rows:
        arm=src/(r["case"]+"-"+r["mode"])
        a=dict(case=r["case"],family=r["family"],status=r["status"],expected=r["expected"],expected_disagreement=r["expected_disagreement"],result=r["result"],metrics=r["metrics"],rss_individual_kib=r["rss_individual_kib"],cnf=r["cnf"],residual_sha256=r["residual_sha256"])
        if r["residual_sha256"]:
            assert sha(arm/"residual.tsv")==r["residual_sha256"]
        if r["cnf"]:
            assert sha(arm/"actual.cnf")==r["cnf"]["sha256"]
        if r["cnf"] and r["residual_sha256"]:
            n,h,p,f=read_snapshot(arm/"residual.tsv")
            v,c=flat_counts(n,h,p,f)
            assert (v,c)==(r["cnf"]["variables"],r["cnf"]["clauses"])
            a.update(n=n,h=h,baseline_count_parity=True,neutral=plan(p,False),weighted_root_reuse=plan(p,True))
            for k in ("neutral","weighted_root_reuse"):
                if a[k]["status"]=="OK":
                    a[k]["saving_fraction"]=a[k]["clause_saving"]/c
        reports.append(a)
        slim=dict(a)
        for k in ("neutral","weighted_root_reuse"):
            if k in slim:
                slim[k]={x:y for x,y in slim[k].items() if x!="chosen"}
        print("D1D_ARM",json.dumps(slim),flush=True)
    paired=[r for r in reports if r.get("baseline_count_parity")]
    summary=dict(arms=len(reports),residuals=sum(bool(r["residual_sha256"]) for r in reports),actual_cnfs=sum(bool(r["cnf"]) for r in reports),paired=len(paired),expected_disagreements=sum(r["expected_disagreement"] for r in reports),status_counts={s:sum(r["status"]==s for r in reports) for s in sorted({r["status"] for r in reports})})
    for k in ("neutral","weighted_root_reuse"):
        eligible=[r for r in paired if r[k]["status"]=="OK"]
        pos=[r for r in eligible if r[k]["clause_saving"]>0]
        summary[k]=dict(eligible=len(eligible),positive=len(pos),families=sorted({r["family"] for r in pos}),max_saving_fraction=max((r[k]["saving_fraction"] for r in eligible),default=None),costly_positive=[r["case"] for r in pos if r["status"]=="Timeout" or (r["result"]["tool_s"].startswith("Some(") and float(r["result"]["tool_s"][5:-1])>=10)])
    out.write_text(json.dumps(dict(provenance=prov,rows=reports,summary=summary),indent=2)+"\n")
    print("D1D_SUMMARY",json.dumps(summary),flush=True)

if __name__=="__main__":
    main()

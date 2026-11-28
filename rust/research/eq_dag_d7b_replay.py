#!/usr/bin/env python3
"""D7b replay actual Factored CNFs; diagnosis, no router tuning."""
import ast,json,math,sys
from fractions import Fraction as F
from pathlib import Path
from eq_dag_d3_ab import sha,DELTA
from eq_dag_e1d_parity import read_snapshot
from eq_dag_e1a_census import scan
from eq_dag_e1e_encode import audit
from eq_dag_e1b_encode import build as flat_build,weight_fn,test
from eq_dag_e1c_archive_replay import parse,match,controls
from eq_dag_e1f_screen import error_fn,audit_weights,trace_rank,upper

HEAD="749327480045ee52cfd7eab8f8999e0f2125c011"
TREE="38f1af334c122c404c5781898fe34d098aba4543"
def main():
    src,weight_lib,interval_lib,out=map(lambda p:Path(p).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    assert (src/"head.txt").read_text().strip()==HEAD
    assert (src/"tree.txt").read_text().strip()==TREE
    prov=json.loads((src/"provenance.json").read_text())
    assert prov["head"]==HEAD and prov["frozen_router"]=="9168826d9db2f0c7b56b07966806d71f8d798ef2"
    rows=list(map(json.loads,(src/"rows.jsonl").read_text().splitlines()))
    assert len(rows)==36
    changed=[r for r in rows if r["variant"]=="combined" and r["route"]!="flat"]
    assert {r["case"] for r in changed}=={"grover-noancilla_5_random_pauli","feynman_grover_5_eq"} and len(changed)==2
    weight=weight_fn(weight_lib);err=error_fn(interval_lib);controls();test(weight)
    reports=[]
    for r in changed:
        case=r["case"];assert r["route"]=="factored"
        a=next(x for x in rows if x["case"]==case and x["period"]==r["period"] and x["variant"]=="main")
        left=src/f"{case}-{r['period']}-main";right=src/f"{case}-{r['period']}-combined"
        snap=right/"residual.tsv";original=left/"actual.cnf";candidate=right/"actual.cnf"
        assert sha(left/"residual.tsv")==sha(snap)==a["residual_sha256"]==r["residual_sha256"]
        assert sha(original)==a["cnf"]["sha256"] and sha(candidate)==r["cnf"]["sha256"]
        n,h,p,f=read_snapshot(snap.read_bytes())
        domain=ast.literal_eval(next(l.split("\t")[1] for l in snap.read_text().splitlines() if l.startswith("vars\t")))
        assert domain==sorted(set(domain)) and len(domain)==n+h
        bits=max(96,32*math.ceil((-2*math.log2(1e-8)+math.ceil(math.log2(max(1,len(p))))+32)/32))
        plan=scan(p,"mixed",cap=50_000)
        assert plan["status"]=="OK" and plan["exact_replay"]
        q=plan["choices"];work=plan["probes"]
        e=flat_build(domain,n,p,f,q,weight,bits)
        assert audit(e,domain,f,n).encode()==candidate.read_bytes()
        flat=flat_build(domain,n,p,f,[],weight,bits)
        canonical=out/(case+"-canonical-flat.cnf")
        canonical.write_text(flat.render())
        # Decode actual archived Flat independently and verify full primary
        # bijection, not merely weight multiset parity.
        old=parse(original.read_bytes(),n,domain);new=parse(canonical.read_bytes(),n,domain)
        ids={v:i+1 for i,v in enumerate(domain)}
        assert new[0]==set(ids.values()) and new[3]==[ids[i] for i in range(n)]
        assert [m for m,w in new[1]]==[tuple(ids[v] for v in m) for m in sorted(p)]
        assert new[2]==[{tuple(ids[v] for v in m) for m in f[i]} for i in range(n)]
        ok,mapping,iterations,ambiguous=match(old,new)
        x,nx=audit_weights(canonical,lambda cb:flat_build(domain,n,p,f,[],cb,bits),err)
        y,ny=audit_weights(candidate,lambda cb:flat_build(domain,n,p,f,q,cb,bits),err)
        total=x+y;assert total<1
        rank=trace_rank(n,domain,f);bound=total/(1-total)*F(2)**((h+1)//2-rank)
        row=dict(case=case,original_sha256=sha(original),candidate_sha256=sha(candidate),residual_sha256=sha(snap),canonical_sha256=sha(canonical),phase_terms=len(p),factor_blocks=len(q),work=work,bits=bits,exact_phase_replay=True,actual_candidate_byte_parity=True,archived_flat_bijection=ok,refinement_rounds=iterations,ambiguous_color_classes=ambiguous,mapping=mapping if ok else None,flat_weight_count=nx,factored_weight_count=ny,flat_error_sum=upper(x),factored_error_sum=upper(y),rank=rank,h=h,normalized_bound=upper(bound),passes_1e20=ok and bound<=DELTA,passes_1e8=ok and bound<=F(1,10**8),exact_fraction_bound=str(bound),scope="finite serialized input weights only, not solver arithmetic or source EQ certificate")
        reports.append(row);print("D7B_CASE",json.dumps({k:v for k,v in row.items() if k not in ("mapping","exact_fraction_bound")}),flush=True)
    summary=dict(cases=len(reports),exact_replay=sum(r["exact_phase_replay"] for r in reports),candidate_bytes=sum(r["actual_candidate_byte_parity"] for r in reports),archived_bijection=sum(r["archived_flat_bijection"] for r in reports),bound_1e20=sum(r["passes_1e20"] for r in reports),bound_1e8=sum(r["passes_1e8"] for r in reports),solver_calls=0)
    (out/"receipts.json").write_text(json.dumps(dict(summary=summary,rows=reports),indent=2)+"\n")
    print("D7B_SUMMARY",json.dumps(summary),flush=True)
    assert summary["cases"]==summary["exact_replay"]==summary["candidate_bytes"]==summary["archived_bijection"]==2
if __name__=="__main__":main()

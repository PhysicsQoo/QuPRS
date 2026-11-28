#!/usr/bin/env python3
"""D8b replay every distinct corrected-baseline changed CNF receipt; no solves."""
import ast,json,math,sys
from fractions import Fraction as F
from pathlib import Path
from eq_dag_d3_ab import sha,DELTA
from eq_dag_e1d_parity import read_snapshot,invert,replay
from eq_dag_e1a_census import scan
from eq_dag_e1e_encode import build as parity_build,audit,fixture
from eq_dag_e1b_encode import build as flat_build,weight_fn,test
from eq_dag_e1c_archive_replay import parse,match,controls
from eq_dag_e1f_screen import error_fn,audit_weights,trace_rank,upper

HEAD="0a2b3b0e8a9bcfa6d3d0a54b38e0fe7f2c6b0087"
TREE="af41bc232651f7e111ac9069c707ff330448be1d"
def main():
    src,weight_lib,interval_lib,out=map(lambda p:Path(p).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    assert (src/"head.txt").read_text().strip()==HEAD
    assert (src/"tree.txt").read_text().strip()==TREE
    prov=json.loads((src/"provenance.json").read_text())
    assert prov["head"]==HEAD and prov["frozen_router"]=="9168826d9db2f0c7b56b07966806d71f8d798ef2"
    rows=list(map(json.loads,(src/"rows.jsonl").read_text().splitlines()))
    assert prov["baseline"]=="d486685f04824c8d3d07097c6ce0693ae6d47b7a"
    assert len(rows)==86
    assert len({(r["case"],r["period"],r["variant"]) for r in rows})==86
    assert all(r["returncode"]==0 and r["status"] in {"equivalent","equivalent*","not_equivalent"} for r in rows)
    changed=[r for r in rows if r["variant"]=="combined" and r["route"]!="flat"]
    expected={"vqe_16":"parity","grover-noancilla_negative_5":"factored","qwalk-noancilla_negative_5":"factored","vqe_16_neq":"parity"}
    assert {r["case"] for r in changed}==set(expected) and len(changed)==22
    seen={}
    # Verify actual bytes for ALL repeated arms, including unchanged Flat and RR bypass.
    for r in rows:
        d=src/f"{r['case']}-{r['period']}-{r['variant']}"
        assert sha(d/"residual.tsv")==r["residual_sha256"]
        if r["cnf"]:assert sha(d/"actual.cnf")==r["cnf"]["sha256"]
        else:assert not (d/"actual.cnf").exists() and r["result"]["solver_invoked"]=="false"
        if r["variant"]=="combined":
            a=next(x for x in rows if x["case"]==r["case"] and x["period"]==r["period"] and x["variant"]=="main")
            assert a["residual_sha256"]==r["residual_sha256"] and a["status"]==r["status"]
            if r["route"]=="flat":assert a["cnf"]==r["cnf"]
            else:
                assert r["route"]==expected[r["case"]]
                key=(r["case"],r["route"],r["residual_sha256"],a["cnf"]["sha256"],r["cnf"]["sha256"])
                seen.setdefault(key,r)
    assert len(seen)==4
    representatives=list(seen.values())
    weight=weight_fn(weight_lib);err=error_fn(interval_lib);controls();fixture(weight);test(weight)
    reports=[]
    for r in representatives:
        case=r["case"];route=r["route"]
        a=next(x for x in rows if x["case"]==case and x["period"]==r["period"] and x["variant"]=="main")
        left=src/f"{case}-{r['period']}-main";right=src/f"{case}-{r['period']}-combined"
        snap=right/"residual.tsv";original=left/"actual.cnf";candidate=right/"actual.cnf"
        assert sha(left/"residual.tsv")==sha(snap)==a["residual_sha256"]==r["residual_sha256"]
        assert sha(original)==a["cnf"]["sha256"] and sha(candidate)==r["cnf"]["sha256"]
        n,h,p,f=read_snapshot(snap.read_bytes())
        domain=ast.literal_eval(next(l.split("\t")[1] for l in snap.read_text().splitlines() if l.startswith("vars\t")))
        assert domain==sorted(set(domain)) and len(domain)==n+h
        bits=max(96,32*math.ceil((-2*math.log2(1e-8)+math.ceil(math.log2(max(1,len(p))))+32)/32))
        if route=="parity":
            rad={m:c[1] for m,c in p.items() if c[1]}
            q,work=invert(rad,200_000)
            assert q is not None and replay(q)==rad
            def candidate_build(cb):return parity_build(domain,n,p,f,q,cb,bits)[0]
        else:
            plan=scan(p,"mixed",cap=50_000)
            assert plan["status"]=="OK" and plan["exact_replay"]
            q=plan["choices"];work=plan["probes"]
            def candidate_build(cb):return flat_build(domain,n,p,f,q,cb,bits)
        e=candidate_build(weight)
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
        y,ny=audit_weights(candidate,candidate_build,err)
        total=x+y;assert total<1
        rank=trace_rank(n,domain,f);bound=total/(1-total)*F(2)**((h+1)//2-rank)
        row=dict(case=case,route=route,original_sha256=sha(original),candidate_sha256=sha(candidate),residual_sha256=sha(snap),canonical_sha256=sha(canonical),phase_terms=len(p),replacement_terms_or_blocks=len(q),work=work,bits=bits,exact_phase_replay=True,actual_candidate_byte_parity=True,archived_flat_bijection=ok,refinement_rounds=iterations,ambiguous_color_classes=ambiguous,mapping=mapping if ok else None,flat_weight_count=nx,candidate_weight_count=ny,flat_error_sum=upper(x),candidate_error_sum=upper(y),rank=rank,h=h,normalized_bound=upper(bound),passes_1e20=ok and bound<=DELTA,passes_1e8=ok and bound<=F(1,10**8),exact_fraction_bound=str(bound),scope="finite serialized input weights only, not solver arithmetic or NEQ certificate")
        reports.append(row);print("D8B_CASE",json.dumps({k:v for k,v in row.items() if k not in ("mapping","exact_fraction_bound")}),flush=True)
    summary=dict(arms_verified=len(rows),changed_arms=len(changed),cases=len(reports),exact_replay=sum(r["exact_phase_replay"] for r in reports),candidate_bytes=sum(r["actual_candidate_byte_parity"] for r in reports),archived_bijection=sum(r["archived_flat_bijection"] for r in reports),bound_1e20=sum(r["passes_1e20"] for r in reports),bound_1e8=sum(r["passes_1e8"] for r in reports),solver_calls=0)
    (out/"receipts.json").write_text(json.dumps(dict(summary=summary,rows=reports),indent=2)+"\n")
    print("D8B_SUMMARY",json.dumps(summary),flush=True)
    assert summary["cases"]==summary["exact_replay"]==summary["candidate_bytes"]==summary["archived_bijection"]==summary["bound_1e20"]==summary["bound_1e8"]==4
    print("D8B_REPLAY_PASS")
if __name__=="__main__":main()

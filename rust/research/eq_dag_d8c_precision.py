#!/usr/bin/env python3
"""D8c offline weight precision sweep; no solver, no router or tolerance changes."""
import ast,json,math,sys
from fractions import Fraction as F
from pathlib import Path
from eq_dag_d3_ab import sha,DELTA
from eq_dag_e1d_parity import read_snapshot,invert,replay
from eq_dag_e1e_encode import build as parity_build,audit,fixture
from eq_dag_e1b_encode import build as flat_build,weight_fn
from eq_dag_e1c_archive_replay import parse,match,controls
from eq_dag_e1f_screen import error_fn,audit_weights,trace_rank,upper
def topology(path):
    return "\n".join(l for l in path.read_text().splitlines() if not l.startswith("c p weight "))
def main():
    src,weight_lib,interval_lib,out=map(lambda p:Path(p).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    assert (src/"head.txt").read_text().strip()=="0a2b3b0e8a9bcfa6d3d0a54b38e0fe7f2c6b0087"
    assert (src/"tree.txt").read_text().strip()=="af41bc232651f7e111ac9069c707ff330448be1d"
    rows=list(map(json.loads,(src/"rows.jsonl").read_text().splitlines()))
    weight=weight_fn(weight_lib);err=error_fn(interval_lib);controls();fixture(weight)
    results=[]
    for case in ("vqe_16","vqe_16_neq"):
        a,b=[next(r for r in rows if r["case"]==case and r["period"]==1 and r["variant"]==v) for v in ("main","combined")]
        left=src/f"{case}-1-main";right=src/f"{case}-1-combined"
        snap=right/"residual.tsv";original=left/"actual.cnf";candidate=right/"actual.cnf"
        assert sha(left/"residual.tsv")==sha(snap)==a["residual_sha256"]==b["residual_sha256"]
        assert sha(original)==a["cnf"]["sha256"] and sha(candidate)==b["cnf"]["sha256"] and b["route"]=="parity"
        n,h,p,f=read_snapshot(snap.read_bytes())
        domain=ast.literal_eval(next(l.split("\t")[1] for l in snap.read_text().splitlines() if l.startswith("vars\t")))
        assert len(domain)==n+h and sorted(set(domain))==domain
        rad={m:c[1] for m,c in p.items() if c[1]}
        q,work=invert(rad,200_000);assert q is not None and replay(q)==rad
        rank=trace_rank(n,domain,f);exponent=(h+1)//2-rank
        reports=[];flat0=None;parity0=None
        for bits in (96,128,160,192):
            flat=out/f"{case}-{bits}-flat.cnf";parity=out/f"{case}-{bits}-parity.cnf"
            flat.write_text(flat_build(domain,n,p,f,[],weight,bits).render())
            parity.write_text(audit(parity_build(domain,n,p,f,q,weight,bits)[0],domain,f,n))
            if bits==96:
                assert parity.read_bytes()==candidate.read_bytes()
                ok,_,_,_=match(parse(original.read_bytes(),n,domain),parse(flat.read_bytes(),n,domain))
                assert ok
                flat0=topology(flat);parity0=topology(parity)
            else:
                assert topology(flat)==flat0 and topology(parity)==parity0
            x,nx=audit_weights(flat,lambda cb:flat_build(domain,n,p,f,[],cb,bits),err)
            y,ny=audit_weights(parity,lambda cb:parity_build(domain,n,p,f,q,cb,bits)[0],err)
            total=x+y;assert total<1
            bound=total/(1-total)*F(2)**exponent
            row=dict(case=case,bits=bits,h=h,rank=rank,amplification_exponent=exponent,flat_weight_count=nx,parity_weight_count=ny,flat_sha256=sha(flat),parity_sha256=sha(parity),flat_bytes=flat.stat().st_size,parity_bytes=parity.stat().st_size,normalized_bound=upper(bound),exact_bound=str(bound),passes_1e20=bound<=DELTA,topology_unchanged=True)
            reports.append(row);print("D8C_POINT",json.dumps({k:v for k,v in row.items() if k!="exact_bound"}),flush=True)
        passed=[r["bits"] for r in reports if r["passes_1e20"]]
        result=dict(case=case,minimum_tested_passing_bits=min(passed) if passed else None,rows=reports)
        results.append(result);print("D8C_CASE",json.dumps(dict(case=case,minimum_tested_passing_bits=result["minimum_tested_passing_bits"])),flush=True)
    (out/"receipts.json").write_text(json.dumps(dict(rows=results,solver_calls=0,scope="offline canonical re-encoding, not actual native or solver performance admission"),indent=2)+"\n")
    assert all(r["minimum_tested_passing_bits"] is not None for r in results)
    print("D8C_PRECISION_SWEEP_COMPLETE")
if __name__=="__main__":main()

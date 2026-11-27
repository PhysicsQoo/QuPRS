#!/usr/bin/env python3
"""E1a: bounded exact phase-block census on real sealed WMC residuals.
No numeric weight generation or solver calls. Turn component modulo 1;
stored rational radian component exact, independent of turns.
"""
from collections import Counter
from fractions import Fraction
from itertools import combinations,product
import json,re,sys
from pathlib import Path
from eq_dag_phase_screen import read_snapshot,flat_counts
from eq_dag_d3_ab import sha

CAP=3000000
SOURCES=(("e744768dc3ed8b2b86a65295da1000ed4d0431c9","4189183f6ff4bc04fed22ad9a5a246e9c2512b53",34,26),("8811544a462338569bc5a375e3df41fdd18ea3b8","b7ebfdcf3cfdac115bf971fddc92306bc66adde8",19,12))
RAD=re.compile(r"Some\(Ratio \{ numer: (-?\d+), denom: (\d+) \}\)")
ZERO=(Fraction(0),Fraction(0))

def norm(a,b):
    return (a%1,b)

def coeff(raw):
    n,d,rad,symbols=raw
    if symbols!="{}":
        return None
    if rad=="None":
        b=Fraction(0)
    else:
        m=RAD.fullmatch(rad)
        if m is None:
            raise ValueError("unknown exact radian snapshot format: "+rad[:160])
        b=Fraction(int(m[1]),int(m[2]))
    return norm(Fraction(int(n),int(d)),b)

def scale(c,k):
    return norm(c[0]*k,c[1]*k)

def add(a,b):
    return norm(a[0]+b[0],a[1]+b[1])

def expansion(kind,a,b,c):
    u=tuple(sorted(set(a)|set(b)))
    if kind=="xor":
        return {a:c,b:c,u:scale(c,-2)}
    assert kind=="complement" and len(b)==1 and b[0] not in a
    return {a:c,u:scale(c,-1)}

def cost(kind,a,b):
    u=tuple(sorted(set(a)|set(b)))
    if kind=="complement":
        # weighted conjunction of A and the negative literal
        return dict(factors=1,variables=1,clauses=len(a)+1,old_clauses=len(a)+len(u)+2,new_clauses=len(u)+1)
    # A and B are neutral AND outputs unless primary singletons.
    aux=[m for m in (a,b) if len(m)!=1]
    before=len(a)+len(b)+len(u)+3
    after=sum(len(m)+1 for m in aux)+4
    return dict(factors=2,variables=2-len(aux),clauses=before-after,old_clauses=before,new_clauses=after)

def scan(p,policy,cap=CAP):
    # Independent disjoint-term plans; mixed takes complement first at each
    # maximal support. No partial claims if work cap reached.
    unused=set(p)
    chosen=[]
    probes=0
    for u in sorted(p,key=lambda m:(-len(m),m)):
        if u not in unused or not u:
            continue
        children=[u[:i]+u[i+1:] for i in range(len(u))]
        found=False
        if policy in ("complement","mixed"):
            for i,a in enumerate(children):
                probes+=1
                if probes>cap:
                    return dict(status="WORK_CAP",probes=probes)
                if a in unused and p[u]==scale(p[a],-1):
                    b=(u[i],)
                    chosen.append(("complement",a,b,p[a]))
                    unused.difference_update((u,a))
                    found=True
                    break
        if found or policy=="complement" or len(u)<2:
            continue
        for a,b in combinations(children,2):
            probes+=1
            if probes>cap:
                return dict(status="WORK_CAP",probes=probes)
            if a in unused and b in unused and p[a]==p[b] and p[u]==scale(p[a],-2):
                chosen.append(("xor",a,b,p[a]))
                unused.difference_update((u,a,b))
                break
    # Reconstruct all original coefficients modulo turns and exactly in radians.
    # Distinct support consumption is checked separately.
    restored={m:p[m] for m in unused}
    consumed=set()
    totals=Counter()
    records=[]
    for kind,a,b,c in chosen:
        assert set(a)<set(a)|set(b)
        ex=expansion(kind,a,b,c)
        assert not (set(ex)&(consumed|unused))
        consumed.update(ex)
        for m,v in ex.items():
            restored[m]=add(restored.get(m,ZERO),v)
        savings=cost(kind,a,b)
        totals.update({k:savings[k] for k in ("factors","variables","clauses")})
        records.append(dict(kind=kind,a=a,b=b,coefficient=[str(v) for v in c],cost=savings))
    assert restored==p and len(consumed)+len(unused)==len(p)
    return dict(status="OK",probes=probes,blocks=len(chosen),kinds=dict(Counter(x[0] for x in chosen)),weighted_factor_saving=totals["factors"],variable_saving=totals["variables"],clause_saving=totals["clauses"],exact_replay=True,choices=records)

def controls():
    c=coeff(("1","8","Some(Ratio { numer: -123, denom: 1000 })","{}"))
    a,b=(0,1),(0,2)
    p=expansion("xor",a,b,c)
    assert scan(p,"xor")["weighted_factor_saving"]==2
    assert scan(p,"xor")["variable_saving"]==0
    q=expansion("complement",a,(2,),c)
    assert scan(q,"complement")["weighted_factor_saving"]==1
    assert scan(q,"complement")["clause_saving"]==len(a)+1
    for kind,left,right,poly in (("xor",a,b,p),("complement",a,(2,),q)):
        for bits in product((0,1),repeat=3):
            ev=lambda m:all(bits[i] for i in m)
            val=ZERO
            for m,k in poly.items():
                val=add(val,scale(k,int(ev(m))))
            expected=int(ev(left)^ev(right)) if kind=="xor" else int(ev(left) and not ev(right))
            assert val==scale(c,expected)
    bad=dict(p);bad[(0,1,2)]=add(bad[(0,1,2)],(Fraction(0),Fraction(1,10**40)))
    assert scan(bad,"xor")["blocks"]==0
    assert scan(p,"xor",0)["status"]=="WORK_CAP"
    assert coeff(("0","1","None","{1: FreeRational { numer: 1, denom: 2 }}")) is None

def main():
    controls()
    d1,d2,out=map(Path,sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    reports=[]
    for src,(head,tree,nrows,npairs) in zip((d1,d2),SOURCES):
        assert (src/"head.txt").read_text().strip()==head
        assert (src/"tree.txt").read_text().strip()==tree
        prov=json.loads((src/"provenance.json").read_text())
        assert prov["head"]==head and prov["tree"]==tree
        rows=[json.loads(x) for x in (src/"rows.jsonl").read_text().splitlines()]
        assert len(rows)==nrows and sum(bool(x["cnf"] and x["residual_sha256"]) for x in rows)==npairs
        for r in rows:
            if not (r["cnf"] and r["residual_sha256"]): continue
            arm=src/(r["case"]+"-"+r["mode"])
            assert sha(arm/"residual.tsv")==r["residual_sha256"] and sha(arm/"actual.cnf")==r["cnf"]["sha256"]
            n,h,phase,outputs=read_snapshot(arm/"residual.tsv")
            v,c=flat_counts(n,h,phase,outputs)
            assert (v,c)==(r["cnf"]["variables"],r["cnf"]["clauses"])
            parsed={m:coeff(raw) for m,raw in phase.items()}
            a=dict(source_head=head,case=r["case"],family=r["family"],mode=r["mode"],status=r["status"],phase_terms=len(phase),radian_terms=sum(raw[2]!="None" for raw in phase.values()),symbolic_terms=sum(x is None for x in parsed.values()),variables=v,clauses=c,solver_time=r["result"]["tool_s"],residual_sha256=r["residual_sha256"])
            if a["symbolic_terms"]:
                a["plans"]={k:dict(status="SYMBOLIC_UNSUPPORTED") for k in ("xor","complement","mixed")}
            else:
                a["plans"]={k:scan(parsed,k) for k in ("xor","complement","mixed")}
            reports.append(a)
            print("E1A_ARM",json.dumps(dict(a,plans={k:{x:y for x,y in z.items() if x!="choices"} for k,z in a["plans"].items()})),flush=True)
    assert len(reports)==38
    summary=dict(arms=len(reports),hybrid=sum(x["mode"]=="hybrid" for x in reports),solver_calls=0,baseline_count_parity=len(reports),scope="bounded adjacent-support exact phase-block census, no numeric encoding")
    for k in ("xor","complement","mixed"):
        ok=[r for r in reports if r["plans"][k]["status"]=="OK"]
        pos=[r for r in ok if r["plans"][k]["weighted_factor_saving"]>0]
        summary[k]=dict(eligible=len(ok),positive=len(pos),hybrid_positive=sum(x["mode"]=="hybrid" for x in pos),max_factor_reduction=max((r["plans"][k]["weighted_factor_saving"]/r["phase_terms"] for r in pos),default=0))
    (out/"phase_factor_census.json").write_text(json.dumps(dict(summary=summary,rows=reports),indent=2)+"\n")
    print("E1A_SUMMARY",json.dumps(summary),flush=True)
if __name__=="__main__":
    main()

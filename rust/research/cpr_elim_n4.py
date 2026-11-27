"""N4 independent prefix matrix oracle. Explicit lift arms are diagnostics,
not policy admissions. Zero reachable Elim events is bounded negative evidence.
All arithmetic is exact in Z[zeta_8] / sqrt(2)^h; no floating tolerance.
"""
import json
import sys
import itertools
from cpr_normalization_n1 import matrix, equal, add, mul, root, ZERO, ONE

# Independently frozen gate streams. True = right multiplication by adjoint.
CASES = {
    "hh": [("h",0),("h",0),("h",1,True),("h",1,True)],
    "omega_t": [("h",0),("s",0),("h",0),("t",0),("h",0),("cx",0,1),("h",1)],
    "nonlinear": [("h",1),("h",2),("h",0),("ccx",0,1,2),("ccx",1,2,0),("h",0),("h",1),("h",2)],
    "bra_ket": [("h",0,True),("h",1),("ccx",1,2,0,True),("t",0,True),("cx",0,2),("h",2,True),("s",1),("h",1)],
    "nonlinear_phase": [("h",0),("h",1),("ccx",0,1,2),("t",2),("cz",1,2),("h",2),("x",0,True),("h",0),("h",1)],
    "mixed_inverse": [("h",0),("h",1),("ccx",0,1,2),("s",2),("h",0,True),("h",1,True),("ccx",0,1,2,True),("s",2,True)],
}
ARMS=("original","output_lift","input_lift")

def ident(n):
    return {(x,x):ONE for x in itertools.product((0,1),repeat=n)},0

def transitions(x, kind, q, adj=False):
    if kind=="h":
        a=q[0]
        for v in (0,1):
            y=list(x);y[a]=v
            yield tuple(y),root(4*x[a]*v)
    elif kind in ("s","t","cz"):
        exponent = (2 if kind=="s" else 1)*x[q[0]] if kind!="cz" else 4*x[q[0]]*x[q[1]]
        yield x,root(-exponent if adj else exponent)
    else:
        y=list(x)
        if kind=="x":y[q[0]]^=1
        elif kind=="cx":y[q[1]]^=x[q[0]]
        elif kind=="ccx":y[q[2]]^=x[q[0]]*x[q[1]]
        else:raise AssertionError(kind)
        yield tuple(y),ONE

def step(state,op):
    m,h=state;kind,*q=op
    bra=bool(q and q[-1] is True)
    if bra:q.pop()
    out={}
    if bra:
        for x in itertools.product((0,1),repeat=3):
            for z,c in transitions(x,kind,q,True):
                for (i,y),v in m.items():
                    if i==z:out[x,y]=add(out.get((x,y),ZERO),mul(c,v))
    else:
        for (x,z),v in m.items():
            for y,c in transitions(z,kind,q):
                out[x,y]=add(out.get((x,y),ZERO),mul(v,c))
    return {k:v for k,v in out.items() if v!=ZERO},h+(kind=="h")

def main(path):
    rows=[];summaries=[]
    for l in open(path):
        if l.startswith("CPR_N4_STATE "):rows.append(json.loads(l.split(" ",1)[1]))
        elif l.startswith("CPR_N4_NATIVE "):summaries.append(json.loads(l.split(" ",1)[1]))
    assert len(summaries)==1
    native=summaries[0];assert native["reachable_arms"]==18 and native["synthetic_elim_bits"]==1
    sources={}
    for case,ops in CASES.items():
        src=[ident(3)]
        for op in ops:src.append(step(src[-1],op))
        sources[case]=src
    seen={};kprev={};last_h={};events=0;elim_bits=0;synthetic=[]
    for r in rows:
        case,arm,i,event,k = (r[x] for x in ("case","arm","step","event","k"))
        actual=matrix(r["state"],[],k)
        if case=="synthetic_unitary":
            assert equal(actual,ident(1))
            if event=="elim":assert k==1 and not equal(matrix(r["state"],[],0),ident(1))
            synthetic.append(event);continue
        key=(case,arm);assert case in CASES and arm in ARMS
        assert equal(actual,sources[case][i]),(case,arm,i,event,k)
        h=sum(v>=r["state"]["n"] for v in r["state"]["live"])
        if event=="initial":assert i==0 and k==0 and key not in seen
        elif event=="elim":
            assert k>kprev[key] and last_h[key]-h==k-kprev[key]
            elim_bits+=k-kprev[key];events+=1
        else:
            assert k==kprev[key]
            if event in ("hh","omega"):
                assert last_h[key]-h==(2 if event=="hh" else 1);events+=1
        kprev[key]=k;last_h[key]=h
        seen.setdefault(key,[]).append((i,event))
    assert synthetic==["before","elim"]
    assert set(seen)==set(itertools.product(CASES,ARMS))
    for (case,arm),log in seen.items():
        assert [i for i,e in log if e=="gate"]==list(range(1,len(CASES[case])+1))
        expected=[i for i,op in enumerate(CASES[case],1) if op[0]=="h" or i==len(CASES[case])]
        assert [i for i,e in log if e=="saturated"]==expected
        assert [i for i,e in log if e=="lift"]==([] if arm=="original" else [2])
    assert native["rr_events"]==events and native["reachable_elim_bits"]==elim_bits
    print("CPR_N4_GATE",json.dumps({"arms":len(seen),"receipts":len(rows),"exact_prefix_parity":True,
          "rr_events":events,"reachable_elim_bits":elim_bits,"synthetic_unitary_scale_required":True,
          "status":"PASS","scope":"BOUNDED_AUDIT_NOT_UNREACHABILITY_PROOF"}))

if __name__=="__main__":
    main(sys.argv[1])

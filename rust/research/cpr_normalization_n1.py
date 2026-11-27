"""Exact independent N1 oracle: coefficient vectors in Z[zeta_8], zeta_8^4=-1.
Compare full input/output matrices, including guard rows, with integer
multiplication by sqrt(2)=zeta_8-zeta_8^3. No floats, WMC or native evaluator.
Synthetic receipts establish local semantics, not reachability.
"""
import itertools
import json
from fractions import Fraction
import sys

ZERO=(0,0,0,0)
ONE=(1,0,0,0)
ROOT2=(0,1,0,-1)
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def mul(a,b):
    c=[0]*4
    for i,x in enumerate(a):
        for j,y in enumerate(b):
            q,r=divmod(i+j,4);c[r]+=(-1)**q*x*y
    return tuple(c)
def power2(v,k):
    assert k>=0
    for _ in range(k):v=mul(v,ROOT2)
    return v
def root(k):
    q,r=divmod(k%8,4)
    return tuple((-1)**q if i==r else 0 for i in range(4))
def mon(m,bits):return all(bits[v] for v in m)
def anf(p,bits):return sum(mon(m,bits) for m in p)%2
def matrix(s,rows,k):
    n=s["n"];live=s["live"];hidden=[v for v in live if v>=n]
    assert set(range(n))<=set(live) and len(live)==len(set(live)) and len(hidden)<=12 and n<=4
    assert s["guard"] is None and len(s["outputs"])==n
    p=[]
    for m,c,r in s["phase"]:
        v=8*Fraction(c);assert Fraction(r)==0 and v.denominator==1
        p.append((m,int(v)))
    out={}
    for x in itertools.product((0,1),repeat=n):
        for y in itertools.product((0,1),repeat=len(hidden)):
            bits=dict(zip(range(n),x));bits.update(zip(hidden,y))
            if any(anf(row,bits) for row in rows):continue
            f=tuple(anf(o,bits) for o in s["outputs"])
            e=sum(c for m,c in p if mon(m,bits))
            out[x,f]=add(out.get((x,f),ZERO),root(e))
    return {a:b for a,b in out.items() if b!=ZERO},len(hidden)-k
def equal(a,b):
    x,e=a;y,f=b
    common=max(e,f)
    return {k:power2(v,common-e) for k,v in x.items()}=={k:power2(v,common-f) for k,v in y.items()}
def main(path):
    assert mul(ROOT2,ROOT2)==(2,0,0,0) and root(4)==(-1,0,0,0)
    rows=[json.loads(l.split("CPR_N1_RECEIPT ",1)[1]) for l in open(path) if l.startswith("CPR_N1_RECEIPT ")]
    expected={"output_lift","input_lift","internal_hh","lifted_gate","elim_two","omega_quarter","omega_three_quarters","extract_two","extract_guard_dependency","external_hh_counterexample"}
    assert len(rows)==len(expected) and {r["case"] for r in rows}==expected
    for r in rows:
        a=matrix(r["before"],[],r["k0"]);b=matrix(r["after"],r["rows"],r["k1"])
        if r["case"]=="external_hh_counterexample":
            assert r["expect"]=="rejected_equal" and r["before"]==r["after"] and equal(a,b)
        else:
            assert equal(a,b),r["case"]
            if r["expect"]=="needs_scale":
                assert not equal(a,matrix(r["after"],r["rows"],r["k0"])),r["case"]
        print("CPR_N1_ORACLE",json.dumps({"case":r["case"],"expect":r["expect"],"status":"PASS","denominator_before":a[1],"denominator_after":b[1],"support_before":len(a[0]),"support_after":len(b[0])}),flush=True)
    print("CPR_N1_GATE",json.dumps({"checked":len(rows),"positive_equal":9,"external_pivot_rejected":1,"scale_needed":3,"status":"PASS"}))
if __name__=="__main__":main(sys.argv[1])

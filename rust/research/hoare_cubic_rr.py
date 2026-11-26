"""Bounded research oracle for weighted cubic sums; not production RR.

Only independent unit-weight pivots with unary phase 2,4,6 (mod 8).
Canonical sums, not original phase histograms, are invariant.
"""
import itertools
import json
import time


def ring_mul(a,b):
    c=[0]*4
    for i,x in enumerate(a):
        for j,y in enumerate(b):
            c[(i+j)%4]+=x*y*(-1 if i+j>=4 else 1)
    return c


def root(e):
    e%=8
    a=[0]*4
    a[e%4]=1 if e<4 else -1
    return a


def pick_pivots(n,edges,mode,alternative=False):
    cand=[i for i in range(n) if (1+3*i%7)%2==0 and (not mode or i%3)]
    bad={frozenset(q) for e in edges for q in itertools.combinations(e,2)}
    def valid(p):
        return all(frozenset(q) not in bad for q in itertools.combinations(p,2))
    first=None
    for k in range(len(cand),0,-1):
        choices=[p for p in itertools.combinations(cand,k) if valid(p)]
        if not choices:continue
        if first is None:
            first=choices[0]
            if not alternative:return first
        for p in reversed(choices):
            if p!=first:return p
    raise AssertionError("no distinct admissible pivot set")


def local_check(n,edges,r,m,p,rest,incident,no):
    """Direct summation over removed bits, with original phase expression.

    No reduced bit planes used for reference. Include both admitted and
    rejected residual assignments and verify exact cyclotomic scale.
    """
    seed=0x52524333
    admitted=rejected=0
    for trial in range(256):
        seed=(1664525*seed+1013904223)&0xffffffff
        x=0 if trial==0 else (1<<len(rest))-1 if trial==1 else seed&((1<<len(rest))-1)
        z=sum((1<<i) for j,i in enumerate(rest) if x>>j&1)
        e=sum(r[i] for i in rest if z>>i&1)+4*sum(all(z>>i&1 for i in edge) for edge in no)
        guard=True;scale=[1,0,0,0]
        for i in p:
            b=sum((z>>j&1)*(z>>k&1) for j,k in incident[i])%2
            if r[i]==4:
                guard=guard and b==1;scale=ring_mul(scale,[2,0,0,0])
            else:
                e+=1 if (r[i]+4*b)%8==2 else 7
                scale=ring_mul(scale,[0,1,0,-1])
        want=ring_mul(root(e),scale) if guard else [0]*4
        actual=[0]*4
        for a in range(1<<len(p)):
            v=z|sum((1<<i) for j,i in enumerate(p) if a>>j&1)
            exp=sum(r[i] for i in range(n) if v>>i&1)+4*sum(all(v>>i&1 for i in edge) for edge in edges)
            actual=[s+t for s,t in zip(actual,root(exp))]
        assert actual==want
        admitted+=int(guard);rejected+=int(not guard)
    assert admitted and rejected
    return dict(samples=256,admitted=admitted,rejected=rejected,original_terms=256*(1<<len(p)))


def count_reduced(n,edges,mode,alternative=False):
    assert n in (14,18,24,32) and mode in (0,1)
    start=time.monotonic_ns()
    r=[1+3*i%7 for i in range(n)]
    m=[2 if mode and i%3==0 else 1 for i in range(n)]
    p=pick_pivots(n,edges,mode,alternative);ps=set(p)
    assert all(m[i]==1 and r[i] in (2,4,6) for i in p)
    assert all(len(ps.intersection(e))<=1 for e in edges)
    rest=[i for i in range(n) if i not in ps]
    no=[e for e in edges if not ps.intersection(e)]
    incident={i:[tuple(j for j in e if j!=i) for e in edges if i in e] for i in p}
    chunk=23 if alternative else 24
    k=min(chunk,len(rest));free=rest[:k];fixed=rest[k:]
    assert len(rest)<=28 and 1<<len(fixed)<=32
    N=1<<k;mask=(1<<N)-1;planes={}
    for j,i in enumerate(free):
        if j<3:v=int.from_bytes(bytes(([0xaa,0xcc,0xf0][j],))*(N//8),"little")
        else:
            q=1<<(j-3)
            v=int.from_bytes((b"\x00"*q+b"\xff"*q)*(N//(16*q)),"little")
        planes[i]=v
    classes=[mask]
    for i in free:
        if m[i]==2:
            z=planes[i];new=[0]*(len(classes)+1)
            for j,a in enumerate(classes):
                new[j]|=a&(mask^z);new[j+1]|=a&z
            classes=new
    assert sum(c.bit_count() for c in classes)==N
    bins=[0]*8;support=0;weighted_support=0
    prep=time.monotonic_ns()-start
    def add(d,b):
        c=0
        for j in range(3):
            x=d[j]^b[j];carry=(d[j]&b[j])|(x&c);d[j]=x^c;c=carry
    t=time.monotonic_ns()
    for a in range(1<<len(fixed)):
        z=dict(planes);w=1
        for j,i in enumerate(fixed):
            b=a>>j&1;z[i]=mask if b else 0
            if b:w*=m[i]
        d=[0]*3;guard=mask
        for i in rest:add(d,[z[i] if r[i]>>j&1 else 0 for j in range(3)])
        for i,j,l in no:d[2]^=z[i]&z[j]&z[l]
        for i in p:
            b=0
            for j,l in incident[i]:b^=z[j]&z[l]
            if r[i]==4:guard&=b
            else:
                neg=b if r[i]==2 else mask^b
                add(d,[mask,neg,neg])
        support+=guard.bit_count()
        weighted_support+=w*sum((guard&c).bit_count()*(1<<j) for j,c in enumerate(classes))
        for e in range(8):
            a=guard
            for j,v in enumerate(d):a&=v if e>>j&1 else mask^v
            bins[e]+=w*sum((a&c).bit_count()*(1<<j) for j,c in enumerate(classes))
    count_ns=time.monotonic_ns()-t
    assert sum(bins)==weighted_support and support<=1<<len(rest)
    assert mode or weighted_support==support
    omega=sum(r[i]!=4 for i in p);g=len(p)-omega
    aligned=[(bins[i]-bins[i+4])*(1<<g) for i in range(4)]
    for _ in range(omega):aligned=ring_mul(aligned,[0,1,0,-1])
    t=time.monotonic_ns()
    checks=local_check(n,edges,r,m,p,rest,incident,no)
    return dict(n=n,mode="magnitude" if mode else "phase",alternative=alternative,
                pivots=p,remaining=len(rest),chunks=1<<len(fixed),chunk_bits=k,
                omega=omega,guards=g,support=support,weighted_support=weighted_support,
                residual_digits=bins,coeff=aligned,prep_ns=prep,count_ns=count_ns,
                local_check_ns=time.monotonic_ns()-t,**checks)


def run_cubic_rr(edges_fn):
    known={
        (14,0):[-64,-48,0,48],(14,1):[-136,-808,8,136],
        (18,0):[0,160,64,-224],(18,1):[-656,1424,-432,-2656],
        (24,0):[-2432,-896,2688,2432],(24,1):[-84352,45792,103648,83392],
        (32,0):[-13312,-2560,-22528,20992],(32,1):[918208,-4644672,-3220416,7258048],
    }
    rows=[]
    for n in (14,18,24,32):
        edges=edges_fn(n)
        for mode in (0,1):
            row=count_reduced(n,edges,mode)
            assert row["coeff"]==known[n,mode]
            rows.append(row)
            print("HOARE_CUBIC_RR "+json.dumps(row),flush=True)
            if n==32:
                alt=count_reduced(n,edges,mode,True)
                assert alt["pivots"]!=row["pivots"] and alt["coeff"]==row["coeff"]
                rows.append(alt)
                print("HOARE_CUBIC_RR "+json.dumps(alt),flush=True)
    print("HOARE_CUBIC_RR_SUMMARY "+json.dumps(dict(routes=len(rows),original_oracle_pairs=6,
          distinct_pivot_pairs=2,local_checks=sum(x["samples"] for x in rows),
          original_terms=sum(x["original_terms"] for x in rows))),flush=True)

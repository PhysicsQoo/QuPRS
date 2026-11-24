"""Development-only Pauli sector transport for H^n M H^n.

M is an affine monomial Clifford+T circuit. Replay signed translation
of its Z8 phase, not a sampled phase or WMC query. No production or
source-parser certificate; UNKNOWN outside the admitted fragment.
"""
import csv
import hashlib
import json
import random
import time


def parity(x):
    return x.bit_count() & 1


def add(poly,m,k):
    k=(poly.get(m,0)+k)%8
    if k:poly[m]=k
    else:poly.pop(m,None)


def add_even_affine(poly,m,c,k):
    # k is even. XOR's integer multilinear expansion modulo 8
    # then needs only degree <=2: higher coefficients are multiples of 8.
    assert k%2==0
    if c:
        add(poly,0,k)
        k=-k
    bits=[1<<i for i in range(m.bit_length()) if m>>i&1]
    for i,b in enumerate(bits):
        add(poly,b,k)
        for a in bits[:i]:add(poly,a|b,-2*k)


def affine_pred(f,n):
    mask=0;c=0
    if len(set(f))!=len(f):raise ValueError("noncanonical predicate")
    for m in f:
        if m<0 or m>=1<<n or m.bit_count()>1:
            raise ValueError("nonaffine predicate")
        if m==0:c=1
        else:mask|=m
    return mask,1^c  # predicate is asserted true


def entailed(pre,n,s):
    """GF(2) elimination with explicit original-row combination."""
    rows={};original=[affine_pred(f,n) for f in pre]
    for i,(m,b) in enumerate(original):
        comb=1<<i
        while m:
            p=m.bit_length()-1
            if p not in rows:
                rows[p]=(m,b,comb);break
            v,r,j=rows[p];m^=v;b^=r;comb^=j
        if not m and b:return None  # conservative: empty pre is out of scope
    m=s;b=0;comb=0
    while m:
        p=m.bit_length()-1
        if p not in rows:return None
        v,r,j=rows[p];m^=v;b^=r;comb^=j
    witness=0
    for p,(m,r,_) in sorted(rows.items()):
        if parity(m&witness)!=r:witness|=1<<p
    assert all(parity(m&witness)==r for m,r in original)
    mm=bb=0
    for i,(m,r) in enumerate(original):
        if comb>>i&1:mm^=m;bb^=r
    assert (mm,bb)==(s,b) and parity(s&witness)==b
    return b,comb,witness


def derivative(n,middle,t):
    """Find s=A^{-1}t; replay p(x xor s)-p(x) mod 8."""
    s=t
    for op,*qs in reversed(middle):
        if op=="cx":
            a,b=qs;s^=((s>>a)&1)<<b
    masks=[1<<i for i in range(n)];const=[0]*n;delta=s;poly={}
    for op,*qs in middle:
        a=qs[0];da=(delta>>a)&1
        if op=="x":
            const[a]^=1
        elif op=="cx":
            b=qs[1];masks[b]^=masks[a];const[b]^=const[a]
            delta^=da<<b
        elif op in ("z","s","t"):
            k={"z":4,"s":2,"t":1}[op]
            if da:
                add(poly,0,k)
                add_even_affine(poly,masks[a],const[a],-2*k)
        elif op=="cz":
            b=qs[1];db=(delta>>b)&1
            # 4 times product difference, so use GF(2) expansion.
            if da:add_even_affine(poly,masks[b],const[b],4)
            if db:add_even_affine(poly,masks[a],const[a],4)
            add(poly,0,4*da*db)
        else:raise ValueError("unsupported gate")
    assert delta==t
    return s,poly


def split(n,gates):
    if not 1<=n<=16 or not 2*n<=len(gates)<=512:
        return None
    arity={"h":1,"x":1,"z":1,"s":1,"t":1,"cx":2,"cz":2}
    for op,*qs in gates:
        if op not in arity or len(qs)!=arity[op] or len(set(qs))!=len(qs) or any(q<0 or q>=n for q in qs):
            return None
    hset=set(range(n))
    for layer in (gates[:n],gates[-n:]):
        if any(g[0]!="h" for g in layer) or {g[1] for g in layer}!=hset:return None
    middle=gates[n:-n]
    if any(g[0]=="h" for g in middle):return None
    return middle


def decide(n,gates,pre,post):
    start=time.monotonic()
    def result(status,verdict="UNKNOWN",**data):
        return dict(status=status,verdict=verdict,elapsed_s=time.monotonic()-start,
                    wmc_queries=0,**data)
    middle=split(n,gates)
    if middle is None or len(post)!=1:return result("UNSUPPORTED_SCOPE")
    try:
        t,q=affine_pred(post[0],n)
        if not t:return result("UNSUPPORTED_CONSTANT_POST")
        s,poly=derivative(n,middle,t)
        if any(m for m in poly):return result("NONCONSTANT_DERIVATIVE",input_mask=s,output_mask=t,
                                            derivative_terms=len(poly))
        phase=poly.get(0,0)
        if phase not in (0,4):raise ValueError("translation involution violated")
        p=entailed(pre,n,s)
    except ValueError:
        return result("UNSUPPORTED_OR_INVALID")
    if p is None:return result("PRE_NOT_FIXED",input_mask=s,output_mask=t)
    e,comb,w=p;b=phase//4
    data=dict(input_mask=s,output_mask=t,phase_delta=phase,pre_sector=e,post_sector=q,
              pre_row_combination=comb,transported_sector=e^b,derivative_terms=len(poly))
    # M X^s=(-1)^b X^t M; conjugation by H^n gives U Z^s=(-1)^b Z^t U.
    # Every legal input lands in the transported sector. Wrong sector:
    # all its norm violates Q; a legal computational input is a witness.
    if e^b==q:return result("EXACT_SECTOR_TRANSPORT","PROVED",**data)
    return result("EXACT_SECTOR_TRANSPORT","REFUTED",witness_input=w,**data)


def middle_eval(gates,x):
    """Independent basis simulation: no affine polynomial or derivative."""
    phase=0
    for op,*qs in gates:
        a=qs[0];v=(x>>a)&1
        if op=="x":x^=1<<a
        elif op=="cx":x^=v<<qs[1]
        elif op=="cz":phase+=4*v*((x>>qs[1])&1)
        else:phase+={"z":4,"s":2,"t":1}[op]*v
    return x,phase%8


def oracle_bad(n,middle,x,t,q):
    # Unnormalized amplitude of H M H, exact Z[omega] basis.
    for z in range(1<<n):
        if parity(z&t)==q:continue
        a=[0]*4
        for y in range(1<<n):
            out,p=middle_eval(middle,y)
            k=(p+4*(parity(x&y)^parity(z&out)))%8
            a[k%4]+=1 if k<4 else -1
        if any(a):return True
    return False


def predicate(m,b):
    return tuple(([0] if b==0 else [])+[1<<i for i in range(m.bit_length()) if m>>i&1])


def contract():
    rng=random.Random(297021);derivative_checks=0;terminal_checks=0;unknown_checks=0;positive=negative=0
    for k in range(96):
        n=2+k%3
        middle=[]
        # Half the random circuits use only affine permutations and Z,
        # so there are guaranteed exact positives/negatives.
        for _ in range(1+k%9):
            op=rng.choice(("x","cx","z") if k%2==0 else ("x","cx","z","s","t","cz"))
            qs=rng.sample(range(n),2 if op in ("cx","cz") else 1)
            middle.append((op,*qs))
        layer=[("h",i) for i in range(n)]
        gates=layer+middle+layer
        for t in range(1,1<<n):
            s,poly=derivative(n,middle,t)
            for x in range(1<<n):
                u,a=middle_eval(middle,x);v,b=middle_eval(middle,x^s)
                assert u^v==t
                expected=sum(c for m,c in poly.items() if x&m==m)%8
                assert expected==(b-a)%8
                derivative_checks+=1
            e=rng.randrange(2)
            for q in (0,1):
                pre=[predicate(s,e)];post=[predicate(t,q)]
                r=decide(n,gates,pre,post)
                if r["verdict"]=="UNKNOWN":
                    unknown_checks+=1;continue
                for x in range(1<<n):
                    if parity(x&s)==e:
                        assert oracle_bad(n,middle,x,t,q)==(r["verdict"]=="REFUTED")
                        terminal_checks+=1
                positive+=r["verdict"]=="PROVED";negative+=r["verdict"]=="REFUTED"
    # Scope / failed premise controls: failure must not become REFUTED.
    assert decide(1,[("h",0),("t",0),("h",0)],[(0,1)],[(1,)])["status"]=="NONCONSTANT_DERIVATIVE"
    assert decide(1,[("h",0),("h",0)],[],[(1,)])["status"]=="PRE_NOT_FIXED"
    assert decide(1,[("h",0),("h",0),("h",0)],[(0,1)],[(1,)])["verdict"]=="UNKNOWN"
    assert decide(1,[("h",0),("cx",0,0),("h",0)],[(0,1)],[(1,)])["verdict"]=="UNKNOWN"
    assert positive and negative and unknown_checks
    print("HOARE_SECTOR_TRANSPORT_CONTRACT "+json.dumps(dict(derivative_checks=derivative_checks,
          terminal_input_checks=terminal_checks,proved=positive,refuted=negative,
          unknown=unknown_checks,negative_controls=4)),flush=True)


def run_fourier(directory):
    from hoare_quokka_compare import load_case
    contract()
    fields="case circuit n h gates support pre rank expected_mass admission".split()
    with (directory/"heldout.tsv").open() as f:
        cases=list(csv.DictReader(f,fieldnames=fields,delimiter="\t"))
    assert len(cases)==20
    rows=[]
    for c in cases:
        name=c["case"];path=directory/f"quokka-{name}.tsv"
        n,gates,pre,post=load_case(path)
        r=decide(n,gates,pre,post)
        target="REFUTED" if int(c["expected_mass"]) else "PROVED"
        if c["admission"]=="NATIVE_EXPORT_ATTEMPTED":
            assert r["verdict"]==target,(name,r,target)
        else:
            assert r["verdict"]=="UNKNOWN",(name,r)
        if r["verdict"]=="REFUTED":
            x=r["witness_input"]
            assert all(sum(x&m==m for m in f)%2 for f in pre)
        r.update(case=name,expected_verdict=target,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                 development_cohort=True,prior_heldout_reused=True)
        rows.append(r)
        print("HOARE_SECTOR_TRANSPORT "+json.dumps(r),flush=True)
    assert sum(r["verdict"]=="PROVED" for r in rows)==6
    assert sum(r["verdict"]=="REFUTED" for r in rows)==6
    print("HOARE_SECTOR_TRANSPORT_SUMMARY "+json.dumps(dict(cases=20,proved=6,refuted=6,unsupported=8,
          wmc_queries=0,source_parser_certified=False,production_rule=False,development_cohort=True)),flush=True)

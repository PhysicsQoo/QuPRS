"""Independent bounded source tensor trace; research oracle, not QuPRS RR.

Contract literal QASM gates as complex Arb balls. The shared input indices
and output equalities implement Tr(V^dagger U). No PathSum, CNF, solver,
SVD truncation, or independent phase alignment is used.
"""
import json
import hashlib
from fractions import Fraction
from pathlib import Path
from flint import acb, arb, fmpq, ctx
from conditional_rr_source_ball import (
    ROOT, load, prepared, angle, dense_overlap, validate_gate_conventions, EPS,
)

MAX_WIDTH = 8
MAX_STEPS = 3000
MAX_GATES = 1000

def tensor_trace(a, b, n):
    if len(a)+len(b)>MAX_GATES or n>32:
        raise ValueError("source oracle gate/wire cap")
    factors = []
    next_id = n
    def fresh():
        nonlocal next_id
        v = next_id
        next_id += 1
        return v
    def add(v, fn):
        if len(v)!=len(set(v)) or len(v)>MAX_WIDTH:
            raise ValueError("invalid factor width/domain")
        factors.append((tuple(v), [fn(i) for i in range(1<<len(v))]))
    # Include every input, including completely untouched wires.
    for i in range(n):
        add((i,), lambda _: acb(1))
    def circuit(ops, conjugate):
        wires = list(range(n))
        for name, q, arg in ops:
            old = wires[q]
            if name == "cx":
                target = wires[arg]
                wires[arg] = fresh()
                add((old,target,wires[arg]),
                    lambda i: acb(int(((i>>2)&1)==(((i>>1)&1)^(i&1)))))
            else:
                wires[q] = fresh()
                # Matrix entries are row-major [out,in].
                add((old,wires[q]), lambda i: arg[i].conjugate() if conjugate else arg[i])
        return wires
    x,y = circuit(a,False),circuit(b,True)
    for i,j in zip(x,y):
        if i!=j:
            add((i,j),lambda k: acb(int(k in (0,3))))
    peak,steps = 0,0
    while True:
        adj = {}
        for v,_ in factors:
            for i in v:
                adj.setdefault(i,set()).update(v)
        if not adj:
            break
        p = min(adj,key=lambda i:(len(adj[i]),i))
        vs = tuple(sorted(adj[p]-{p}))
        peak=max(peak,len(vs)+1)
        steps+=1
        if peak>MAX_WIDTH or steps>MAX_STEPS:
            raise ValueError("source oracle contraction cap")
        chosen=[f for f in factors if p in f[0]]
        factors[:]=[f for f in factors if p not in f[0]]
        order=vs+(p,)
        maps=[tuple(order.index(i) for i in v) for v,_ in chosen]
        def marginal(k):
            total=acb(0)
            for bit in (0,1):
                j=k|(bit<<len(vs))
                product=acb(1)
                for (_,values),mapping in zip(chosen,maps):
                    index=sum(((j>>s)&1)<<t for t,s in enumerate(mapping))
                    product*=values[index]
                total+=product
            return total
        add(vs,marginal)
    z=acb(1)
    for v,values in factors:
        assert not v and len(values)==1
        z*=values[0]
    return z/(1<<n),dict(peak_width=peak,eliminations=steps)

def controls():
    validate_gate_conventions()
    # Non-commuting gates, asymmetric CX orientation, complex trace,
    # untouched wires, reversed overlap and exact global phase.
    a=prepared([("ry",0,angle("0.41")),("cx",0,1),
                ("rx",1,angle("-pi/3")),("rz",0,angle("0.123"))])
    b=prepared([("rz",1,angle("pi/7")),("cx",1,0),
                ("ry",0,angle("-0.76"))])
    for u,v,n in ((a,b,3),(b,a,3),(a,a,3),([],[],3),
                  (prepared([("rx",0,angle("2*pi"))]),[],2)):
        z,_=tensor_trace(u,v,n)
        d=sum((dense_overlap(u,v,k,n) for k in range(1<<n)),acb(0))/(1<<n)
        assert (z-d).contains(0), (z,d)
    print("CRR_TENSOR_CONTROLS_PASS dense_trace=5",flush=True)

def rational(s):
    q=Fraction(s)
    return arb(fmpq(q.numerator,q.denominator))

def main():
    controls()
    receipt=json.loads((Path(__file__).parent/"fixtures/conditional_rr_wstate16_45954275039.json").read_text())
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    case=next(c for c in manifest["cohorts"]["table2_mqt"]["cases"] if c["id"]=="wstate_16")
    n=case["qubits"]
    assert n==16 and receipt["head"]=="04aa6cb255caa9fcb273f3022952b1ff66f7bcb9"
    assert receipt["run_id"]==45954275039 and receipt["job_id"]==140357020512
    assert len(receipt["rows"])==2 and {r["variant"] for r in receipt["rows"]}=={"positive","random_rotation"}
    a,ha=load(case["source"],n)
    for row in receipt["rows"]:
        variant=row["variant"]
        assert row["case"]=="wstate_16" and row["arm"]=="conditional" and row["status"]=="complete"
        target=case["transpiled"] if variant=="positive" else dict(
            path="benchmarks/MQTBench/Random_Rotation/"+Path(case["source"]["path"]).name,
            git_blob_sha1="b3b203ece0681b2d5d0ce563e8b82c7fb1854192")
        b,hb=load(target,n)
        for entry,h in ((case["source"],ha),(target,hb)):
            assert "CRR_GENERIC_SOURCE wstate_16 "+variant+" "+entry["path"]+" "+h in receipt["source_lines"]
        z,stats=tensor_trace(a,b,n)
        threshold=(1-EPS*EPS).sqrt()
        verdict="Equivalent" if abs(z).lower()>threshold else "NotEquivalent" if abs(z).upper()<threshold else "INCONCLUSIVE"
        k=int(row["twice"])
        scale=(arb(2)**(k//2))*(arb(2).sqrt() if k%2 else 1)
        observed=acb(rational(row["real"]),rational(row["imag"]))/scale
        delta=abs(z-observed).upper()
        matched=bool(delta<arb("1e-50") and verdict==row["verdict"])
        print("CRR_WSTATE16_SOURCE_PARITY "+json.dumps(dict(
            variant=variant,source_sha256=ha,target_sha256=hb,
            precision_bits=ctx.prec,reference_head=receipt["head"],
            reference_run=receipt["run_id"],reference_job=receipt["job_id"],
            source_verdict=verdict,matched=matched,normalized_trace=str(z),
            count_delta_upper=str(delta),**stats)),flush=True)
        assert matched, "independent source or count mismatch"
    print("CRR_WSTATE16_SOURCE_CLOSEOUT_PASS count=2",flush=True)

if __name__=="__main__":
    main()

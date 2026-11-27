#!/usr/bin/env python3
"""E1e: actual MPFR-weighted sparse radian-parity CNF; zero solver calls.

Preserve turn monomials, original precision budget, primary domain, and trace.
No production changes. Non-beneficiary encodings are evidence, not admitted.
"""
import ast
import itertools
import json
import sys
import time
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

from eq_dag_e1d_parity import HEAD, TREE, read_snapshot, invert, replay, cost, controls
from eq_dag_e1b_encode import Encoder, weight_fn, positive_weights, evaluate
from eq_dag_d3_ab import sha

E1B = "2addb665bd8015791c5ee7527a8ce0de5bf8e3a1"
E1B_TREE = "f3c63a58c6a7ab651e0117e2a847ffa52b1c0f47"

def build(domain, n, p, outputs, parity, weight, bits):
    rad = {m:c[1] for m,c in p.items() if c[1]}
    assert replay(parity) == rad
    e = Encoder(domain, weight, bits)
    turns = {m:c[0] for m,c in p.items() if c[0]}
    singleton = {m for m in parity if len(m)<=1}
    for m in sorted(set(turns)|singleton):
        c = (turns.get(m,F(0)), parity.get(m,F(0)) if len(m)<=1 else F(0))
        assert c != (F(0),F(0))
        e.mono(m,c)
    for m,c in sorted(parity.items()):
        if len(m)<2:
            continue
        z = e.ids[m[0]]
        for v in m[1:]:
            z = e.xor(z,e.ids[v],True)
        # Keep the neutral shared parity root separate from its weighted alias.
        e.gate("and",[z],(F(0),c))
    phase_end = len(e.c)
    e.outputs(n,outputs)
    return e,phase_end

def audit(e, domain, outputs, n):
    # Independently consume every serialized clause using truth-table
    # forbidden assignments for XOR and direct full AND/false definitions.
    clauses = []
    for z,(kind,ops) in e.defs.items():
        assert z > len(domain) and all(0 < abs(x) < z for x in ops)
        if kind=="xor":
            a,b=ops
            for x,y,v in itertools.product((0,1),repeat=3):
                if v != (x^y):
                    clauses.append(tuple(sorted((-a if x else a,-b if y else b,-z if v else z))))
        elif kind=="and":
            clauses.extend(tuple(sorted((-z,x))) for x in ops)
            clauses.append(tuple(sorted((z,*(-x for x in ops)))))
        else:
            assert kind=="false" and not ops
            clauses.append((-z,))
    # Trace outputs use the same production-proven E1b output encoder;
    # account for the exact remaining two clauses per input independently.
    text = e.render()
    raw = [tuple(sorted(map(int,l.split()[:-1]))) for l in text.splitlines()
           if l and l[0] not in "pc"]
    assert len(raw)==len(clauses)+2*n
    # Equality clauses are interleaved with subsequent output gates.
    leftover=Counter(raw)-Counter(clauses)
    assert not (Counter(clauses)-Counter(raw))
    assert sum(leftover.values())==2*n
    # The trace gates are allocated last. Reconstruct their roots from
    # source output ANF, independently of the trace equality clauses.
    trace_v=sum(1 if not f else sum(len(m)!=1 for m in f)+len(f)-1
                for f in outputs.values())
    cursor=e.n-trace_v+1
    expected=Counter()
    for i in range(n):
        f=sorted(outputs[i])
        roots=[]
        for m in f:
            ops=tuple(e.ids[v] for v in m)
            if len(ops)==1:
                roots.append(ops[0])
            else:
                assert e.defs[cursor]==("and",ops)
                roots.append(cursor);cursor+=1
        if not roots:
            assert e.defs[cursor]==("false",())
            z=cursor;cursor+=1
        else:
            z=roots[0]
            for y in roots[1:]:
                assert e.defs[cursor]==("xor",tuple(sorted((z,y))))
                z=cursor;cursor+=1
        a=e.ids[i]
        expected.update([tuple(sorted((-a,z))),tuple(sorted((a,-z)))])
    assert cursor==e.n+1 and leftover==expected
    weights = [l.split() for l in text.splitlines() if l.startswith("c p weight ")]
    assert len(weights)==2*len(e.w)
    ids = {int(w[3]):tuple(map(F,w[4:6])) for w in weights}
    assert len(ids)==len(weights)
    assert set(ids)=={i for z in e.w for i in (z,-z)}
    for z,(a,b) in e.w.items():
        assert ids[z]==(F(a),F(b)) and ids[-z]==(F(1),F(0))
    assert set(e.defs)==set(range(len(domain)+1,e.n+1))
    return text

def fixture(weight):
    controls()
    # Small exact Gaussian control with shared parity and free primary.
    # Radian component is validated separately by exact inversion/replay;
    # nonzero radian MPFR output is not claimed to be exactly Gaussian.
    parity={(0,1):F(1,7),(1,2):F(-2,9)}
    rad=replay(parity)
    p={m:(F(0),c) for m,c in rad.items()}
    p[(0,)]=(F(1,4),rad.get((0,),F(0)))
    domain=list(range(4))
    f={0:[(0,),(2,)]}
    e,_=build(domain,1,p,f,parity,weight,96)
    audit(e,domain,f,1)
    for bits in itertools.product((0,1),repeat=4):
        source=sum(c[1]*int(all(bits[i] for i in m)) for m,c in p.items())
        target=sum(c*(sum(bits[i] for i in m)%2) for m,c in parity.items())
        assert source==target
        sat,_=evaluate(e,bits)
        assert sat==(bits[0]==(bits[0]^bits[2]))
    # Exact Gaussian finite-weight and trace/free-primary model parity.
    p={(0,):(F(1,4),F(0)),(0,1):(F(1,2),F(0))}
    e,_=build(domain,1,p,f,{},weight,96)
    audit(e,domain,f,1)
    for bits in itertools.product((0,1),repeat=4):
        sat,val=evaluate(e,bits)
        exponent=(bits[0]+2*bits[0]*bits[1])%4
        assert sat==(bits[0]==(bits[0]^bits[2]))
        assert val==([(F(1),F(0)),(F(0),F(1)),(F(-1),F(0)),(F(0),F(-1))][exponent] if sat else None)
    try:
        build(domain,1,{m:(F(0),c) for m,c in rad.items()},f,{**parity,(0,1):F(1,7)+F(1,10**40)},weight,96)
    except AssertionError:
        pass
    else:
        raise AssertionError("mutated parity accepted")

def main():
    src,e1b,lib,out=map(Path,sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    assert (src/"head.txt").read_text().strip()==HEAD and (src/"tree.txt").read_text().strip()==TREE
    assert (e1b/"head.txt").read_text().strip()==E1B and (e1b/"tree.txt").read_text().strip()==E1B_TREE
    weight=weight_fn(lib); fixture(weight)
    receipts=json.loads((e1b/"receipts.json").read_text())
    assert receipts["summary"]["arms"]==receipts["summary"]["exact_phase_replay"]==12
    prior={r["case"]:r for r in receipts["rows"]}
    rows=[]
    for r in map(json.loads,(src/"rows.jsonl").read_text().splitlines()):
        if not (r["cnf"] and r["residual_sha256"]): continue
        case=r["case"]; a=prior[case]; arm=src/(case+"-hybrid")
        snap=arm/"residual.tsv"; flat=arm/"actual.cnf"
        assert sha(snap)==r["residual_sha256"]==a["source_residual_sha256"]
        assert sha(flat)==r["cnf"]["sha256"]==a["original_cnf_sha256"]
        cf=e1b/(case+"-flat.cnf"); ef=e1b/(case+"-factored.cnf")
        assert sha(cf)==a["flat_sha256"] and sha(ef)==a["factored_sha256"]
        assert positive_weights(cf.read_text())==positive_weights(flat.read_text())
        n,h,p,f=read_snapshot(snap.read_bytes())
        domain=ast.literal_eval(next(l.split("\t")[1] for l in snap.read_text().splitlines() if l.startswith("vars\t")))
        assert len(domain)==n+h and domain==sorted(set(domain))
        started=time.perf_counter()
        parity,work=invert({m:c[1] for m,c in p.items() if c[1]})
        row=dict(case=case,residual_sha256=sha(snap),original_cnf_sha256=sha(flat),e1b_sha256=sha(ef),weight_bits=a["weight_bits"],subset_work=work,status="WORK_CAP" if parity is None else "OK")
        if parity is not None:
            assert replay(parity)=={m:c[1] for m,c in p.items() if c[1]}
            model=cost(n,h,p,f,parity)
            assert (model["flat_variables"],model["flat_clauses"])==(a["flat_vars"],a["flat_clauses"])==(r["cnf"]["variables"],r["cnf"]["clauses"])
            e,phase_end=build(domain,n,p,f,parity,weight,a["weight_bits"])
            text=audit(e,domain,f,n)
            assert (e.n,len(e.c),len(e.w),len(e.xors))==(model["variables"],model["clauses"],model["factors"],model["shared_xor_nodes"])
            q=out/(case+"-parity.cnf");q.write_text(text)
            row.update(model,parity_terms=len(parity),phase_clauses=phase_end,cnf_sha256=sha(q),exact_radian_replay=True,encoding_wall_s=time.perf_counter()-started,e1b_vars=a["factored_vars"],e1b_clauses=a["factored_clauses"],e1b_weighted=a["factored_weighted"],non_growth=e.n<=a["flat_vars"] and len(e.c)<=a["flat_clauses"])
        rows.append(row)
        print("E1E_ARM",json.dumps(row),flush=True)
    assert len(rows)==12 and len({r["case"] for r in rows})==12
    assert all(r["status"]=="OK" for r in rows)
    summary=dict(arms=len(rows),actual_cnf=len(rows),non_growth=sum(r["non_growth"] for r in rows),solver_calls=0,scope="actual serialized MPFR weighted parity CNF; not finite-weight equivalence, solver or E2E acceptance")
    (out/"receipts.json").write_text(json.dumps(dict(summary=summary,rows=rows),indent=2)+"\n")
    print("E1E_SUMMARY",json.dumps(summary),flush=True)
if __name__=="__main__":
    main()

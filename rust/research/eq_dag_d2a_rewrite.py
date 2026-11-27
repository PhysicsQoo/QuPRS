#!/usr/bin/env python3
"""D2a: exact DIMACS-domain subset-root rewrite and independent expansion replay.
Only original phase AND biconditionals change. All original weights and
variable IDs remain byte-identical; output/trace/free-variable clauses remain.
Experimental artifact transformation, not production encoder or solver test.
"""
import itertools
import json
from collections import Counter
from pathlib import Path
import sys
from eq_dag_d1e_screen import plan, controls, sha

BASE="8811544a462338569bc5a375e3df41fdd18ea3b8"
TREE="b7ebfdcf3cfdac115bf971fddc92306bc66adde8"

def parse(text):
    lines=text.splitlines()
    h=lines[0].split()
    assert h[:2]==["p","cnf"] and len(h)==4
    nv,nc=map(int,h[2:])
    comments=[]
    weights={}
    i=1
    while i<len(lines) and lines[i].startswith("c "):
        line=lines[i]
        comments.append(line)
        if line.startswith("c p weight "):
            a=line.split()
            assert len(a)==7 and a[-1]=="0"
            z=int(a[3])
            assert 0<abs(z)<=nv and z not in weights
            weights[z]=tuple(a[4:6])
        else:
            assert line=="c t wmc"
        i+=1
    assert all(-z in weights for z in weights)
    positive=sorted(z for z in weights if z>0)
    clauses=[]
    for line in lines[i:]:
        a=tuple(map(int,line.split()))
        assert a and a[-1]==0 and all(0<abs(v)<=nv for v in a[:-1])
        clauses.append(a[:-1])
    assert len(clauses)==nc
    return nv,comments,positive,clauses

def blocks(weighted,clauses):
    # Read exact phase-prefix format, rejecting unknown/ambiguous layout.
    definitions={}
    cursor=0
    for z in weighted:
        operands=[]
        while cursor<len(clauses):
            c=clauses[cursor]
            cursor+=1
            if len(c)==2 and c[0]==-z and c[1]>0:
                operands.append(c[1])
            else:
                # Native singleton z <-> x emits (-x,z), while the
                # general AND block emits (z,-x,...). Accept both orders
                # only for this exact singleton reverse implication.
                assert c==(z,*(-x for x in operands)) or (len(operands)==1 and c==(-operands[0],z)),(z,c,operands)
                break
        else:
            raise AssertionError("missing complete phase definition")
        assert z not in operands and len(operands)==len(set(operands))
        definitions[z]=tuple(operands)
    return definitions,clauses[cursor:]

def render(nv,comments,definitions,tail):
    nc=sum(len(x)+1 for x in definitions.values())+len(tail)
    lines=[f"p cnf {nv} {nc}",*comments]
    for z,ops in definitions.items():
        lines.extend(f"{-z} {x} 0" for x in ops)
        reverse=(-ops[0],z,0) if len(ops)==1 else (z,*(-x for x in ops),0)
        lines.append(" ".join(map(str,reverse)))
    lines.extend(" ".join(map(str,(*c,0))) for c in tail)
    return "\n".join(lines)+"\n"

def replay(flat,dag):
    # Independent verification: parse both actual serialized CNFs anew.
    n,w,ids,c=parse(flat)
    nd,wd,idd,cd=parse(dag)
    assert n==nd and w==wd and ids==idd
    original,tail=blocks(ids,c)
    candidate,taild=blocks(idd,cd)
    assert tail==taild
    weighted=set(ids)
    assert all(not (set(x)&weighted) for x in original.values())
    assert len({frozenset(x) for x in original.values()})==len(ids)
    expanded={}
    maxdepth={}
    for z in sorted(ids,key=lambda z:(len(original[z]),z)):
        values=set()
        depth=1
        for operand in candidate[z]:
            if operand in weighted:
                assert operand in expanded and len(original[operand])<len(original[z])
                values.update(expanded[operand])
                depth=max(depth,1+maxdepth[operand])
            else:
                values.add(operand)
        assert values==set(original[z]),(z,values,original[z])
        expanded[z]=values
        maxdepth[z]=depth
    # Full biconditionals + strict topological dependency give unique
    # extension, with each weighted variable unchanged for every assignment.
    return dict(phase_definitions=len(ids),variables=n,flat_clauses=len(c),dag_clauses=len(cd),flat_literals=sum(map(len,c)),dag_literals=sum(map(len,cd)),max_chain_depth=max(maxdepth.values(),default=0),weight_lines_identical=True,tail_identical=True)

def rewrite(flat):
    n,w,ids,c=parse(flat)
    old,tail=blocks(ids,c)
    weighted=set(ids)
    assert all(not (set(x)&weighted) for x in old.values())
    support={tuple(sorted(x)):z for z,x in old.items()}
    assert len(support)==len(ids)
    p=plan(support)
    assert p["status"]=="OK"
    choice={tuple(x["monomial"]):tuple(x["root"]) for x in p["choices"]}
    new={}
    for z,ops in old.items():
        root=choice.get(tuple(sorted(ops)))
        if root is None:
            new[z]=ops
        else:
            rset=set(root)
            new[z]=(support[root],*(x for x in ops if x not in rset))
    dag=render(n,w,new,tail)
    receipt=replay(flat,dag)
    assert receipt["flat_clauses"]-receipt["dag_clauses"]==p["clause_saving"]
    assert receipt["flat_literals"]-receipt["dag_literals"]==p["literal_saving"]
    return dag,receipt

def models(text):
    n,w,ids,clauses=parse(text)
    return {bits for bits in itertools.product((False,True),repeat=n)
            if all(any(bits[abs(v)-1]==(v>0) for v in c) for c in clauses)}

def tests():
    controls()
    # Source-faithful native singleton and constant blocks, plus full AND.
    single="p cnf 5 6\nc t wmc\nc p weight 3 0 1 0\nc p weight -3 1.0 0.0 0\nc p weight 4 -1 0 0\nc p weight -4 1.0 0.0 0\nc p weight 5 0.5 0.5 0\nc p weight -5 1.0 0.0 0\n-3 1 0\n-1 3 0\n4 0\n-5 1 0\n-5 2 0\n5 -1 -2 0\n"
    candidate,receipt=rewrite(single)
    assert candidate==single and models(single)==models(candidate)
    for malformed in (single.replace("-1 3 0","-2 3 0"),single.replace("-1 3 0","1 3 0")):
        try:
            rewrite(malformed)
        except AssertionError:
            pass
        else:
            raise AssertionError("invalid singleton implication accepted")
    # Nonreal, negative, arbitrary-decimal weights remain exact text.
    flat=render(7,["c t wmc","c p weight 5 0 1 0","c p weight -5 1.0 0.0 0","c p weight 6 -1 0 0","c p weight -6 1.0 0.0 0","c p weight 7 0.123456789 -0.987654321 0","c p weight -7 1.0 0.0 0"],{5:(1,2),6:(1,2,3),7:(1,2,3,4)},[(1,-4)])
    dag,receipt=rewrite(flat)
    assert receipt["flat_clauses"]-receipt["dag_clauses"]==3
    assert models(flat)==models(dag)
    # Tamper a full, well-formed definition: replay must reject.
    n,w,ids,c=parse(dag)
    defs,tail=blocks(ids,c)
    defs[7]=(5,4)
    try:
        replay(flat,render(n,w,defs,tail))
    except AssertionError:
        pass
    else:
        raise AssertionError("mutated definition accepted")
    # Weight mutation must reject even if Boolean models unchanged.
    try:
        replay(flat,dag.replace("0.123456789","0.123456788"))
    except AssertionError:
        pass
    else:
        raise AssertionError("mutated weight accepted")

def main():
    tests()
    src,out=map(Path,sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    assert (src/"head.txt").read_text().strip()==BASE
    assert (src/"tree.txt").read_text().strip()==TREE
    rows=[json.loads(x) for x in (src/"rows.jsonl").read_text().splitlines()]
    assert len(rows)==19
    reports=[]
    for r in rows:
        if not (r["cnf"] and r["residual_sha256"]):
            continue
        arm=src/(r["case"]+"-"+r["mode"])
        flatpath=arm/"actual.cnf"
        assert sha(flatpath)==r["cnf"]["sha256"]
        assert sha(arm/"residual.tsv")==r["residual_sha256"]
        dag,receipt=rewrite(flatpath.read_text())
        assert receipt["phase_definitions"]==int(r["metrics"]["phase_terms"])
        assert (receipt["variables"],receipt["flat_clauses"],receipt["flat_literals"])==(r["cnf"]["variables"],r["cnf"]["clauses"],r["cnf"]["literals"])
        target=out/(r["case"]+".cnf")
        target.write_text(dag)
        record=dict(case=r["case"],status=r["status"],residual_sha256=r["residual_sha256"],flat_sha256=r["cnf"]["sha256"],dag_sha256=sha(target),**receipt)
        reports.append(record)
        print("D2A_ARM",json.dumps(record),flush=True)
    assert len(reports)==12
    summary=dict(arms=len(reports),verified_model_preserving_rewrites=len(reports),solver_calls=0,production_changes=0)
    (out/"rewrite_receipts.json").write_text(json.dumps(dict(rows=reports,summary=summary),indent=2)+"\n")
    print("D2A_SUMMARY",json.dumps(summary),flush=True)
if __name__=="__main__":
    main()

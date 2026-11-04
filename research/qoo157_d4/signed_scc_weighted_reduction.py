"""P0 QOO-157: independent binary-SCC weighted-complex CNF reduction.

Research only. Exact rational-complex literal-weight multiplication.
Fail closed on unsupported WMC extensions. No solver code changes.
A variable equivalence identified by original binary clauses has a
one-to-one assignment extension; after signed substitution its two
literal weights must be multiplied into its representative.
"""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from itertools import product
from pathlib import Path
import argparse
import json

ONE = (Fraction(1), Fraction(0))
ZERO = (Fraction(0), Fraction(0))


def mul(a, b):
    return (a[0]*b[0]-a[1]*b[1], a[0]*b[1]+a[1]*b[0])


def add(a, b):
    return (a[0]+b[0], a[1]+b[1])


def fraction_decimal(x: Fraction) -> str:
    """Finite decimal without rounding; input decimal weights are exact rationals."""
    n, d = x.numerator, x.denominator
    p2 = p5 = 0
    while d % 2 == 0:
        d //= 2
        p2 += 1
    while d % 5 == 0:
        d //= 5
        p5 += 1
    if d != 1:
        raise ValueError("nonterminating rational cannot be emitted exactly")
    places = max(p2, p5)
    integer = abs(n)*2**(places-p2)*5**(places-p5)
    whole, frac = divmod(integer, 10**places)
    val = str(whole) + (("." + str(frac).zfill(places)) if places else "")
    if places:
        val = val.rstrip("0").rstrip(".")
    return ("-" if n < 0 else "") + val


def read_cnf(raw: bytes):
    nvars = expected = None
    clauses = []
    weights = {}
    if not raw:
        raise ValueError("empty input")
    for line in raw.decode("utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[:2] == ["p", "cnf"]:
            if len(parts) != 4 or nvars is not None:
                raise ValueError("bad DIMACS header")
            nvars, expected = int(parts[2]), int(parts[3])
        elif parts[:3] == ["c", "p", "weight"]:
            if len(parts) != 7 or parts[-1] != "0":
                raise ValueError("unsupported complex literal-weight syntax")
            lit = int(parts[3])
            if nvars is None or lit == 0 or abs(lit) > nvars or lit in weights:
                raise ValueError("invalid/duplicate complex weight")
            weights[lit] = (Fraction(Decimal(parts[4])),
                            Fraction(Decimal(parts[5])))
        elif parts == ["c", "t", "wmc"]:
            continue
        elif parts[0] == "c":
            raise ValueError("unknown WMC metadata cannot be silently dropped: "+line[:100])
        else:
            if nvars is None or parts[-1] != "0":
                raise ValueError("malformed DIMACS clause")
            clause = [int(s) for s in parts[:-1]]
            if any(v == 0 or abs(v) > nvars for v in clause):
                raise ValueError("clause literal out of range")
            clauses.append(tuple(clause))
    if nvars is None or nvars < 1 or expected != len(clauses):
        raise ValueError("CNF declared variable/clause mismatch")
    return nvars, clauses, weights


def components(nvars, clauses):
    n = 2*nvars
    graph, back = [[] for _ in range(n)], [[] for _ in range(n)]
    def node(lit):
        return 2*(abs(lit)-1)+(lit < 0)
    for clause in clauses:
        if len(clause) != 2:
            continue
        a,b = clause
        for x,y in ((-a,b),(-b,a)):
            u,v=node(x),node(y)
            graph[u].append(v);back[v].append(u)
    seen=set(); finish=[]
    for root in range(n):
        if root in seen: continue
        seen.add(root); stack=[(root,0)]
        while stack:
            u,j=stack[-1]
            if j==len(graph[u]):
                finish.append(u);stack.pop();continue
            stack[-1]=(u,j+1)
            v=graph[u][j]
            if v not in seen:
                seen.add(v);stack.append((v,0))
    comp=[-1]*n
    cid=0
    for root in reversed(finish):
        if comp[root]>=0:continue
        comp[root]=cid; todo=[root]
        while todo:
            u=todo.pop()
            for v in back[u]:
                if comp[v]<0:
                    comp[v]=cid;todo.append(v)
        cid+=1
    for v in range(1,nvars+1):
        if comp[node(v)]==comp[node(-v)]:
            raise ValueError("binary constraints have contradictory SCC")
    groups=defaultdict(list)
    for v in range(1,nvars+1):
        key=tuple(sorted((comp[node(v)],comp[node(-v)])))
        groups[key].append(v)
    return comp, sorted(groups.values(),key=lambda g:min(g))


def reduce(nvars, clauses, weights):
    comp, groups=components(nvars, clauses)
    def node(lit):
        return 2*(abs(lit)-1)+(lit < 0)
    remap={}
    represented={}
    for new_id,group in enumerate(groups,1):
        representative=min(group)
        for v in group:
            parity=1 if comp[node(v)]==comp[node(representative)] else -1
            if (parity==1 and comp[node(-v)]!=comp[node(-representative)]) or (
                parity==-1 and comp[node(-v)]!=comp[node(representative)]):
                raise ValueError("inconsistent SCC complement mapping")
            remap[v]=parity*new_id
        represented[new_id]=group
    updated=[]
    dropped_taut=0
    for clause in clauses:
        mapped=[(remap[abs(lit)] if lit>0 else -remap[abs(lit)])
                for lit in clause]
        uniq=set(mapped)
        if any(-lit in uniq for lit in uniq):
            dropped_taut+=1
            continue
        updated.append(tuple(sorted(uniq,key=lambda l:(abs(l),l<0))))
    new_weights={}
    weighted_groups=0
    for group_id,group in represented.items():
        if not any(v in weights or -v in weights for v in group):
            continue
        weighted_groups+=1
        for sign in (1,-1):
            prod=ONE
            for v in group:
                original_lit=sign*(v if remap[v]>0 else -v)
                prod=mul(prod,weights.get(original_lit,ONE))
            new_weights[sign*group_id]=prod
    return len(groups),updated,new_weights,{
        "merged_variables":nvars-len(groups),
        "removed_tautological_clauses":dropped_taut,
        "nontrivial_equivalence_groups":sum(len(g)>1 for g in groups),
        "original_weighted_variables":len(set(abs(x) for x in weights)),
        "reduced_weighted_variables":weighted_groups,
        "signed_source_mapping":{str(k):v for k,v in sorted(remap.items())},
        "equivalent_groups":[{"new_var":g,"source_vars":v}
                             for g,v in represented.items() if len(v)>1],
        "no_global_factor_required_for_bijective_binary_equivalence":True
    }


def write_cnf(nvars,clauses,weights):
    lines=[f"p cnf {nvars} {len(clauses)}","c t wmc"]
    for lit in sorted(weights,key=lambda v:(abs(v),v<0)):
        re,im=weights[lit]
        lines.append(f"c p weight {lit} {fraction_decimal(re)} {fraction_decimal(im)} 0")
    for clause in clauses:
        lines.append(" ".join(map(str,clause))+(" " if clause else "")+"0")
    return ("\n".join(lines)+"\n").encode()


def exhaustive_count(nvars,clauses,weights):
    if nvars>12:raise ValueError("small oracle only")
    result=ZERO
    for values in product((False,True),repeat=nvars):
        if not all(any((values[abs(l)-1] if l>0 else not values[abs(l)-1])
                        for l in clause) for clause in clauses):
            continue
        w=ONE
        for v,yes in enumerate(values,1):
            w=mul(w,weights.get(v if yes else -v,ONE))
        result=add(result,w)
    return result


def self_tests():
    # Equality, negated equality, complex cancellation, unit+free,
    # mixed signs, both weighted and unweighted source variables.
    fixtures=[
        (3,[(1,-2),(-1,2)],{1:(Fraction(2),Fraction(3)),
            -1:(Fraction(-1),Fraction(1)),2:(Fraction(1),Fraction(-2)),
            -2:(Fraction(3),Fraction(0))}),
        (3,[(1,2),(-1,-2)],{1:(Fraction(1),Fraction(2)),
            -1:(Fraction(-2),Fraction(3)),2:(Fraction(0),Fraction(4)),
            -2:(Fraction(5),Fraction(-1))}),
        (4,[(1,-2),(-1,2),(2,3),(-2,-3),(3,-4),(-3,4)],
         {1:(Fraction(2),Fraction(1)),2:(Fraction(-3),Fraction(2)),
          3:(Fraction(1),Fraction(-2)),4:(Fraction(0),Fraction(1))}),
        (3,[(1,),(-2,),(2,3),(-2,-3)],
         {1:(Fraction(1),Fraction(0)),-1:(Fraction(-1),Fraction(0)),
          2:(Fraction(0),Fraction(1)),3:(Fraction(1),Fraction(0))}),
        (3,[],{1:(Fraction(1),Fraction(0)),-1:(Fraction(-1),Fraction(0))}),
        (2,[(1,),(-1,)],{})
    ]
    for case,(n,c,w) in enumerate(fixtures):
        base=exhaustive_count(n,c,w)
        n2,c2,w2,manifest=reduce(n,c,w)
        raw=write_cnf(n2,c2,w2)
        assert read_cnf(raw)==(n2,c2,w2),f"roundtrip fixture {case}"
        reduced=exhaustive_count(n2,c2,w2)
        assert base==reduced,(case,base,reduced,manifest)
    assert fraction_decimal(Fraction(-13,1000))=="-0.013"
    try:
        read_cnf(b"p cnf 1 0\nc p show 1\n")
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported metadata must fail closed")
    return {"small_exact_oracle_fixtures":len(fixtures),"status":"EXACT_FRACTION_COMPLEX_ORACLE_PASS"}


def export(cnf_dir:Path,source_science:Path,target:Path,report:Path):
    source=json.loads(source_science.read_text())
    if source.get("complete") is not True:raise ValueError("archived science not complete")
    summary={"status":"INCOMPLETE","oracle":self_tests(),
             "original_science_artifact":13317939531,"source_cnf_sha_strict":True,
             "small_wmc_oracle_only_not_large_proof":True,"cases":{}}
    for case in ("grover4_eq","qaoa7_neq","qpeexact8_eq","qft16_eq"):
        data=(cnf_dir/(case+".cnf")).read_bytes()
        digest=sha256(data).hexdigest()
        if digest!=source["cases"][case]["same_cnf_sha256"]:
            raise ValueError("source provenance mismatch "+case)
        n,c,w=read_cnf(data)
        newn,newc,neww,meta=reduce(n,c,w)
        result=write_cnf(newn,newc,neww)
        nn,cc,ww=read_cnf(result)
        if (nn,cc,ww)!=(newn,newc,neww):
            raise ValueError("reduced CNF not roundtrip identical")
        dest=target/(case+".cnf")
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(result)
        summary["cases"][case]={
            "source_sha256":digest,"source_vars":n,"source_clauses":len(c),
            "reduced_sha256":sha256(result).hexdigest(),
            "reduced_vars":newn,"reduced_clauses":len(newc),
            "reduced_weight_entries":len(neww),**meta}
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(json.dumps(summary,indent=2)+"\n")
    summary["status"]="SOURCE_EXACT_REDUCTION_READY_FOR_SOLVER_COUNT_SCREEN"
    report.write_text(json.dumps(summary,indent=2)+"\n")
    return summary


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--cnf-dir",type=Path,required=True)
    p.add_argument("--source-science",type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    result=export(a.cnf_dir,a.source_science,a.out_dir,a.report)
    print(json.dumps({"status":result["status"],"oracles":result["oracle"],
        "merged":{k:v["merged_variables"] for k,v in result["cases"].items()}}))

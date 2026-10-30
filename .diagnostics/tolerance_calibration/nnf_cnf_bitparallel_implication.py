"""Non-enumerative d-DNNF -> original CNF entailment, all clauses at once.

For each original CNF clause C_j, constrain all literals in C_j
to FALSE. A bitset tracks, for every NNF subgraph, which such partial
assignments still admit a model. AND uses the separately checked
decomposability condition; OR uses existential branch union.
If the final bitset is zero, the independently interpreted d-DNNF
implies *every* clause of the original CNF. This is a one-direction
proof, NOT a full CNF <-> d-DNNF compilation certificate.
"""
from __future__ import annotations
from collections import defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import time

def clauses_from_cnf(path):
    clauses=[];n=expected=None
    for line in path.read_text().splitlines():
        a=line.split()
        if not a:continue
        if a[:2]==["p","cnf"]:
            n=int(a[2]);expected=int(a[3])
        elif a[0]!="c":
            assert a[-1]=="0"
            clauses.append(tuple(int(x) for x in a[:-1]))
    if n is None or len(clauses)!=expected:raise ValueError("CNF header mismatch")
    return n,clauses

def entailment(cnf,nnf):
    n,clauses=clauses_from_cnf(cnf)
    forbidden=defaultdict(int)
    for j,cl in enumerate(clauses):
        for lit in cl:forbidden[lit]|=1<<j
    full=(1<<len(clauses))-1
    def allowed(literal):
        return full ^ forbidden[literal]
    mapping=defaultdict(list)
    fixed=[]; free=[]
    support=[];feasible=[]
    n_and=n_or=0
    header=None
    start=time.monotonic()
    for line in nnf.read_text().splitlines():
        a=line.split()
        if not a or a[0]=="c":continue
        tag=a[0]
        if tag=="p":
            if a[1]!="vmap" or int(a[2])!=n:
                raise ValueError("source variable map mismatch")
        elif tag=="v":
            orig,sim=int(a[1]),int(a[2])
            if not 1<=orig<=n or sim==0:raise ValueError("invalid map")
            mapping[abs(sim)].append(orig*(1 if sim>0 else -1))
        elif tag=="a":fixed.extend(map(int,a[1:-1]))
        elif tag=="f":free.append(tuple(map(int,a[1:-1])))
        elif tag=="d":
            if len(a)>2:raise ValueError("unsupported deleted original variables")
        elif tag=="nnf":
            header=tuple(map(int,a[1:]))
        elif tag=="L":
            lit=int(a[1]);members=mapping.get(abs(lit))
            if not members:raise ValueError(("unmapped NNF leaf",lit))
            sign=1 if lit>0 else -1
            acc=full;supp=0
            for m in members:
                acc&=allowed(sign*m)
                supp|=1<<(abs(m)-1)
            feasible.append(acc);support.append(supp)
        elif tag=="A":
            children=tuple(map(int,a[2:]))
            if len(children)!=int(a[1]):raise ValueError("AND arity mismatch")
            acc=full;supp=0
            for i in children:
                if i>=len(feasible):raise ValueError("forward dependency")
                if supp&support[i]:
                    raise ValueError(("AND not decomposable",len(feasible),i))
                supp|=support[i]
                acc&=feasible[i]
            feasible.append(acc);support.append(supp);n_and+=1
        elif tag=="O":
            children=tuple(map(int,a[3:]))
            if len(children)!=int(a[2]):raise ValueError("OR arity mismatch")
            acc=supp=0
            for i in children:
                if i>=len(feasible):raise ValueError("forward dependency")
                acc|=feasible[i]
                supp|=support[i]
            feasible.append(acc);support.append(supp);n_or+=1
        else:raise ValueError(("unknown NNF format",tag))
    if header is None or header[0]!=len(feasible) or not feasible:
        raise ValueError("NNF node header wrong")
    result=feasible[-1]
    for lit in fixed:result&=allowed(lit)
    for group in free:
        p=m=full
        for lit in group:
            p&=allowed(lit);m&=allowed(-lit)
        result&=p|m
    unresolved=[j for j in range(len(clauses)) if result&(1<<j)]
    all_orig=[abs(l) for group in mapping.values() for l in group]
    all_orig.extend(abs(l) for l in fixed)
    for group in free:all_orig.extend(abs(l) for l in group)
    if sorted(all_orig)!=list(range(1,n+1)):
        raise ValueError("incomplete/duplicated original variable mapping")
    return {
      "cnf_sha256":hashlib.sha256(cnf.read_bytes()).hexdigest(),
      "nnf_sha256":hashlib.sha256(nnf.read_bytes()).hexdigest(),
      "original_vars":n,"original_clauses":len(clauses),
      "compiled_nnf_nodes":len(feasible),
      "checked_decomposable_and_nodes":n_and,
      "checked_or_nodes":n_or,
      "nnf_entails_all_original_cnf_clauses":len(unresolved)==0,
      "nnf_models_that_can_violate_original_clauses":len(unresolved),
      "example_unproven_clause_indices":unresolved[:10],
      "elapsed_seconds":round(time.monotonic()-start,4),
      "independent_complete_reverse_cnf_implies_nnf_proof":False,
      "independent_checked_unsat_proof_file":False,
      "method":"bit-parallel exact existential satisfiability under each clause falsification",
    }

def main(source,out,cases):
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    for label in cases:
        r=entailment(source/(label+".cnf"),source/(label+".nnf"))
        r["case"]=label
        print("BITPARALLEL_NNF_IMPLIES_CNF "+json.dumps(r,sort_keys=True),flush=True)
        results.append(r)
    (out/"bitparallel-nnf-to-cnf.json").write_text(json.dumps(
        {"records":results,"one_direction_only":True},indent=2,sort_keys=True)+"\n")
    if any(not r["nnf_entails_all_original_cnf_clauses"] for r in results):
        raise AssertionError("NNF did not independently imply the original CNF")
    print("BITPARALLEL_ALL_ORIGINAL_CLAUSES_ENTAILED",sum(r["original_clauses"] for r in results),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--artifact-folder",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--case",action="append",required=True)
    x=p.parse_args()
    main(x.artifact_folder,x.output,x.case)

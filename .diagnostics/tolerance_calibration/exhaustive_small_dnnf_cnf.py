"""Independent exhaustive equivalence check for *small* CNF vs emitted d-DNNF.

Research-only verifier. Enumerates all 2^n assignments (n<=14) and
independently interprets GPMC's vmap, fixed and free variable groups.
This proves exact Boolean equivalence for the *given* small pair,
but says nothing about general large-CNF compiler correctness.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def verify(cnf_path:Path,nnf_path:Path):
    text=cnf_path.read_text()
    n=None;clauses=[]
    for line in text.splitlines():
        a=line.split()
        if not a:continue
        if a[:2]==["p","cnf"]:
            if n is not None:raise ValueError("duplicate CNF header")
            n=int(a[2])
            if n>14:raise ValueError("exhaustive proof limited to n<=14")
        elif a[0]!="c":
            if a[-1]!="0":raise ValueError("CNF clause terminator")
            clauses.append(tuple(map(int,a[:-1])))
    if n is None:raise ValueError("no CNF header")

    mapping={};fixed=[];free=[];nodes=[];nnf_n=None
    for line in nnf_path.read_text().splitlines():
        a=line.split()
        if not a or a[0]=="c":continue
        t=a[0]
        if t=="p":
            if a[1]!="vmap" or int(a[2])!=n:
                raise ValueError("original variable map mismatch")
        elif t=="v":
            original,lit=int(a[1]),int(a[2])
            mapping.setdefault(abs(lit),[]).append(original*(1 if lit>0 else -1))
        elif t=="a":fixed.extend(map(int,a[1:-1]))
        elif t=="f":free.append(tuple(map(int,a[1:-1])))
        elif t=="d":
            if len(a)>2:raise ValueError("deleted variable unsupported")
        elif t=="nnf":nnf_n=int(a[1])
        elif t=="L":nodes.append(("L",int(a[1]),()))
        elif t=="A":
            children=tuple(map(int,a[2:]))
            if len(children)!=int(a[1]):raise ValueError("bad AND arity")
            nodes.append(("A",0,children))
        elif t=="O":
            children=tuple(map(int,a[3:]))
            if len(children)!=int(a[2]):raise ValueError("bad OR arity")
            nodes.append(("O",int(a[1]),children))
        else:raise ValueError(("unsupported dDNNF line",t))
    if nnf_n!=len(nodes) or not nodes:
        raise ValueError("dDNNF node count mismatch")
    mismatches=[];n_true=0
    for bits in range(1<<n):
        def lit_true(lit):
            return bool(bits&(1<<(abs(lit)-1)))==(lit>0)
        is_cnf=all(any(lit_true(lit) for lit in clause) for clause in clauses)
        v=[]
        for node_type,literal,children in nodes:
            if node_type=="L":
                lits=mapping.get(abs(literal))
                if lits is None:raise ValueError("unmapped NNF literal")
                v.append(all(lit_true(x*(1 if literal>0 else -1)) for x in lits))
            elif node_type=="A":
                v.append(all(v[k] for k in children))
            else:
                v.append(any(v[k] for k in children))
        is_nnf=(v[-1] and all(lit_true(lit) for lit in fixed)
            and all(all(lit_true(lit) for lit in group)
                    or all(lit_true(-lit) for lit in group)
                    for group in free))
        if is_cnf!=is_nnf:
            mismatches.append(bits)
        n_true+=is_cnf
    output={
        "cnf_sha256":hashlib.sha256(cnf_path.read_bytes()).hexdigest(),
        "nnf_sha256":hashlib.sha256(nnf_path.read_bytes()).hexdigest(),
        "n_variables":n,"assignments_checked":1<<n,
        "satisfying_assignments_original_cnf":n_true,
        "mismatches":len(mismatches),
        "sample_mismatches":mismatches[:6],
        "small_specific_pair_boolean_equivalence_proven":len(mismatches)==0,
        "not_general_compiler_certificate":True,
    }
    if mismatches:raise AssertionError(output)
    return output


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--cnf",type=Path,required=True)
    ap.add_argument("--nnf",type=Path,required=True)
    args=ap.parse_args()
    print("EXHAUSTIVE_CNF_NNF_VERDICT "+json.dumps(verify(args.cnf,args.nnf),
        sort_keys=True),flush=True)

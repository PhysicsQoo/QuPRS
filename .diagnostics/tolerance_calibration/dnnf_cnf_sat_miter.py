"""Independent SAT-backed CNF vs GPMC d-DNNF Boolean miter.

No assignment enumeration. Tseitin-encode both original CNF and the
entire emitted (vmap/fixed/free)-expanded NNF, then solve XOR of truth.
UNSAT from a separate SAT implementation is useful evidence; it is
NOT a checked DRAT/LRAT proof certificate. Timeout/memory fail CLOSED.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import time

from pysat.solvers import Solver

def read_cnf(path):
    n=None;clauses=[]
    for line in path.read_text().splitlines():
        a=line.split()
        if not a:continue
        if a[:2]==["p","cnf"]:
            if n is not None:raise ValueError("duplicate CNF header")
            n=int(a[2]);expected=int(a[3])
        elif a[0]!="c":
            if a[-1]!="0":raise ValueError("CNF lacks terminator")
            clauses.append(tuple(int(v) for v in a[:-1]))
    if n is None or len(clauses)!=expected:raise ValueError("CNF size mismatch")
    return n,clauses

def read_nnf(path,n):
    mapv=defaultdict(list);fixed=[];free=[];nodes=[]
    header=None
    for line in path.read_text().splitlines():
        a=line.split()
        if not a or a[0]=="c":continue
        token=a[0]
        if token=="p":
            if a[1]!="vmap" or int(a[2])!=n:raise ValueError("vmap")
        elif token=="v":
            orig,sim=int(a[1]),int(a[2])
            if not 1<=orig<=n or sim==0:raise ValueError("map variable")
            mapv[abs(sim)].append(orig*(1 if sim>0 else -1))
        elif token=="a":fixed.extend(map(int,a[1:-1]))
        elif token=="f":free.append(tuple(map(int,a[1:-1])))
        elif token=="d":
            if len(a)>2:raise ValueError("deleted variable not supported")
        elif token=="nnf":header=tuple(map(int,a[1:]))
        elif token=="L":nodes.append(("L",int(a[1]),()))
        elif token=="A":
            args=tuple(map(int,a[2:]))
            if len(args)!=int(a[1]):raise ValueError("bad AND arity")
            nodes.append(("A",0,args))
        elif token=="O":
            args=tuple(map(int,a[3:]))
            if len(args)!=int(a[2]):raise ValueError("bad OR arity")
            nodes.append(("O",int(a[1]),args))
        else:raise ValueError(("unknown NNF opcode",token))
    if not nodes or header is None or header[0]!=len(nodes):
        raise ValueError("NNF nodes mismatch")
    if any(k>=len(nodes) or k<0 for _,_,c in nodes for k in c):
        raise ValueError("out-of-range NNF edge")
    return mapv,fixed,free,nodes,header

class Builder:
    def __init__(self,n,solver):
        self.next=n
        self.solver=solver
        self.clauses_added=0
    def add(self,clause):
        self.solver.add_clause(clause)
        self.clauses_added+=1
    def gate(self,typ,lits):
        self.next+=1
        y=self.next
        if typ=="A":
            for lit in lits:self.add([-y,lit])
            self.add([y]+[-lit for lit in lits])
        else:
            for lit in lits:self.add([y,-lit])
            self.add([-y]+list(lits))
        return y

def run_one(folder,label):
    root=folder/(label+".cnf"); nnf=folder/(label+".nnf")
    n,clauses=read_cnf(root)
    maps,fixed,free,nodes,header=read_nnf(nnf,n)
    started=time.monotonic()
    with Solver(name="cadical153") as solver:
        b=Builder(n,solver)
        outputs=[]
        for typ,param,children in nodes:
            if typ=="L":
                source=maps.get(abs(param))
                if not source:raise ValueError(("missing original literal mapping",param))
                sign=1 if param>0 else -1
                y=b.gate("A",[sign*lit for lit in source])
            elif typ=="A":
                if any(x>=len(outputs) for x in children):raise ValueError("forward AND edge")
                y=b.gate("A",[outputs[k] for k in children])
            else:
                if any(x>=len(outputs) for x in children):raise ValueError("forward OR edge")
                y=b.gate("O",[outputs[k] for k in children])
            outputs.append(y)
        parts=[outputs[-1],*fixed]
        for group in free:
            a=b.gate("A",list(group))
            neg=b.gate("A",[-x for x in group])
            parts.append(b.gate("O",[a,neg]))
        nnf_truth=b.gate("A",parts)
        cnf_clauses=[b.gate("O",list(c)) for c in clauses]
        cnf_truth=b.gate("A",cnf_clauses)
        b.add([nnf_truth,cnf_truth])
        b.add([-nnf_truth,-cnf_truth])
        construction=time.monotonic()-started
        sat=solver.solve()
        elapsed=time.monotonic()-started
        row={
            "case":label,"cnf_sha256":hashlib.sha256(root.read_bytes()).hexdigest(),
            "nnf_sha256":hashlib.sha256(nnf.read_bytes()).hexdigest(),
            "original_cnf_vars":n,"original_cnf_clauses":len(clauses),
            "nnf_nodes":len(nodes),"nnf_edges":header[1],
            "tseitin_boolean_variables":b.next,"sat_clauses":b.clauses_added,
            "construction_seconds":round(construction,3),
            "total_seconds":round(elapsed,3),
            "sat_backend":"CaDiCaL 1.5.3 via PySAT",
            "solver_says_cnf_xor_nnf_is_sat":sat,
            "sat_backed_semantic_equivalence":not sat,
            "independent_drat_lrat_certificate_checked":False,
            "not_a_proof_of_all_gpmc_compilations":True,
        }
        if sat:
            assignment=solver.get_model()
            bits={abs(k):k>0 for k in assignment if abs(k)<=n}
            original=all(any(bits.get(abs(v),False)==(v>0) for v in c)
                         for c in clauses)
            # Independently evaluate the NNF from *original* assignments
            result=[]
            for typ,param,children in nodes:
                if typ=="L":
                    literals=maps[abs(param)]
                    sign=1 if param>0 else -1
                    value=all(bits[abs(q)]==(sign*q>0) for q in literals)
                elif typ=="A":value=all(result[j] for j in children)
                else:value=any(result[j] for j in children)
                result.append(value)
            nnf_value=(result[-1] and all(bits[abs(q)]==(q>0) for q in fixed)
                and all(all(bits[abs(q)]==(q>0) for q in group)
                        or all(bits[abs(q)]==(-q>0) for q in group)
                        for group in free))
            row["confirmed_counterexample"]=original!=nnf_value
            row["original_cnf_on_counterexample"]=original
            row["mapped_nnf_on_counterexample"]=nnf_value
            row["counterexample_original_assignment"]=[k if bits[k] else -k
                                                        for k in range(1,n+1)]
        return row

def main(folder,out,cases):
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for name in cases:
        row=run_one(folder,name)
        print("NONEXHAUSTIVE_CNF_NNF_MITER "+json.dumps(row,sort_keys=True),flush=True)
        rows.append(row)
    (out/"nonexhaustive-sat-miter.json").write_text(json.dumps({
        "cases":rows,
        "no_formal_checked_sat_proof":True,
        "not_generalized_cnf_to_dnnf_certificate":True
    },indent=2,sort_keys=True)+"\n")
    if any(r["solver_says_cnf_xor_nnf_is_sat"] for r in rows):
        raise AssertionError("SAT found a possible CNF/dDNNF mismatch")
    print("SAT_MITER_SELECTED_CASES_UNSAT_NO_CHECKED_PROOF",len(rows),flush=True)

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--artifact-folder",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    a.add_argument("--case",action="append",required=True)
    x=a.parse_args();main(x.artifact_folder,x.output,x.case)

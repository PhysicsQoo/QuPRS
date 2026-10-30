"""Research-only checked DRUP for the 31-variable QPE CNF<=>NNF pair.

Reuses independently tested Boolean interpretation of mapped NNF and
a separate RUP-checker. Corrects the prior SAT-only status of this
fixed QPE baseline; all proof checks are offline, never public hot path.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
from pysat.solvers import Solver
from dnnf_cnf_sat_miter import read_cnf,read_nnf,Builder
from qft_checked_functional_rup import IndependentRUP,parse_proof,write_dimacs

CASES={"qpeexact8-baseline":(31,83),
       "qpeexact8-self_negative":(10,1)}
class Collect:
    def __init__(self):self.formula=[]
    def add_clause(self,clause):self.formula.append(tuple(clause))

def build(cnf,nnf):
    n,clauses=read_cnf(cnf)
    maps,fixed,free,nodes,header=read_nnf(nnf,n)
    out=Collect();b=Builder(n,out)
    nodes_out=[]
    for typ,param,children in nodes:
        if typ=="L":
            sources=maps.get(abs(param))
            if not sources:raise ValueError("unmapped simplified literal")
            sign=1 if param>0 else -1
            y=b.gate("A",[sign*q for q in sources])
        elif typ=="A":
            if any(j>=len(nodes_out) for j in children):raise ValueError("forward AND")
            y=b.gate("A",[nodes_out[j] for j in children])
        else:
            if any(j>=len(nodes_out) for j in children):raise ValueError("forward OR")
            y=b.gate("O",[nodes_out[j] for j in children])
        nodes_out.append(y)
    fixed_conjunction=[nodes_out[-1],*fixed]
    for group in free:
        p=b.gate("A",list(group))
        q=b.gate("A",[-x for x in group])
        fixed_conjunction.append(b.gate("O",[p,q]))
    nnf_truth=b.gate("A",fixed_conjunction)
    cnf_truth=b.gate("A",[b.gate("O",list(clause)) for clause in clauses])
    b.add([nnf_truth,cnf_truth])
    b.add([-nnf_truth,-cnf_truth])
    return out.formula,n,len(nodes),len(clauses)

def check_case(inp,out,name,expected):
    cnf=inp/(name+".cnf");nnf=inp/(name+".nnf")
    formula,n,nodes,clauses=build(cnf,nnf)
    if (n,nodes)!=expected:raise AssertionError(("source identity changed",n,nodes))
    proof_cnf=out/(name+".boolean-xor.cnf")
    proof_drup=out/(name+".boolean-xor.drup")
    write_dimacs(proof_cnf,formula)
    start=time.monotonic()
    with Solver(name="g4",with_proof=True) as solver:
        solver.append_formula(formula)
        sat=solver.solve()
        proof=solver.get_proof()
    if sat or not proof:raise AssertionError(("expected UNSAT with proof",name,sat))
    proof_drup.write_text("\n".join(proof)+"\n")
    checker=IndependentRUP(formula)
    additions=deletions=0;has_empty=False
    for deleted,clause in parse_proof(proof):
        if deleted:
            deletions+=1
            continue
        if not checker.check_rup(clause):
            raise AssertionError(("RUP rejection",name,additions))
        checker.add(clause)
        additions+=1
        if not clause:
            has_empty=True
            break
    if not has_empty:raise AssertionError("no empty clause checked")
    row={"case":name,
         "cnf_sha256":hashlib.sha256(cnf.read_bytes()).hexdigest(),
         "nnf_sha256":hashlib.sha256(nnf.read_bytes()).hexdigest(),
         "xor_cnf_sha256":hashlib.sha256(proof_cnf.read_bytes()).hexdigest(),
         "drup_sha256":hashlib.sha256(proof_drup.read_bytes()).hexdigest(),
         "original_cnf_variables":n,
         "original_cnf_clauses":clauses,
         "nnf_nodes":nodes,
         "Boolean_XOR_miter_clauses":len(formula),
         "checked_RUP_additions":additions,
         "safely_ignored_deletions":deletions,
         "checked_empty_clause":True,
         "original_fixed_CNF_iff_NNF_proven_by_checked_DRUP":True,
         "seconds":round(time.monotonic()-start,3),
         "not_a_general_solver_correctness_proof":True}
    print("QPE_CHECKED_DRUP_BOOLEAN_EQUIVALENCE "+json.dumps(row,sort_keys=True),flush=True)
    return row
def main(inp,out):
    out.mkdir(parents=True,exist_ok=True)
    rows=[check_case(inp,out,c,spec) for c,spec in CASES.items()]
    (out/"qpe-checked-boolean-equivalence.json").write_text(
        json.dumps({"records":rows,"general_compiler_proof":False},indent=2,sort_keys=True)+"\n")
    print("QPE_BOTH_FIXED_CNF_NNF_CHECKED_DRUP_UNSAT",flush=True)
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--artifact-folder",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    main(args.artifact_folder,args.output)

"""Independent original-CNF functional-extension SAT certificate research.

The real QFT16 CNF encoder allocates:
  1..16: output qbits; 17..(n - numerical_weight_count): path vars;
  later vars: phase/Tseitin aux.
Prove (via SAT) that two satisfying assignments with identical path
variables cannot differ in any output/aux variable.

When UNSAT, CNF model count <= 2^(number of path vars).
Together with checked dDNNF=>CNF and independently evaluated
dDNNF model count = 2^k, this implies CNF <=> dDNNF for the
given instance, CONDITIONED on sound SAT UNSAT result.
A checked LRAT/DRAT solver proof would strengthen trust further.
No GPMC call, no production code modifications.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from pysat.solvers import Solver
from nnf_cnf_bitparallel_implication import entailment
from structure_aware_source_bound import simplified_graph_proof

EXPECTED={
 "qft16-baseline":(486,400,16,70),
 "qft16-self_negative":(465,385,16,64),
}

def clause_data(path):
    n=None;clauses=[]
    weights=set()
    for line in path.read_text().splitlines():
        a=line.split()
        if not a:continue
        if a[:2]==["p","cnf"]:
            n=int(a[2]);expected=int(a[3])
        elif a[:3]==["c","p","weight"] and int(a[3])>0:
            weights.add(int(a[3]))
        elif a[0]!="c":
            assert a[-1]=="0"
            clauses.append(tuple(map(int,a[:-1])))
    assert len(clauses)==expected
    return n,clauses,weights

def check_one(src,case):
    n,clauses,weights=clause_data(src/(case+".cnf"))
    expect=EXPECTED[case]
    if (n,len(weights))!=expect[:2]:
        raise AssertionError(("source CNF shape changed",case,n,len(weights)))
    nout,k=expect[2:]
    # Source-pinned Python to_DIMACS always assigns output bits first,
    # then path vars, then phase literals. Confirm this exact layout.
    path_variables=set(range(nout+1,nout+k+1))
    all_derived=set(range(1,n+1))-path_variables
    if weights!=set(range(nout+k+1,n+1)):
        raise AssertionError(("phase variables not exact final CNF range",case))
    implication=entailment(src/(case+".cnf"),src/(case+".nnf"))
    if not implication["nnf_entails_all_original_cnf_clauses"]:
        raise AssertionError("dDNNF not proven to imply original CNF")
    nnnf,_=simplified_graph_proof(src/(case+".nnf"),n)
    if nnnf!=2**k:
        raise AssertionError(("NNF model count not exact 2^free pathvars",case,nnnf,k))

    start=time.monotonic()
    # First CNF copy uses 1..n, second copy shares pathvar indices.
    # All other variables in copy2 are offset by +n.
    def second(v):
        return v if v in path_variables else v+n
    with Solver(name="cadical153") as sol:
        for clause in clauses:
            sol.add_clause(clause)
            sol.add_clause([second(abs(x))*(1 if x>0 else -1) for x in clause])
        # Tseitin XOR for every output/auxiliary difference.
        # d ↔ (a XOR b), then require OR_j(d_j).
        out_diff=[]
        q=2*n
        for v in sorted(all_derived):
            q+=1
            d=q
            a,b=v,second(v)
            sol.add_clause([-a,-b,-d])
            sol.add_clause([a,b,-d])
            sol.add_clause([a,-b,d])
            sol.add_clause([-a,b,d])
            out_diff.append(d)
        sol.add_clause(out_diff)
        solve_start=time.monotonic()
        sat=sol.solve()
        total=time.monotonic()-start
        row={
            "case":case,
            "cnf_sha256":hashlib.sha256((src/(case+".cnf")).read_bytes()).hexdigest(),
            "nnf_sha256":hashlib.sha256((src/(case+".nnf")).read_bytes()).hexdigest(),
            "free_path_variables":k,"output_bit_vars":nout,
            "phase_weight_variables":len(weights),
            "original_cnf_vars":n,"derived_variables":len(all_derived),
            "original_cnf_clauses":len(clauses),
            "dDNNF_subsumed_by_CNF_checked":True,
            "independent_NNF_integer_model_count":str(nnnf),
            "two_copy_CNF_same_pathvar_different_derived_SAT":sat,
            "unique_extension_if_unsat":not sat,
            "CNF_model_count_upper_bound":f"2^{k}" if not sat else None,
            "NNF_model_count_equals_upper_bound":nnnf==2**k,
            "fixed_CNF_NNF_equivalence_if_SAT_unsat_sound":not sat,
            "SAT_proof_independently_checked":False,
            "sat_solver":"CaDiCaL 1.5.3 via PySAT",
            "elapsed_seconds":round(total,3),
            "solve_seconds":round(time.monotonic()-solve_start,3),
            "no_GPMC_calls":True,
        }
        if sat:
            model=sol.get_model()
            truth={abs(x):x>0 for x in model}
            row["counterexample_derived_vars"]=[
                v for v in sorted(all_derived) if truth.get(v)!=truth.get(second(v))
            ][:25]
        print("FUNCTIONAL_CNF_UNIQUENESS "+json.dumps(row,sort_keys=True),flush=True)
        return row

def main(directory,out):
    out.mkdir(parents=True,exist_ok=True)
    records=[check_one(directory,name) for name in EXPECTED]
    (out/"functional-uniqueness-qft16.json").write_text(json.dumps({
        "cases":records,
        "conditional_full_cnf_dnnf_equivalence":all(x["fixed_CNF_NNF_equivalence_if_SAT_unsat_sound"] for x in records),
        "independent_unsat_proof_file_not_checked":True,
        "not_general_cnf_compiler_correctness":True},indent=2,sort_keys=True)+"\n")
    if any(x["two_copy_CNF_same_pathvar_different_derived_SAT"] for x in records):
        raise AssertionError("functional free-variable hypothesis failed")
    print("QFT16_FUNCTIONAL_UPPER_BOUND_PROVEN_IF_SAT_UNSAT_SOUND",flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--artifact-folder",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args();main(a.artifact_folder,a.output)

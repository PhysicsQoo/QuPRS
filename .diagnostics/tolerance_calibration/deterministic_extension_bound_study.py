"""Phase 13: source-pinned weighted-variable deterministic-extension research.

For each original QPE/QFT DIMACS, take the complement of its exact
positive weight variable IDs as the *conservative* primary set B.
Construct two copies of the ORIGINAL CNF sharing B, duplicating only
the weighted variables Z, and ask whether any Z differs.  An UNSAT
with an independently checked Glucose4 DRUP/RUP proof certifies that
the mapping B -> Z is a partial function.  Therefore #SAT(CNF) <= 2^|B|.

This does not establish that all B assignments are feasible, nor
that B is minimal. Tight QFT path-only 2^70/2^64 certificates already
exist separately. Intended as a lightweight bound FOR TRUSTED
ENCODER-GENERATED CNFs ONLY; arbitrary weighted DIMACS can have free Z.

Negative controls intentionally break a z<->AND definition and add
a free weighted z. Both MUST return SAT, with independently evaluated
counterexample assignments. No GPMC call and no production edit.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
from pysat.solvers import Solver
from qft_checked_functional_rup import IndependentRUP,parse_proof,write_dimacs

CASES={
 "qpeexact8-baseline":(31,17,"34d38d1718f1796d6af46cfa079aa2093aa00e5997f5b428e8af4b1672a35ee7",11),
 "qpeexact8-self_negative":(10,2,"b965d82a7bf4900350a2cbef028ff51506b9bb0f426859c1be9432207872d2d7",8),
 "qft16-baseline":(486,400,"20ee9e55eb1fc644d08daf130d180ded46f06f67897fa46f57b4f4ef4ef7f8f1",70),
 "qft16-self_negative":(465,385,"8e65b1d5cfdc99c4d980bc4fea24162afc4f9583e0ebf17686fc8a9f1bc6555c",64),
}
def read(path):
    n=None;clauses=[];weights=set()
    for raw in path.read_text().splitlines():
        a=raw.split()
        if not a:continue
        if a[:2]==["p","cnf"]:
            if n is not None:raise ValueError("multiple headers")
            n=int(a[2]);total=int(a[3])
        elif a[:3]==["c","p","weight"]:
            lit=int(a[3])
            if lit>0:
                if lit in weights:raise ValueError("duplicate positive weight")
                weights.add(lit)
        elif a[0]!="c":
            if a[-1]!="0":raise ValueError("clause terminator")
            clause=tuple(map(int,a[:-1]))
            if any(x==0 for x in clause):raise ValueError("zero in clause")
            clauses.append(clause)
    if n is None or len(clauses)!=total or not all(1<=k<=n for k in weights):
        raise ValueError("invalid CNF source")
    return n,clauses,weights
def two_copy(n,clauses,base):
    remaining=set(range(1,n+1))-base
    def copy2(lit):
        v=abs(lit)
        return (v if v in base else v+n)*(1 if lit>0 else -1)
    formula=[]
    for c in clauses:
        formula.append(tuple(c))
        formula.append(tuple(copy2(q) for q in c))
    difference=[]
    for idx,var in enumerate(sorted(remaining),1):
        d=2*n+idx
        a=var;b=var+n
        formula.extend([(-a,-b,-d),(a,b,-d),(a,-b,d),(-a,b,d)])
        difference.append(d)
    if not difference:raise ValueError("nothing to certify")
    formula.append(tuple(difference))
    return formula,remaining
def clause_true(clause,assignment):
    return any(assignment[abs(q)]==(q>0) for q in clause)
def prove(formula,n,original,derived,dirpath,case,must_unsat):
    out=dirpath/(case+".uniqueness.cnf")
    write_dimacs(out,formula)
    proofname=dirpath/(case+".uniqueness.drup")
    start=time.monotonic()
    with Solver(name="g4",with_proof=True) as solver:
        solver.append_formula(formula)
        sat=solver.solve()
        proof=solver.get_proof() if not sat else None
        model=solver.get_model() if sat else None
    if sat == must_unsat:raise AssertionError(("incorrect uniqueness decision",case,sat))
    entry={"case":case,"two_copy_miter_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
           "SAT":sat,"claimed_unique_extension":not sat,
           "miter_clauses":len(formula),
           "original_CNF_variables":n,"fixed_original_variables":len(set(range(1,n+1))-derived),
           "duplicated_original_variables":len(derived),
           "independent_RUP_checked":False}
    if sat:
        assignment={abs(lit):lit>0 for lit in model}
        first={v:assignment[v] for v in range(1,n+1)}
        second={v:assignment[v if v not in derived else v+n] for v in range(1,n+1)}
        if not all(clause_true(c,first) and clause_true(c,second) for c in original):
            raise AssertionError("SAT witness violates original copies")
        if not any(first[v]!=second[v] for v in derived):
            raise AssertionError("SAT witness does not differ on derived vars")
        if any(first[v]!=second[v] for v in set(range(1,n+1))-derived):
            raise AssertionError("shared base vars differ")
        entry["validated_non_unique_counterexample"]=True
        entry["different_auxiliary_variable_count"]=sum(first[v]!=second[v] for v in derived)
        entry["counterexample_base"]={str(v):int(first[v]) for v in sorted(set(range(1,n+1))-derived)}
    else:
        if not proof:raise AssertionError("missing UNSAT proof")
        proofname.write_text("\n".join(proof)+"\n")
        check=IndependentRUP(formula)
        additions=deletions=0;empty=False
        for deleted,clause in parse_proof(proof):
            if deleted:
                deletions+=1
                continue
            if not check.check_rup(clause):
                raise AssertionError(("invalid RUP addition",case,additions,clause))
            check.add(clause);additions+=1
            if not clause:
                empty=True
                break
        if not empty:raise AssertionError(("DRUP lacks empty clause",case))
        entry.update({"independent_RUP_checked":True,
                      "proof_SHA256":hashlib.sha256(proofname.read_bytes()).hexdigest(),
                      "RUP_additions_checked":additions,
                      "ignored_deletions_sound":deletions,
                      "independent_empty_clause":True})
    entry["seconds"]=round(time.monotonic()-start,3)
    print("DETERMINISTIC_WEIGHT_EXTENSION "+json.dumps(entry,sort_keys=True),flush=True)
    return entry
def controls(out):
    # z=3 iff x1 AND x2, 3 clauses; base x1, x2.
    valid=[(-3,1),(-3,2),(3,-1,-2)]
    cases=[
        ("positive_AND_definition",3,valid,{1,2},True),
        ("negative_missing_reverse_clause",3,valid[:2],{1,2},False),
        ("negative_unconstrained_weighted_var",3,[(1,)],{1,2},False),
        ("positive_constant_phase_weight",2,[(2,)],{1},True),
        ("positive_XOR_definition",3,[(-1,-2,-3),(1,2,-3),(1,-2,3),(-1,2,3)],{1,2},True)
    ]
    result=[]
    for name,n,clauses,base,unsat in cases:
        m,derived=two_copy(n,clauses,base)
        row=prove(m,n,clauses,derived,out,name,unsat)
        row["expected_control_label"]="reject" if not unsat else "accept"
        result.append(row)
    return result
def main(inp,out):
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for case,(nv,m,sha,tight_k) in CASES.items():
        path=inp/(case+".cnf")
        if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
            raise AssertionError(("source SHA changed",case))
        n,clauses,weighted=read(path)
        if n!=nv or len(weighted)!=m:raise AssertionError(("CNF size moved",case))
        base=set(range(1,n+1))-weighted
        formula,derived=two_copy(n,clauses,base)
        row=prove(formula,n,clauses,derived,out,case,True)
        row.update({"original_CNF_SHA256":sha,
          "positive_weight_variables":m,
          "conservative_free_basis_size":len(base),
          "certified_CNF_model_upper_bound":f"2^{len(base)}",
          "prior_fixture_specific_tighter_bound":f"2^{tight_k}",
          "bound_gap_power_of_two":len(base)-tight_k,
          "no_GPMC_calls":True,"not_general_arbitrary_weighted_DIMACS_certificate":True})
        rows.append(row)
    controls_result=controls(out)
    (out/"deterministic-extension-proof-study.json").write_text(
       json.dumps({"real_cnf":rows,"adversarial_controls":controls_result,
          "universal_theorem_requires_encoder_definition_source_review":True,
          "from_DIMACS_alone_weight_literal_independence_is_NOT_guaranteed":True,
          "extra_solver_calls_in_production":0},indent=2,sort_keys=True)+"\n")
    print("DETERMINISTIC_EXTENSION_FOUR_REAL_AND_FIVE_CONTROLS_COMPLETE",flush=True)
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--artifact-folder",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    a=ap.parse_args();main(a.artifact_folder,a.output)

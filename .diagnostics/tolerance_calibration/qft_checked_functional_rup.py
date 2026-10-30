"""Independent checked DRUP certificate for QFT16 functional-extension UNSAT.

Construct the exact two-copy original-CNF uniqueness miter from archived
source CNF. Log a Glucose4 DRUP clausal refutation. Independently check
every added clause by reverse unit propagation (RUP), explicitly requiring
the empty clause. Clause deletions are ignored conservatively: keeping
earlier logically implied clauses is sound.

If both fixed miters have valid independently checked RUP refutations,
then every pathvar assignment has at most one CNF extension. Combined
with independently checked dDNNF => original CNF and exact dDNNF
model count of 2^k, it proves Boolean equivalence of these fixed
CNF/NNF pairs. No GPMC invocation and no production changes.
"""
from __future__ import annotations
import argparse
from collections import defaultdict,deque
import hashlib,json,time
from pathlib import Path
from pysat.solvers import Solver
from qft_cnf_functional_uniqueness import clause_data, EXPECTED
from nnf_cnf_bitparallel_implication import entailment
from structure_aware_source_bound import simplified_graph_proof

def construct(src,case):
    n,clauses,weights=clause_data(src/(case+".cnf"))
    expected_n,m,nout,nfree=EXPECTED[case]
    if (n,len(weights))!=(expected_n,m):raise AssertionError("source mismatch")
    base=set(range(nout+1,nout+nfree+1))
    nonbase=set(range(1,n+1))-base
    if weights!=set(range(nout+nfree+1,n+1)):
        raise AssertionError("source phase weight numbering changed")
    def mapped(v):return v if v in base else v+n
    formula=[]
    for c in clauses:
        formula.append(c)
        formula.append(tuple(mapped(abs(x))*(1 if x>0 else -1) for x in c))
    differences=[]
    for idx,v in enumerate(sorted(nonbase),start=1):
        d=2*n+idx
        a,b=v,mapped(v)
        formula.extend([
            (-a,-b,-d),(a,b,-d),(a,-b,d),(-a,b,d)
        ])
        differences.append(d)
    formula.append(tuple(differences))
    return formula,n,len(base)

class IndependentRUP:
    def __init__(self,initial):
        self.clauses=[]
        self.index=defaultdict(list)
        self.units=[]
        self.empty=False
        for c in initial:self.add(c)
    def add(self,clause):
        c=tuple(clause)
        j=len(self.clauses)
        self.clauses.append(c)
        if not c:self.empty=True
        elif len(c)==1:self.units.append(c[0])
        for v in set(c):self.index[v].append(j)
    def check_rup(self,new):
        if self.empty:return True
        # We try to derive a contradiction from formula + ¬new.
        todo=deque([-x for x in new])
        todo.extend(self.units)
        values={}
        while todo:
            lit=todo.popleft();v=abs(lit);sgn=lit>0
            old=values.get(v)
            if old is not None:
                if old!=sgn:return True
                continue
            values[v]=sgn
            # Only clauses containing the freshly falsified literal can
            # become newly unit or empty.
            for idx in self.index.get(-lit,()):
                clause=self.clauses[idx]
                unassigned=None;many=False;satisfied=False
                for other in clause:
                    state=values.get(abs(other))
                    if state is None:
                        if unassigned is not None:many=True;break
                        unassigned=other
                    elif state==(other>0):
                        satisfied=True
                        break
                if satisfied or many:continue
                if unassigned is None:return True
                todo.append(unassigned)
        return False

def parse_proof(text):
    for line in text:
        s=line.strip()
        if not s or s.startswith("c "):continue
        deleting=s.startswith("d ")
        if deleting:s=s[2:].strip()
        parts=s.split()
        if not parts or parts[-1]!="0":
            raise ValueError(("invalid DRUP proof clause",line[:80]))
        try:c=tuple(map(int,parts[:-1]))
        except ValueError as e:raise ValueError(("bad proof integer",line[:80])) from e
        if 0 in c:raise ValueError("zero inside proof clause")
        yield deleting,c

def write_dimacs(path,formula):
    top=max(abs(x) for c in formula for x in c)
    with path.open("w") as f:
        f.write(f"p cnf {top} {len(formula)}\n")
        for c in formula:f.write(" ".join(map(str,c))+" 0\n")

def do_case(source,out,label):
    original=source/(label+".cnf")
    nnf=source/(label+".nnf")
    mapping=entailment(original,nnf)
    if not mapping["nnf_entails_all_original_cnf_clauses"]:
        raise AssertionError("NNF not subset original CNF")
    original_vars=EXPECTED[label]
    k=original_vars[3]
    nnf_models,notes=simplified_graph_proof(nnf,original_vars[0])
    if nnf_models!=2**k:raise AssertionError("NNF count mismatch")
    formula,n,nfree=construct(source,label)
    formula_path=out/(label+".functional-miter.cnf")
    proof_path=out/(label+".functional-proof.drup")
    write_dimacs(formula_path,formula)
    begin=time.monotonic()
    with Solver(name="g4",with_proof=True) as solver:
        solver.append_formula(formula)
        sat=solver.solve()
        proof=solver.get_proof()
    if sat or not proof:raise AssertionError(("no DRUP UNSAT proof",label,sat))
    proof_path.write_text("\n".join(proof)+"\n")
    solve_sec=time.monotonic()-begin
    begin_check=time.monotonic()
    checker=IndependentRUP(formula)
    additions=deletions=0;ended_empty=False
    for skip,clause in parse_proof(proof):
        if skip:
            deletions+=1
            continue
        if not checker.check_rup(clause):
            raise AssertionError(("invalid RUP addition",label,additions,len(clause),clause[:15]))
        checker.add(clause)
        additions+=1
        if not clause:
            ended_empty=True
            break
    if not ended_empty:raise AssertionError("proof never derived empty clause")
    row={
        "case":label,
        "original_CNF_SHA256":hashlib.sha256(original.read_bytes()).hexdigest(),
        "NNF_SHA256":hashlib.sha256(nnf.read_bytes()).hexdigest(),
        "functional_miter_CNF_SHA256":hashlib.sha256(formula_path.read_bytes()).hexdigest(),
        "independent_checked_DRUP_SHA256":hashlib.sha256(proof_path.read_bytes()).hexdigest(),
        "QFT_CNF_vars":n,
        "free_path_variables":nfree,
        "derived_variables":n-nfree,
        "functional_miter_clauses":len(formula),
        "SAT_solver":"Glucose4/PySAT with DRUP proof",
        "SAT_result":"UNSAT",
        "DRUP_RUP_addition_steps_verified":additions,
        "DRUP_deletion_steps_ignored_soundly":deletions,
        "independent_checker_derived_empty_clause":ended_empty,
        "proof_independently_checked":True,
        "SAT_run_seconds":round(solve_sec,4),
        "RUP_check_seconds":round(time.monotonic()-begin_check,4),
        "NNF_implies_CNF_structurally_checked":True,
        "NNF_integer_count":str(nnf_models),
        "CNF_model_count_upper_bound":"2^"+str(k),
        "exact_boolean_CNF_NNF_equality_for_fixed_case":True,
        "not_a_proof_of_general_GPMC_compiler_correctness":True,
        "source_gate_semantics_remain_separate":True,
        "production_solver_extra_runs":0,
    }
    print("INDEPENDENT_CHECKED_QFT_FUNCTIONAL_RUP "+json.dumps(row,sort_keys=True),flush=True)
    return row

def main(src,out):
    out.mkdir(parents=True,exist_ok=True)
    records=[do_case(src,out,k) for k in EXPECTED]
    (out/"checked-functional-semantics.json").write_text(
        json.dumps({"records":records,
        "fixed_pair_boolean_semantics_certified":True,
        "not_all_QASM_semantics_certified":True},indent=2,sort_keys=True)+"\n")
    print("QFT16_BOTH_FIXED_CNF_NNF_BIDIRECTIONAL_WITH_CHECKED_RUP",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--artifact-folder",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    x=p.parse_args();main(x.artifact_folder,x.output)

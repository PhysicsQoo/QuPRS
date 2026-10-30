"""Research-only original CNF exact INTEGER model count cross-check.

The independently parsed dDNNF already satisfies (NNF -> CNF) on all
four cases. If exact *original CNF* model count matches the independent
exact dDNNF integer model count, set inclusion implies set equality.
This is a logically valid inference CONDITIONAL ON trusting GPMC's
unweighted mode-0 model counter. It is not a checked #SAT certificate.
No public WMC invocation or production classifier is modified.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from QuPRS.utils import WMC
from structure_aware_source_bound import simplified_graph_proof
from nnf_cnf_bitparallel_implication import entailment

CASES=("qpeexact8-baseline","qpeexact8-self_negative",
       "qft16-baseline","qft16-self_negative")
MC=re.compile(r"^c s exact arb int ([0-9]+)$")

def run(input_dir,out):
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    with WMC("gpmc") as solver:
        for name in CASES:
            cnf=input_dir/(name+".cnf")
            nnf=input_dir/(name+".nnf")
            implications=entailment(cnf,nnf)
            if not implications["nnf_entails_all_original_cnf_clauses"]:
                raise AssertionError("emitted NNF is not a subset of original CNF")
            count_nn,structure=simplified_graph_proof(nnf,implications["original_vars"])
            result=subprocess.run([str(solver),"-mode=0",str(cnf)],
                text=True,capture_output=True,timeout=40,check=False)
            (out/(name+"-unweighted-gpmc.stdout")).write_text(result.stdout)
            (out/(name+"-unweighted-gpmc.stderr")).write_text(result.stderr)
            if result.returncode:
                raise AssertionError(("native GPMC mode 0 error",name,result.returncode,result.stderr[-250:]))
            integer_lines=[m.group(1) for l in result.stdout.splitlines()
                           if (m:=MC.fullmatch(l))]
            if len(integer_lines)!=1:raise AssertionError(("missing integer count",name))
            original_count=int(integer_lines[0])
            # Check GPMC's original direct-CNF integer result against
            # independently re-evaluated dDNNF (no GPMC dDNNF counting).
            equality=original_count==count_nn
            row={
                "case":name,
                "cnf_sha256":hashlib.sha256(cnf.read_bytes()).hexdigest(),
                "nnf_sha256":hashlib.sha256(nnf.read_bytes()).hexdigest(),
                "count_via_original_CNF_native_GPMC_mode0":str(original_count),
                "count_via_independent_dDNNF_integer_evaluation":str(count_nn),
                "NNF_subset_CNF_verified":True,
                "counts_equal":equality,
                "CNF_NNF_boolean_equivalence_if_GPMC_MC_is_correct":equality,
                "GPMC_unweighted_counter_correctness_proof_not_checked":True,
                "independent_proof_carrying_count_certificate":False,
                "direct_original_CNF_MC_research_solver_invocations":1,
                "public_WMC_solver_extra_calls":0,
                "NNF_and_checked":structure["nnf_AND_decomposability_verified"],
            }
            rows.append(row)
            print("UNWEIGHTED_CNF_NNF_COUNT_TRIANGULATION "+json.dumps(row,sort_keys=True),flush=True)
            if not equality:raise AssertionError(("ORIGINAL_CNF_NNF_COUNT_DIFFERENCE",name))
    (out/"original-cnf-unweighted-count-triangulation.json").write_text(
        json.dumps({"cases":rows,"not_a_checked_counter_proof":True,
                    "production_mode_unchanged":True},indent=2,sort_keys=True)+"\n")
    print("ORIGINAL_CNF_NNF_FOUR_CASE_COUNT_EQUALITY_CONDITIONAL",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--artifact-folder",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    run(a.artifact_folder,a.output)

"""Research-only structure-aware WMC source-weight perturbation enclosure.

Works entirely from the sealed CNF/NNF artifact; never invokes the Solver.
The interval is a mathematical theorem CONDITIONAL on:
  (a) faithful d-DNNF-to-original-CNF semantics,
  (b) per-positive-literal source weight error <= chosen delta,
  (c) unit-magnitude true phase weights,
  (d) correct source-to-CNF encoding/normalization.
A conditional result is NOT a proof of end-to-end source equivalence.
"""
from __future__ import annotations
from collections import Counter
from decimal import Decimal,localcontext
from fractions import Fraction
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from dnnf_exact_arithmetic_research import parse_weight_cnf,parse_evaluate

EPS=Fraction(1,10**8)
M=Fraction(1)+Fraction(1,2**40)
ONE=(Fraction(1),Fraction(0))
CASES={
    # Pinned QASM family, miter normalization 2**(twice/2),
    # pinned CNF identity. The normalization must be independently checked
    # against the public result before any production promotion.
    "qpeexact8-baseline":(22,"34d38d1718f1796d6af46cfa079aa2093aa00e5997f5b428e8af4b1672a35ee7"),
    "qpeexact8-self_negative":(16,"b965d82a7bf4900350a2cbef028ff51506b9bb0f426859c1be9432207872d2d7"),
    "qft16-baseline":(102,"20ee9e55eb1fc644d08daf130d180ded46f06f67897fa46f57b4f4ef4ef7f8f1"),
    "qft16-self_negative":(96,"8e65b1d5cfdc99c4d980bc4fea24162afc4f9583e0ebf17686fc8a9f1bc6555c"),
}

def simplified_graph_proof(path:Path, nvars):
    values=[];positive=[];negative=[];supports=[]
    original_membership=Counter()
    or_nodes=and_nodes=0
    decisions_verified=0
    free=0
    with path.open() as f:
        for line in f:
            parts=line.split()
            if not parts or parts[0]=="c":continue
            tag=parts[0]
            if tag=="p":
                if parts[1]!="vmap" or int(parts[2])!=nvars:
                    raise ValueError("wrong vmap header")
            elif tag=="v": original_membership[abs(int(parts[1]))]+=1
            elif tag=="a":
                for lit in parts[1:-1]:original_membership[abs(int(lit))]+=1
            elif tag=="f":
                free+=1 if len(parts)>2 else 0
                for lit in parts[1:-1]:original_membership[abs(int(lit))]+=1
            elif tag=="d":
                if len(parts)>2:raise ValueError("deleted original variable: fail closed")
            elif tag=="nnf":continue
            elif tag=="L":
                lit=int(parts[1]);mask=1<<(abs(lit)-1)
                supports.append(mask)
                positive.append(mask if lit>0 else 0)
                negative.append(mask if lit<0 else 0)
                values.append(1)
            elif tag=="A":
                children=list(map(int,parts[2:]))
                if len(children)!=int(parts[1]):raise ValueError("bad AND arity")
                s=p=n=0;v=1
                for ci in children:
                    if ci>=len(values) or s&supports[ci]:
                        raise ValueError("not a decomposable AND")
                    s|=supports[ci];p|=positive[ci];n|=negative[ci]
                    v*=values[ci]
                if p&n:raise ValueError("contradictory AND")
                supports.append(s);positive.append(p);negative.append(n)
                values.append(v);and_nodes+=1
            elif tag=="O":
                decision=int(parts[1])
                children=list(map(int,parts[3:]))
                if len(children)!=int(parts[2]) or len(children)!=2:
                    raise ValueError("not a binary decision OR")
                a,b=children
                if a>=len(values) or b>=len(values):
                    raise ValueError("forward graph edge")
                bit=1<<(decision-1)
                if not ((positive[a]&bit and negative[b]&bit)
                        or (negative[a]&bit and positive[b]&bit)):
                    raise ValueError("OR alternatives are not syntactically disjoint")
                supports.append(supports[a]|supports[b])
                positive.append(positive[a]&positive[b])
                negative.append(negative[a]&negative[b])
                values.append(values[a]+values[b])
                or_nodes+=1;decisions_verified+=1
            else:raise ValueError(("unsupported NNF token",tag))
    if len(original_membership)!=nvars or any(v!=1 for v in original_membership.values()):
        raise ValueError("original variable mappings are incomplete or duplicated")
    if not values:raise ValueError("empty d-DNNF")
    return values[-1]*(2**free),{
        "nnf_AND_decomposability_verified":and_nodes,
        "nnf_decision_OR_disjointness_verified":decisions_verified,
        "nnf_all_original_vars_unique":True,
        "nnf_independent_original_CNF_equivalence_proven":False,
    }

def fmt(x:Fraction, digits=32):
    if not x:return "0"
    with localcontext() as c:
        c.prec=digits
        return format(Decimal(x.numerator)/Decimal(x.denominator),".12E")

def source_error_bound(nsat:int,m:int,delta_bits:int):
    # Telescoping product with unit target weights and printed |w|<=M.
    return nsat * m * Fraction(1,2**delta_bits) * M**(max(m-1,0))

def evaluate_case(source:Path,case:str,twice:int,sha:str):
    cnf_file=source/(case+".cnf")
    nnf_file=source/(case+".nnf")
    cnf=cnf_file.read_text()
    if hashlib.sha256(cnf.encode()).hexdigest()!=sha:
        raise ValueError("source identity mismatch")
    nvars,weights=parse_weight_cnf(cnf)
    positive={k:v for k,v in weights.items() if k>0}
    assert len(positive)>0
    if any(weights.get(-k)!=ONE for k in positive):
        raise ValueError("only phase-positive/negative-unit CNF supported")
    if any(re*re+im*im>M*M for re,im in positive.values()):
        raise ValueError("one printed weight exceeds modulus bound")
    nsat,proof=simplified_graph_proof(nnf_file,nvars)
    exact,metadata=parse_evaluate(nnf_file,nvars,weights)
    assert metadata["nnf_and_decomposability_checked"]
    r,i=exact
    eps_squared=EPS*EPS
    norm_squared=Fraction(2)**twice
    norm=Fraction(2)**(twice//2) if twice%2==0 else None
    if norm is None:raise ValueError("odd normalization exponent not implemented")
    res={
        "case":case,"cnf_sha256":sha,
        "nnf_sha256":hashlib.sha256(nnf_file.read_bytes()).hexdigest(),
        "cnf_vars":nvars,
        "nnf_nodes":metadata["nnf_nodes"],
        "positive_weight_count":len(positive),
        "exact_nsat_integer":str(nsat),
        "exact_nsat_power_of_two":nsat.bit_length()-1 if nsat==2**(nsat.bit_length()-1) else None,
        "normalization_twice_pinned":twice,
        "source_bound_requires_independent_per_weight_delta_proof":True,
        "dnnf_correctness_against_CNF_not_formally_certified":True,
        **proof,
    }
    for bits in (49,100):
        E=source_error_bound(nsat,len(positive),bits)
        # Squared rational comparisons avoid floating square roots entirely.
        # Negative: sqrt(|C|²)+E < sqrt(T).
        # Positive: sqrt(|C|²)-E >= sqrt(T).
        c2=r*r+i*i
        threshold=norm_squared*(1-eps_squared)
        negative_gap=threshold-c2-E*E
        positive_gap=c2-threshold-E*E
        if negative_gap>0 and negative_gap*negative_gap>4*E*E*c2:
            tag="conditional_not_equivalent"
        elif positive_gap>=0 and positive_gap*positive_gap>=4*E*E*threshold:
            tag="conditional_within_distance"
        else:
            tag="unknown"
        res[f"per_weight_assumed_delta_2exp_minus_{bits}"]={
            "output_status":tag,
            "absolute_count_component_L1_bound":fmt(E),
            "normalized_complex_error_radius":fmt(E/norm),
            "bound_is_rigorous_given_assumptions":True,
            "independent_source_weight_rounding_certificate":False,
        }
    return res

def run(folder:Path,out:Path):
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for case,(twice,sha) in CASES.items():
        row=evaluate_case(folder,case,twice,sha)
        rows.append(row)
        print("STRUCTURAL_SOURCE_BOUND "+json.dumps(row,sort_keys=True),flush=True)
    result={
        "method":"Exact rational NNFs + exact integer satisfying-model count + per-literal telescoping perturbation inequality",
        "real_cnf_cases":rows,
        "input_weight_per_literal_delta_bits_are_assumptions_not_proven":True,
        "nnf_to_original_CNF_semantic_equivalence_is_not_formally_proven":True,
        "no_native_solver_invocations":True,
        "not_a_production_classifier":True,
    }
    (out/"structure-aware-source-uncertainty.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n")
    assert len(rows)==4
    print("STRUCTURAL_BOUND_FOUR_REAL_CASES_RECORDED",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--artifact-folder",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    run(a.artifact_folder,a.output)

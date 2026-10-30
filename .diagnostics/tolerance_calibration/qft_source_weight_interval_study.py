"""Research-only source-to-printed-CNF weight enclosures for real QFT16.

Exact rational source phases are certified by directed MPFR 384-bit
sine/cosine intervals, independently of SymEngine 113-bit evalf output.
Float-bearing / unsupported phase expressions are FAIL-CLOSED, not
silently promoted to exact source angles. No numerical-nearest-root snap.
One public WMC-only call for the complete original QFT16 is research-only.
"""
from __future__ import annotations
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))

import sympy as sp
from QuPRS import check_equivalence
from QuPRS.interface import ps2wmc
from mpfr_directed_phase_bound import Directed

PREVIOUS_QFT_CNF_SHA="20ee9e55eb1fc644d08daf130d180ded46f06f67897fa46f57b4f4ef7f8f1"
QFT_SOURCE_SHA=[
 "39b6889497a4e98098b6bb2b4563ace2fb660f4cc3fe8d0763d3f69fc200d865",
 "aa85188d731454bd85b0fe2ae089ab8e6b812501730eee5f1651ac11d7b7fcbc",
]
D49=Fraction(1,2**49)
D100=Fraction(1,2**100)

def fracstr(x):
    with localcontext() as c:
        c.prec=47
        return format(Decimal(x.numerator)/Decimal(x.denominator),".18E")

def get_source(expr):
    text=str(expr)
    try:
        parsed=sp.sympify(text,locals={"pi":sp.pi},evaluate=False)
    except Exception:
        return "unsupported_parse",None,text
    if parsed.free_symbols or not parsed.is_real:
        return "unsupported_expression",None,text
    if parsed.atoms(sp.Float):
        return "float_bearing_canonical_text_only",None,text
    if parsed.is_Rational:
        return "exact_rational",Fraction(int(parsed.p),int(parsed.q)),text
    evaluated=sp.simplify(parsed)
    if evaluated.is_Rational and not parsed.has(sp.Float):
        return "exact_symbolic_simplified_rational",Fraction(int(evaluated.p),int(evaluated.q)),text
    return "unsupported_symbolic",None,text

def main(out):
    from precision_followup_v2 import sources
    left,right,strategy,shas=sources("qft16")
    if shas!=QFT_SOURCE_SHA:raise AssertionError(("QFT QASM identities moved",shas))
    result=check_equivalence(str(left),str(right),backend="python",
        method="wmc_only",strategy=strategy,tool_name="gpmc",
        timeout=55,approximate_distance_tolerance=1e-8)
    cnf=result.CNF
    if not cnf:raise AssertionError("public API did not retain CNF")
    out.mkdir(parents=True,exist_ok=True)
    (out/"qft16-phase-corpus.cnf").write_text(cnf)
    cnf_hash=hashlib.sha256(cnf.encode()).hexdigest()
    coeffs=ps2wmc.P_to_wlogi(result.final_pathsum.P)
    native=[]
    for line in cnf.splitlines():
        p=line.split()
        if p[:3]==["c","p","weight"] and int(p[3])>0:
            native.append((int(p[3]),Fraction(Decimal(p[4])),Fraction(Decimal(p[5]))))
    if len(coeffs)!=400 or len(native)!=400:raise AssertionError((len(coeffs),len(native)))
    interval=Directed(); categories=Counter(); proven=[];cases=[]
    try:
        for ix,((phase,control),(var,re,im)) in enumerate(zip(coeffs,native)):
            category,cycle,phase_text=get_source(phase)
            categories[category]+=1
            if cycle is None:
                cases.append({"index":ix,"var":var,"category":category,
                    "phase":phase_text[:160],"source_coefficient_certified":False})
                continue
            rlo,rhi=interval.trig(cycle,Fraction(0),"cos")
            ilo,ihi=interval.trig(cycle,Fraction(0),"sin")
            # exact rational L1 upper bound also encloses complex L2 gap
            delta=max(abs(re-rlo),abs(re-rhi))+max(abs(im-ilo),abs(im-ihi))
            proven.append(delta)
            cases.append({"index":ix,"var":var,"category":category,
                "phase":phase_text[:160],
                "certified_l1_weight_gap":fracstr(delta),
                "under_2exp_minus49":delta<=D49,
                "under_2exp_minus100":delta<=D100,
                "source_coefficient_certified":True})
    finally:
        interval.close()
    n_certified=len(proven)
    measured_max=max(proven) if proven else Fraction(0)
    summary={
      "qft_source_hashes":shas,
      "qft_cnf_sha256":cnf_hash,
      "matching_phase6_cnf":cnf_hash==PREVIOUS_QFT_CNF_SHA,
      "positive_weight_count":len(native),
      "source_phase_types":dict(categories),
      "source_to_weight_certified_count":n_certified,
      "source_to_weight_uncertified_count":len(native)-n_certified,
      "certified_max_complex_l1_error":fracstr(measured_max),
      "all_certified_under_2exp_minus49":all(d<=D49 for d in proven),
      "all_certified_under_2exp_minus100":all(d<=D100 for d in proven),
      "public_verdict":result.equivalent,
      "public_printed_verdict":result.wmc_printed_verdict,
      "public_precision_reason":result.wmc_precision_reason,
      "symengine_evalf_rounding_proven":False,
      "exact_qasm_to_symengine_phase_proven":False,
      "float_source_semantics_not_upgraded_by_serialization":True,
      "one_public_solver_call":True,
      "candidate_global_bound_certified":n_certified==len(native),
    }
    (out/"qft16-source-phase-interval.json").write_text(
        json.dumps({"summary":summary,"entries":cases},indent=2,sort_keys=True)+"\n")
    print("QFT_SOURCE_INTERVAL_SUMMARY "+json.dumps(summary,sort_keys=True),flush=True)
    print("QFT_SOURCE_INTERVAL_LIMITED_CERTIFICATION "+str(len(native)-n_certified),flush=True)

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("--output",required=True,type=Path)
    args=ap.parse_args();main(args.output)

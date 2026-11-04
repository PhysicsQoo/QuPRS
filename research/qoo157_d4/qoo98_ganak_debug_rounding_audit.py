"""QOO-98 debug-CNF no-Arjun source preservation and decimal rounding audit.

No native solver execution; exact Decimal comparison of archived printed
literal weights and canonical unsigned clause multisets. This certifies
source-to-debug syntactic/decimal provenance ONLY, not WMC arithmetic.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from decimal import Decimal,localcontext
from hashlib import sha256
from pathlib import Path

CASES=("qaoa7_neq","qft16_eq")

def digest(raw):return sha256(raw).hexdigest()

def parse(path):
    header=None;clauses=[];weights={};projections={}
    for line in path.read_text().splitlines():
        q=line.split()
        if not q:continue
        if q[:2]==["p","cnf"]:
            assert header is None
            header=tuple(map(int,q[2:]))
        elif q[:3]==["c","p","weight"]:
            signed_lit=int(q[3])
            assert signed_lit and signed_lit not in weights
            if len(q)==7:
                assert q[-1]=="0"
                w=(Decimal(q[4]),Decimal(q[5]))
            elif len(q)==8:
                assert q[5] in ("+","-") and q[6].endswith("i") and q[-1]=="0"
                w=(Decimal(q[4]),Decimal(q[6][:-1])*(1 if q[5]=="+" else -1))
            else:raise AssertionError("unknown weight dialect")
            assert all(x.is_finite() for x in w)
            weights[signed_lit]=w
        elif q[:2]==["c","p"] and q[2] in ("show","optshow","exist"):
            assert q[-1]=="0" and q[2] not in projections
            projections[q[2]]=tuple(map(int,q[3:-1]))
        elif q[0] not in ("p","c"):
            assert q[-1]=="0"
            clause=tuple(sorted(map(int,q[:-1])))
            assert all(x for x in clause)
            clauses.append(clause)
    assert header is not None and len(clauses)==header[1]
    return header,Counter(clauses),weights,projections

def analyze(case,source_dir,debug_dir,manifest,audit):
    original=source_dir/(case+".cnf")
    debug=debug_dir/case/"arjun0_puura0.debug.cnf"
    row=audit["cases"][case]["arjun0_puura0"]
    assert digest(original.read_bytes())==manifest["cases"][case]["same_cnf_sha256"]
    assert digest(debug.read_bytes())==row["debug_structure"]["sha256"]
    src_h,src_c,src_w,_=parse(original)
    dst_h,dst_c,dst_w,projection=parse(debug)
    assert src_h==dst_h and src_c==dst_c
    assert set(src_w)==set(dst_w)
    assert all(len(projection[k])==src_h[0] for k in ("show","optshow"))
    assert len(projection["exist"])==0
    with localcontext() as ctx:
        ctx.prec=100
        errors={}
        for lit in src_w:
            x,y=src_w[lit],dst_w[lit]
            dr,di=x[0]-y[0],x[1]-y[1]
            errors[lit]=(dr*dr+di*di).sqrt()
        worst=max(errors,key=errors.get)
        summ=sum(errors.values(),Decimal(0))
    n_rounded=sum(x>0 for x in errors.values())
    result={"source_original_sha256":digest(original.read_bytes()),
        "ganak_no_arjun_debug_sha256":digest(debug.read_bytes()),
        "original_clause_header":list(src_h),
        "Boolean_clause_multiset_identical_ignoring_order_and_literal_order":True,
        "same_signed_literal_weight_keys":True,
        "signed_weight_count":len(src_w),
        "exact_literal_weight_pairs":len(src_w)-n_rounded,
        "rounded_literal_weight_pairs":n_rounded,
        "max_absolute_complex_weight_rounding":str(errors[worst]),
        "sum_absolute_complex_weight_rounding":str(summ),
        "worst_literal":worst,
        "worst_source_complex":list(map(str,src_w[worst])),
        "worst_debug_complex":list(map(str,dst_w[worst])),
        "all_original_input_weight_precision_retained":n_rounded==0,
        "complex_WMC_accuracy_guaranteed":False,
        "projection_debug_show":len(projection["show"]),
        "projection_debug_optshow":len(projection["optshow"]),
        "projection_debug_exist":len(projection["exist"]),
        "mechanism":"the Boolean clause multiset and signed literal IDs survive without Arjun; the native diagnostic writer rounds stored decimal complex weights"}
    return result

def main():
    p=argparse.ArgumentParser()
    for field in ("source-dir","debug-dir","source-manifest","native-audit","out"):
        p.add_argument("--"+field,type=Path,required=True)
    a=p.parse_args()
    manifest=json.loads(a.source_manifest.read_text())
    audit=json.loads(a.native_audit.read_text())
    assert manifest["complete"] is True
    assert audit["status"]=="ALL_FIVE_NATIVE_COUNT_SCREENS_CONCORDANT"
    rows={case:analyze(case,a.source_dir,a.debug_dir,manifest,audit)
          for case in CASES}
    result={"status":"TWO_SOURCE_LOCKED_NO_ARJUN_DECIMAL_ROUNDING_AUDITS_PASS",
      "uses_performance_timing":False,
      "internal_MPFR_error_certified":False,
      "debug_replay_38digit_output_certified":False,
      "cases":rows}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],
      "rounded_weights":{c:x["rounded_literal_weight_pairs"] for c,x in rows.items()}}))

if __name__=="__main__":main()

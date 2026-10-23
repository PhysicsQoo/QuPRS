"""Contrast source-pinned artifact Python with modern dev Python evidence.

Differences are scientific observations, not test failures by themselves.
A source mismatch, missing run, or invalid data remains a hard failure.
"""
import argparse
import csv
from fractions import Fraction
import json
import math
from pathlib import Path

CASES = (
    ("identical_empty","reduction_rules"),("identical_empty","hybrid"),("identical_empty","wmc_only"),
    ("identical_h","reduction_rules"),("identical_h","hybrid"),("identical_h","wmc_only"),
    ("hh_identity","reduction_rules"),("hh_identity","hybrid"),("hh_identity","wmc_only"),
    ("identity_x","reduction_rules"),("identity_x","hybrid"),("identity_x","wmc_only"),
    ("identity_rz_001","reduction_rules"),("identity_rz_001","hybrid"),("identity_rz_001","wmc_only"),
    ("identity_rz_01","reduction_rules"),("identity_rz_01","hybrid"),("identity_rz_01","wmc_only"),
    ("grover4_transpiled","reduction_rules"),("grover4_transpiled","hybrid"),
)

def source_oracle(angle):
    # Strict analytic certificate, not an approximate operator comparison.
    delta=Fraction(angle)
    x=abs(delta)/2
    lower=1-x*x/2
    upper=lower+x**4/24
    assert 0 < x <= Fraction(1,2) and upper < 1
    return {"trace_magnitude_lower":str(lower),
            "trace_magnitude_upper":str(upper),
            "strict_non_equivalence_up_to_global_phase":True}

def compare(paper,modern):
    a=json.loads(Path(paper).read_text())
    b=json.loads(Path(modern).read_text())
    if a["source_sha"]!="e928abc47dd15926364ec77905eb0d5dc92ce8cc":
        raise ValueError("Historical source pin invalid")
    if a["historical_reference"]!=b["historical_reference"] or a["historical_reference"]!=a["source_sha"]:
        raise ValueError("Historical input source mismatch")
    da={(z["case"],z["method"]):z for z in a["results"]}
    db={(z["case"],z["method"]):z for z in b["results"]}
    if set(da)!=set(CASES) or set(db)!=set(CASES):
        raise ValueError("Different or missing case matrix")
    out=[]
    for case,method in CASES:
        old=da[(case,method)]
        new=db[(case,method)]
        if old.get("source_label")!="artifact" or new.get("source_label")!="dev":
            raise ValueError("Unexpected source label")
        if (old.get("qasm_sha256") and new.get("qasm_sha256")
                and old["qasm_sha256"] != new["qasm_sha256"]):
            raise ValueError("Input QASM mismatch")
        status=(old["collection_outcome"],new["collection_outcome"])
        if status==("OBSERVED_RETURN","OBSERVED_RETURN"):
            relation="MATCH" if old["verdict"]==new["verdict"] else "VERDICT_DIFFERENCE"
            if old.get("wmc_executed")!=new.get("wmc_executed"):
                relation="WMC_ROUTE_DIFFERENCE"
            old_count=(old.get("inspection") or {}).get("solver_count")
            new_count=(new.get("inspection") or {}).get("solver_count")
            diff=None
            if old_count and new_count:
                diff=abs(complex(old_count["real"],old_count["imag"])-
                         complex(new_count["real"],new_count["imag"]))
        else:
            relation="UNRESOLVED_ENV_OR_EXECUTION"
            diff=None
        out.append({
            "case":case, "method":method,
            "old_verdict":old.get("verdict"),"dev_verdict":new.get("verdict"),
            "old_return":old["collection_outcome"],"dev_return":new["collection_outcome"],
            "old_wmc":old.get("wmc_executed"),"dev_wmc":new.get("wmc_executed"),
            "old_log_wmc":old.get("reported_log_wmc"),"dev_log_wmc":new.get("reported_log_wmc"),
            "old_reductions":old.get("reduction_counts"),"dev_reductions":new.get("reduction_counts"),
            "old_cnf_sha256":(old.get("inspection") or {}).get("cnf_sha256"),
            "dev_cnf_sha256":(new.get("inspection") or {}).get("cnf_sha256"),
            "solver_result_complex_abs_difference_float":diff,
            "old_gpmc_sha256":(old.get("gpmc") or {}).get("sha256"),
            "dev_gpmc_sha256":(new.get("gpmc") or {}).get("sha256"),
            "category":relation,
        })
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--paper",type=Path,required=True)
    p.add_argument("--dev",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    opts=p.parse_args()
    opts.output.mkdir(parents=True,exist_ok=True)
    data=compare(opts.paper,opts.dev)
    errors=[z for z in data if z["category"]=="UNRESOLVED_ENV_OR_EXECUTION"]
    result={
        "schema":"paper-era-python-v091-vs-dev-observational-matrix-v1",
        "artifact_version":"QuPRS v0.9.1",
        "historical_source_sha":"e928abc47dd15926364ec77905eb0d5dc92ce8cc",
        "planned_comparisons":len(data),
        "observed_pairs":len(data)-len(errors),
        "unresolved_pairs":len(errors),
        "verdict_differences":sum(z["category"]=="VERDICT_DIFFERENCE" for z in data),
        "wmc_route_differences":sum(z["category"]=="WMC_ROUTE_DIFFERENCE" for z in data),
        "exact_math_rz_001":source_oracle(Fraction(1,1000)),
        "exact_math_rz_01":source_oracle(Fraction(1,10)),
        "important_limits":"Solver binary SHA may differ; observation is not exact native solver parity. A near-one verdict is not mathematical equivalence certification.",
        "cases":data,
    }
    (opts.output/"comparison.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    with (opts.output/"comparison.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["case","method","old_verdict","dev_verdict",
                                      "old_wmc","dev_wmc","category",
                                      "solver_result_complex_abs_difference_float"])
        w.writeheader()
        for row in data:
            w.writerow({k:row.get(k) for k in w.fieldnames})
    print(json.dumps({k:result[k] for k in (
        "planned_comparisons","observed_pairs","unresolved_pairs",
        "verdict_differences","wmc_route_differences")}),flush=True)
    return 0 if not errors else 2

if __name__=="__main__":
    raise SystemExit(main())

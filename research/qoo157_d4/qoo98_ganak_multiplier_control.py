"""QOO-98 pinned Ganak debug-CNF multiplier negative controls. SCIENCE ONLY.

Do NOT interpret the prior double-multiply experiment as original WMC
disagreement: Ganak's run_weighted_counter obtains cnf.get_multiplier_weight()
and applies it internally. This experiment tests that behavior causally by
changing ONLY the c MUST MULTIPLY BY line on an archived debug CNF.
No walltime instrumentation, no cross-solver semantic admission.
"""
from __future__ import annotations
import argparse,json
from decimal import Decimal,localcontext
from pathlib import Path
from hashlib import sha256
from qoo98_ganak_debug_replay import load_debug,run_pinned

CASES=("qaoa7_neq","qft16_eq")
ARM="arjun1_puura1"

def digest(data):return sha256(data).hexdigest()

def num(reply):
    return (Decimal(reply["real"]),Decimal(reply["imag"]))

def norm(x):
    with localcontext() as c:
        c.prec=100
        return (x[0]*x[0]+x[1]*x[1]).sqrt()

def reldiff(x,y):
    with localcontext() as c:
        c.prec=100
        return norm((x[0]-y[0],x[1]-y[1]))/max(Decimal(1),norm(x),norm(y))

def mul(x,y):
    with localcontext() as c:
        c.prec=100
        return (x[0]*y[0]-x[1]*y[1],x[0]*y[1]+x[1]*y[0])

def control(binary,debug,archived,baseline,out):
    meta,factor=load_debug(debug,archived)
    raw=debug.read_bytes()
    original=(meta["multiplier_line"]+"\n").encode()
    assert raw.count(original)==1 and raw.endswith(original)
    assert baseline["status"]=="NATIVE_PRINTED_COMPLEX"
    variants={
      "factor_deleted":b"",
      "factor_explicit_unit":b"c MUST MULTIPLY BY 1.00000000e+00 + 0.00000000e+00i 0\n",
      "factor_sign_inverted":("c MUST MULTIPLY BY "+
        f"{-factor[0]:.8e} + {-factor[1]:.8e}i 0\n").encode(),
    }
    result={"source_debug_sha256":digest(raw),"source_factor":list(map(str,factor)),
        "baseline_original_native_count":[baseline["real"],baseline["imag"]],
        "only_factor_line_mutated":True,
        "weighted_projection_equivalence_certified":False,
        "output_precision_digits":9,"performance_timing":"NOT_OBSERVED","controls":{}}
    out.mkdir(parents=True,exist_ok=True)
    pre,post=raw.split(original)
    for name,replacement in variants.items():
        changed=pre+replacement+post
        assert changed.replace(replacement,original,1)==raw if replacement else changed+original==raw
        f=out/(name+".cnf")
        f.write_bytes(changed)
        try:seen=run_pinned(binary,f)
        except Exception as e:
            seen={"status":"NATIVE_READ_EXCEPTION","error":str(e)[:180]}
        result["controls"][name]={"sha256":digest(changed),
           "unchanged_prefix_sha256":digest(pre),
           "native":seen}
    if all(row["native"]["status"]=="NATIVE_PRINTED_COMPLEX"
           for row in result["controls"].values()):
        base=num(baseline)
        none=num(result["controls"]["factor_deleted"]["native"])
        one=num(result["controls"]["factor_explicit_unit"]["native"])
        inverted=num(result["controls"]["factor_sign_inverted"]["native"])
        metrics={
          "factor_absent_vs_unit_relative":reldiff(none,one),
          "factor_inverted_vs_negative_original_relative":reldiff(inverted,(-base[0],-base[1])),
          "explicit_unit_times_original_factor_vs_original_relative":reldiff(mul(one,factor),base),
          "original_vs_explicit_unit_relative":reldiff(base,one),
        }
        result["relative_complex_differences"]={k:str(v) for k,v in metrics.items()}
        # Coarse SCREEN, not arithmetic accuracy: ~9 printed significant digits.
        result["status"]=(
          "NATIVE_AUTOMATIC_MULTIPLIER_APPLIED_PRINT_SCREEN" if
          all(metrics[x]<Decimal("5e-8") for x in (
            "factor_absent_vs_unit_relative",
            "factor_inverted_vs_negative_original_relative",
            "explicit_unit_times_original_factor_vs_original_relative"))
          and metrics["original_vs_explicit_unit_relative"]>Decimal("0.1")
          else "MULTIPLIER_CONSUMPTION_SCREEN_INCONCLUSIVE")
    else:result["status"]="NATIVE_READER_CONTROL_INCOMPLETE"
    return result

def main():
    p=argparse.ArgumentParser()
    for flag in ("binary","intermediate-report","prior-replay-report","debug-dir","out"):
        p.add_argument("--"+flag,type=Path,required=True)
    a=p.parse_args()
    audited=json.loads(a.intermediate_report.read_text())
    replay=json.loads(a.prior_replay_report.read_text())
    binary_sha=digest(a.binary.read_bytes())
    assert audited["binary_sha256"]==replay["binary_sha256"]==binary_sha
    assert audited["status"]=="ALL_FIVE_NATIVE_COUNT_SCREENS_CONCORDANT"
    result={"status":"INCOMPLETE","binary_sha256":binary_sha,
            "new_source_sha256":None,"science_only":True,
            "not_a_38digit_residual_certificate":True,"cases":{}}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    for case in CASES:
        old=audited["cases"][case][ARM]
        assert old["count_status"]=="PRINT_CONCORDANT_UNCERTIFIED"
        row=replay["runs"][case][ARM]
        debug=a.debug_dir/case/(ARM+".debug.cnf")
        assert row["debug"]["sha256"]==old["debug_structure"]["sha256"]
        tested=control(a.binary,debug,old,row["native_reader"],
                       a.out.parent/("multiplier-control-"+case))
        result["cases"][case]=tested
        a.out.write_text(json.dumps(result,indent=2)+"\n")
    result["status"]=("BOTH_PINNED_FACTORS_AUTOMATICALLY_APPLIED_AT_PRINT_RESOLUTION"
      if all(v["status"]=="NATIVE_AUTOMATIC_MULTIPLIER_APPLIED_PRINT_SCREEN"
           for v in result["cases"].values()) else "FACTOR_CONTROLS_INCONCLUSIVE")
    result["intermediate_complex_WMC_semantic_certificate"]="NOT_CERTIFIED"
    result["same_effective_output_precision_38_digits"]="NOT_COMPARABLE"
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],
      "cases":{k:v["status"] for k,v in result["cases"].items()},
      "residual_WMC_certificate":"NOT_CERTIFIED"}))

if __name__=="__main__":main()

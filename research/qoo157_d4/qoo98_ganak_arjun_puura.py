"""QOO-98: Ganak pinned Mode6 Arjun x Puura 2x2 mechanism ablation.

Science gate first: signed source CNF SHA, exact Ganak dialect transport,
8 complex output counts inside component-wise print half-ULP plus *only*
legacy source-count screen. Times exclusively through official CodSpeed.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

import pytest
from qoo98_ganak_native_mode6_admission import OUTPUT, compare

SOURCE_CASES=("qaoa7_neq","qft16_eq")
KNOBS={
    "arjun1_puura1":("--arjun","1","--puura","1"),
    "arjun0_puura1":("--arjun","0","--puura","1"),
    "arjun1_puura0":("--arjun","1","--puura","0"),
    "arjun0_puura0":("--arjun","0","--puura","0"),
}

def load_fixed_source(case):
    native_report=json.loads(Path(os.environ["QOO98_GANAK_NATIVE_REPORT"]).read_text())
    old=json.loads(Path(os.environ["QOO98_SOURCE_SCIENCE"]).read_text())
    assert native_report["status"]=="NATIVE_PRINT_SCREEN_PASS_PRECISION_LIMITED"
    assert native_report["fair_38d_output_ranking"]=="NOT_COMPARABLE_FOR_38D_OUTPUT"
    row=native_report["source_cases"][case]
    source=Path(os.environ["QOO98_SOURCE_CNF_DIR"])/(case+".cnf")
    adapted=Path(os.environ["QOO98_GANAK_CNF_DIR"])/("original_"+case+".cnf")
    assert sha256(source.read_bytes()).hexdigest()==row["source_sha256"]
    assert sha256(adapted.read_bytes()).hexdigest()==row["serialization"]["ganak_dialect_sha256"]
    assert row["source_sha256"]==old["cases"][case]["same_cnf_sha256"]
    assert row["native"]["status"]=="PRINT_CONCORDANT_UNCERTIFIED"
    original=old["cases"][case]["precision_pairs"]["38"]["observations"]["gpmc-38"]
    with localcontext() as ctx:
        ctx.prec=110
        reference=tuple(Decimal(Fraction(original[k]).numerator)/
                        Decimal(Fraction(original[k]).denominator)
                        for k in ("real","imag"))
    return adapted,reference,row

def run_mode6(binary,cnf,knobs):
    cp=subprocess.run([
        str(binary),"--mode=6","--mpfrprec=127","--threads=1",*knobs,str(cnf)],
        capture_output=True,text=True,timeout=35,check=False)
    if cp.returncode:
        return {"status":"NATIVE_ERROR","returncode":cp.returncode,
                "stderr_excerpt":cp.stderr[-500:],"stdout_excerpt":cp.stdout[-500:]}
    match=[m for line in cp.stdout.splitlines()
           if (m:=OUTPUT.fullmatch(line))]
    if len(match)!=1:
        return {"status":"OUTPUT_FORMAT_ERROR",
                "lines":[l for l in cp.stdout.splitlines()
                         if l.startswith("c s exact ")][:4]}
    result={"status":"COMPLETED","real":match[0].group(1),
        "imag":match[0].group(2),
        "sat_label":[s for s in cp.stdout.splitlines()
                     if s in ("s SATISFIABLE","s UNSATISFIABLE")],
        "stdout_sha256":sha256(cp.stdout.encode()).hexdigest()}
    return result

def binary_pin():
    report=json.loads(Path(os.environ["QOO98_GANAK_NATIVE_REPORT"]).read_text())
    binary=Path(os.environ["QOO98_GANAK_BIN"])
    assert sha256(binary.read_bytes()).hexdigest()==report["official_binary_sha256"]
    return binary

def preflight(report_path):
    binary=binary_pin()
    report={"status":"INCOMPLETE","pinned_binary_sha256":sha256(binary.read_bytes()).hexdigest(),
      "preflight_only":True,"timing":"none","clock":"none",
      "requested_internal_mpfr_bits":127,"ganak_actual_stdout_digits":9,
      "certified_internal_numeric_error":False,
      "equal_38digit_output_comparison":False,
      "cases":{}}
    report_path.parent.mkdir(parents=True,exist_ok=True)
    for case in SOURCE_CASES:
        cnf,reference,row=load_fixed_source(case)
        for name,knobs in KNOBS.items():
            try:res=run_mode6(binary,cnf,knobs)
            except subprocess.TimeoutExpired:res={"status":"TIMEOUT_BEFORE_CODSPEED"}
            result=compare(res,reference,large=True)
            report["cases"].setdefault(case,{})[name]={
                "native":result,"knobs":list(knobs),
                "source_sha256":row["source_sha256"],
                "ganak_dialect_sha256":row["serialization"]["ganak_dialect_sha256"]}
            report_path.write_text(json.dumps(report,indent=2)+"\n")
            if result["status"]!="PRINT_CONCORDANT_UNCERTIFIED":
                report["status"]="FAILED_SCIENCE_PREFLIGHT"
                report_path.write_text(json.dumps(report,indent=2)+"\n")
                raise RuntimeError(f"{case}/{name}: {result['status']}")
    report["status"]="8_OF_8_GANAK_MODE6_PRINT_SCREENS_CONCORDANT"
    report_path.write_text(json.dumps(report,indent=2)+"\n")
    return report

@pytest.mark.parametrize("case,knob_name",[
    pytest.param(case,knob_name,id=f"{case}-{knob_name}")
    for case in SOURCE_CASES for knob_name in KNOBS
])
def test_native_ganak_arjun_puura_2x2(benchmark,case,knob_name):
    gate=json.loads(Path(os.environ["QOO98_GANAK_ABLATION_GATE"]).read_text())
    assert gate["status"]=="8_OF_8_GANAK_MODE6_PRINT_SCREENS_CONCORDANT"
    binary=binary_pin()
    cnf,reference,row=load_fixed_source(case)
    knobs=KNOBS[knob_name]
    result=benchmark(run_mode6,binary,cnf,knobs)
    assert compare(result,reference,large=True)["status"]=="PRINT_CONCORDANT_UNCERTIFIED"
    assert gate["cases"][case][knob_name]["native"]["status"]=="PRINT_CONCORDANT_UNCERTIFIED"
    benchmark.extra_info.update({
        "issue":"QOO-98","source_case":case,"ganak_variant":knob_name,
        "native_binary_sha256":sha256(binary.read_bytes()).hexdigest(),
        "source_original_CNF_sha256":row["source_sha256"],
        "native_ganak_dialect_sha256":row["serialization"]["ganak_dialect_sha256"],
        "requested_mpfr_bits":127,"printed_decimal_digits":9,
        "threads":1,"arjun_enabled":knobs[1]=="1","puura_enabled":knobs[3]=="1",
        "print_count_screen":"PRINT_CONCORDANT_UNCERTIFIED",
        "conditional_only":True,"no_equal_38digit_ranking":True,
        "walltime_scope":"native_child_subprocess_on_prepared_CNF",
        "official_instrument":"CodSpeed_v5_WallTime",
        "macro_runner_certified":False
    })

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--science-preflight",type=Path,required=True)
    a=parser.parse_args()
    print(json.dumps({"status":preflight(a.science_preflight)["status"]}))

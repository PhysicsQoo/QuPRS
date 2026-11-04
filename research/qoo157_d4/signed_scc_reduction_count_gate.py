"""QOO-157 original/reduced weighted CNF solver-count gate: no timing."""
from __future__ import annotations
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
from hashlib import sha256
import argparse
import json
import subprocess

from gpmc_td_ablation import COMPLEX,COUNT
from qoo157_preprocess_compare import D4_RESULT
from gpmc_vs_td_factorial import close_enough


def native_count(solver,binary,path):
    command=([binary,"-mode=1","-prec=38",str(path)] if solver=="gpmc"
             else [binary,"-i",str(path)])
    cp=subprocess.run(command,capture_output=True,text=True,timeout=38)
    if cp.returncode:
        raise RuntimeError(f"{solver} rc={cp.returncode}: {cp.stderr[:400]}")
    matches=(COUNT if solver=="gpmc" else D4_RESULT).findall(cp.stdout)
    if len(matches)!=1:raise ValueError(f"{solver}: wrong number count lines")
    p=COMPLEX.fullmatch(matches[0].strip())
    if not p:raise ValueError(f"{solver}: unparsable complex count")
    value=(Decimal(p.group(1)),Decimal(p.group(2)))
    if not all(v.is_finite() for v in value):
        raise ValueError("nonfinite")
    return value


def gate(gpmc,d4,original,reduced,source,exported,out):
    reference=json.loads(source.read_text())
    manifest=json.loads(exported.read_text())
    if manifest["status"]!="SOURCE_EXACT_REDUCTION_READY_FOR_SOLVER_COUNT_SCREEN":
        raise ValueError("no exact oracle stage")
    report={"status":"INCOMPLETE","gpmc_gitlink":"a1bda3489e959d3695b6798d327c5a1fc1bed305",
            "d4_upstream":"be15f91f3e9769e1f5cb175fa27e3eca3a1ea690",
            "gpmc_binary_sha256":sha256(Path(gpmc).read_bytes()).hexdigest(),
            "d4_scratch_binary_sha256":sha256(Path(d4).read_bytes()).hexdigest(),
            "gpmc_mpfr_bits":127,"d4_gmp_actual_bits":128,
            "effective_decimal_digits":38,"not_certified_arithmetic":True,
            "count_screen":"1e-12 * max(1,abs(reference real),abs(reference imag))",
            "cases":{}}
    for case,row in manifest["cases"].items():
        orig=original/(case+".cnf")
        red=reduced/(case+".cnf")
        if sha256(orig.read_bytes()).hexdigest()!=row["source_sha256"]:
            raise ValueError("original CNF changed")
        if sha256(red.read_bytes()).hexdigest()!=row["reduced_sha256"]:
            raise ValueError("reduced CNF changed")
        a=reference["cases"][case]["precision_pairs"]["38"]["observations"]["gpmc-38"]
        with localcontext() as ctx:
            ctx.prec=110
            anchor=tuple(Decimal(Fraction(a[k]).numerator)/
                         Decimal(Fraction(a[k]).denominator)
                         for k in ("real","imag"))
        observations={}
        for solver,binary in (("gpmc",gpmc),("d4",d4)):
            for variant,path in (("original",orig),("reduced",red)):
                count=native_count(solver,binary,path)
                ok,delta,bound=close_enough(count,anchor)
                observations[f"{solver}_{variant}"]={
                    "real":str(count[0]),"imag":str(count[1]),
                    "screen_pass":ok,"max_printed_delta":delta,"bound":bound,
                    "cnf_sha256":sha256(path.read_bytes()).hexdigest()}
                report["cases"][case]={"observations":observations}
                out.parent.mkdir(parents=True,exist_ok=True)
                out.write_text(json.dumps(report,indent=2)+"\n")
                if not ok:raise ValueError(f"{case}/{solver}/{variant}: printed WMC mismatch")
    report["status"]="ORIGINAL_REDUCED_FOUR_CASE_TWO_SOLVER_COUNT_SCREEN_PASS"
    out.write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ("gpmc","d4"):
        p.add_argument("--"+key,required=True)
    for key in ("original","reduced","source","exported","out"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args()
    result=gate(a.gpmc,a.d4,a.original,a.reduced,a.source,a.exported,a.out)
    print(json.dumps({"status":result["status"],"cases":list(result["cases"])}))

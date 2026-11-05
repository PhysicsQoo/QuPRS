"""QOO-157 P8 preproc-only/full same-binary scientific admission.

Preflight source-P7 raw residual dump byte identity and original complex WMC.
No timing data are derived from the native preflight; only CodSpeed may rank
performance. Nothing in this script changes d4 upstream or QuPRS dev/main.
"""
from __future__ import annotations
import argparse, json, os, subprocess, hashlib
from pathlib import Path
from decimal import Decimal, localcontext
from fractions import Fraction
from qoo157_bipe_options import OPTIONS
from qoo157_preprocess_compare import D4_RESULT
from gpmc_td_ablation import COMPLEX
from gpmc_vs_td_factorial import close_enough

CASE="qaoa7_neq"
OPTIONS_P8=("auto_default","manual_sharp","auto_no_vivif")
PASSED="SAME_SOURCE_SAME_BINARY_PREPROC_ONLY_P8_SCIENCE_PASS_6_OF_6"

def execute(binary: Path, cnf: Path, variant: str, scope: str,
            dump: Path|None = None, timeout: int = 30):
    if variant not in OPTIONS_P8 or scope not in ("full","preproc_only"):
        raise ValueError("Unqualified configuration")
    env=os.environ.copy()
    env.pop("QOO157_PREPROC_ONLY",None)
    env.pop("QOO157_RESIDUAL_DUMP",None)
    if scope=="preproc_only":
        env["QOO157_PREPROC_ONLY"]="1"
    if dump is not None:
        dump.parent.mkdir(parents=True,exist_ok=True)
        env["QOO157_RESIDUAL_DUMP"]=str(dump.resolve())
    cp=subprocess.run([str(binary),"-i",str(cnf),*OPTIONS[variant]],
                      env=env,text=True,capture_output=True,timeout=timeout)
    if cp.returncode != 0:
        raise RuntimeError(f"Native failure {variant}/{scope} rc={cp.returncode}: {cp.stderr[-500:]}")
    counts=D4_RESULT.findall(cp.stdout)
    if scope=="full":
        if len(counts)!=1 or COMPLEX.fullmatch(counts[0].strip()) is None:
            raise ValueError("Missing/malformed full native complex WMC")
    else:
        if len(counts)!=0 or cp.stdout.count("c QOO157_PREPROC_ONLY_DONE")!=1:
            raise ValueError("Preproc-only still invoked counter, or marker is missing")
    return cp.stdout

def qualify(binary:Path,cnf:Path,source:Path,p7:Path,out:Path,dumps:Path):
    anchor=json.loads(source.read_text())
    prior=json.loads(p7.read_text())
    if anchor.get("complete") is not True or prior.get("status") != "COMPLETE_RESIDUAL_CONTENT_AUDIT_SCIENCE_PASS":
        raise ValueError("Historical source/P7 science reference incomplete")
    source_row=anchor["cases"][CASE]
    source_sha=hashlib.sha256(cnf.read_bytes()).hexdigest()
    if source_sha != source_row["same_cnf_sha256"] or source_sha != prior["cases"][CASE]["original_cnf_sha256"]:
        raise ValueError("Original source CNF SHA does not match both native references")
    if prior["d4_source_commit"]!="be15f91f3e9769e1f5cb175fa27e3eca3a1ea690":
        raise ValueError("P7 d4 upstream pin drift")
    obs=source_row["precision_pairs"]["38"]["observations"]["d4-38"]
    with localcontext() as ctx:
        ctx.prec=110
        reference=tuple(Decimal(Fraction(obs[k]).numerator)/Decimal(Fraction(obs[k]).denominator)
                        for k in ("real","imag"))
    report={"status":"INCOMPLETE","original_cnf_sha256":source_sha,
            "p7_source_sha":"6f1c7093c766424fb1b1fb6352f20bc89074d150",
            "d4_binary_sha256":hashlib.sha256(binary.read_bytes()).hexdigest(),
            "effective_decimal_digits":38,"gmp_bits":128,"timeout_per_science_invocation":30,
            "official_codspeed_only_for_timing":True,"comparison_requires_fixed_macro_runner_for_shipping":True,
            "variants":{}}
    out.parent.mkdir(parents=True,exist_ok=True)
    for v in OPTIONS_P8:
        row={}
        for scope in ("full","preproc_only"):
            dump=dumps/f"{CASE}_{v}_{scope}.residual"
            stdout=execute(binary,cnf,v,scope,dump=dump)
            raw_sha=hashlib.sha256(dump.read_bytes()).hexdigest()
            expected=prior["cases"][CASE]["variants"][v]["residual_dump_sha256"]
            if raw_sha!=expected:
                raise ValueError(f"Native residual from new binary differs from P7: {v}/{scope}")
            result={"raw_residual_sha256":raw_sha,"source_p7_raw_sha_match":True,
                    "stdout_sha256":hashlib.sha256(stdout.encode()).hexdigest()}
            if scope=="full":
                s=D4_RESULT.findall(stdout)[0]
                m=COMPLEX.fullmatch(s.strip())
                value=tuple(Decimal(n) for n in m.groups())
                ok,delta,bound=close_enough(value,reference)
                if not ok: raise ValueError(f"Full complex-count science fail: {v}: {delta}>{bound}")
                result.update({"count":[str(n) for n in value], "count_scale_delta":delta,
                               "science":"COUNT_CONCORDANT_UNCERTIFIED"})
            else:
                result["preproc_only_counter_skipped"]=True
            row[scope]=result
            report["variants"][v]=row
            out.write_text(json.dumps(report,indent=2)+"\n")
        if row["full"]["raw_residual_sha256"] != row["preproc_only"]["raw_residual_sha256"]:
            raise ValueError("Paired preproc/full native residuals differ")
    if len({report["variants"][v]["full"]["raw_residual_sha256"] for v in OPTIONS_P8})!=1:
        raise ValueError("QAOA7 three candidate option residuals no longer byte-identical")
    report["status"]=PASSED
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":PASSED,"source_sha256":source_sha,
                      "binary_sha256":report["d4_binary_sha256"],
                      "shared_residual_sha256":report["variants"]["auto_default"]["full"]["raw_residual_sha256"]}))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for a in ("binary","cnf","source","p7","out","dumps"):
        p.add_argument("--"+a,type=Path,required=True)
    x=p.parse_args()
    qualify(x.binary,x.cnf,x.source,x.p7,x.out,x.dumps)

"""QOO-98 small source-semantic same-weighted-CNF Ganak Mode6 screen.

SCIENCE-ONLY: not CodSpeed and not a 38-digit output-precision certificate.
The native Ganak weight grammar differs from GPMC pair weights. Preserve
the exact Decimal components and Boolean clause text; never edit solver code.
"""
from __future__ import annotations
from decimal import Decimal,localcontext
from fractions import Fraction
from hashlib import sha256
import argparse,json,re,subprocess
from pathlib import Path
from native_print_admission import EXE_SHA,UPSTREAM,MODE6

CASES=("qaoa7_neq","qft16_eq")
STATUS="GANAK_QOO98_ORIGINAL_SEMANTIC_CNF_OUTPUT_SCREEN_PASS"


def convert(raw:bytes):
    lines=raw.decode().splitlines()
    if not lines or not re.fullmatch(r"p cnf \d+ \d+",lines[0]):
        raise ValueError("unrecognized source CNF")
    new=[];clauses=[];weights=[]
    nweights=0
    for line in lines:
        chunks=line.split()
        if not chunks:continue
        if chunks[:3]==["c","p","weight"]:
            if len(chunks)!=7 or chunks[-1]!="0":
                raise ValueError("unsupported source weight line")
            lit,r,i,zero=chunks[3:]
            if int(lit)==0:raise ValueError("invalid literal")
            real,imag=Decimal(r),Decimal(i)
            if not real.is_finite() or not imag.is_finite():
                raise ValueError("non-finite source weight")
            weight_text=r+("+" if imag>=0 else "-")+(
                i if imag>=0 else i.lstrip("-"))+"i"
            new.append("c p weight "+lit+" "+weight_text+" 0")
            weights.append((int(lit),str(real),str(imag)))
            nweights+=1
        elif chunks[:3]==["c","t","wmc"]:
            if chunks!=["c","t","wmc"]:raise ValueError("unexpected weighted marker")
            new.append(line)
        elif chunks[0]=="c":
            raise ValueError("unrecognized metadata "+line[:100])
        elif chunks[0]=="p":
            if line!=lines[0]:raise ValueError("duplicate header")
            new.append(line)
        else:
            if chunks[-1]!="0":raise ValueError("bad clause")
            clauses.append(line)
            new.append(line)
    if nweights<=0:raise ValueError("source must be weighted")
    header=lines[0].split()
    if len(clauses)!=int(header[3]):raise ValueError("source clause count")
    return ("\n".join(new)+"\n").encode(),{
        "clause_lines_byteidentical":True,"clause_lines_count":len(clauses),
        "source_signed_weight_entries":nweights,
        "source_weighted_variable_count":len(set(abs(x[0]) for x in weights)),
        "component_decimal_strings_preserved":True,
        "all_components_finite":True,
        "bool_clause_multiset_sha256":sha256(("\n".join(clauses)+"\n").encode()).hexdigest()
    }


def examine(binary:Path,source_dir:Path,report_path:Path,outdir:Path,out:Path):
    digest=sha256(binary.read_bytes()).hexdigest()
    if digest!=EXE_SHA:raise ValueError("Ganak binary changed or unpinned")
    ver=subprocess.run([str(binary),"--version"],capture_output=True,text=True,
                       timeout=10,check=False)
    if ver.returncode or UPSTREAM not in ver.stdout:raise ValueError("embedded SHA mismatch")
    reference=json.loads(report_path.read_text())
    if reference.get("complete") is not True:raise ValueError("archived report incomplete")
    report={"status":"INCOMPLETE","source_artifact_id":13317939531,
        "ganak_release_executable_sha256":digest,"ganak_mode":6,
        "ganak_requested_internal_MPFR_bits":127,
        "ganak_printed_significant_digits":9,
        "purpose":"same semantic CNF short boundary screen, untimed",
        "not_38digit_arithmetic_certificate":True,
        "internal_error_not_bounded":True,
        "cases":{}}
    for case in CASES:
        orig=source_dir/(case+".cnf")
        raw=orig.read_bytes()
        sha=sha256(raw).hexdigest()
        a=reference["cases"][case]
        if sha!=a["same_cnf_sha256"]:
            raise ValueError("original source CNF SHA differs from archive")
        ganak_cnf,proof=convert(raw)
        outdir.mkdir(parents=True,exist_ok=True)
        path=outdir/(case+".cnf")
        path.write_bytes(ganak_cnf)
        reference_gpmc=a["precision_pairs"]["38"]["observations"]["gpmc-38"]
        if reference_gpmc["status"]!="COMPLETED":raise ValueError("GPMC38 ref incomplete")
        with localcontext() as ctx:
            ctx.prec=125
            expected={k:Decimal(Fraction(reference_gpmc[k]).numerator)/
                        Decimal(Fraction(reference_gpmc[k]).denominator)
                      for k in ("real","imag")}
        cp=subprocess.run([str(binary),"--mode=6","--mpfrprec=127",
            str(path)],capture_output=True,text=True,timeout=48,check=False)
        if cp.returncode:raise ValueError(f"{case} native Ganak returned {cp.returncode}: {cp.stderr[:220]}")
        m=MODE6.findall(cp.stdout)
        matches=list(MODE6.finditer(cp.stdout))
        if len(matches)!=1:raise ValueError(f"{case} no unique 9digit Mode6 complex line")
        x=matches[0]
        if x["dtype"]!="quadruple float":raise ValueError("127bit mode6 class mismatch")
        result={}
        for part in ("real","imag"):
            printed=x[part]
            actual=Decimal(printed)
            exponent=int(printed.split("e")[1])
            unit=Decimal(1).scaleb(exponent-8)
            diff=abs(actual-expected[part])
            if diff>unit:
                report["cases"][case]={"status":"CENSORED_OUTPUT_DISAGREEMENT",
                    "component":part,"printed":printed,
                    "difference":str(diff),"print_step":str(unit)}
                out.parent.mkdir(parents=True,exist_ok=True)
                out.write_text(json.dumps(report,indent=2)+"\n")
                raise ValueError(f"{case}/{part}: parsed value differs by >1 printed ULP")
            result[part]={"printed":printed,
                          "source_GPMC38_decimal_reference":str(expected[part]),
                          "abs_delta":str(diff),"ganak_printed_step":str(unit),
                          "print_only_concordant":True}
        report["cases"][case]={
            "status":"PRINT_CONCORDANT_UNCERTIFIED",
            "original_weighted_cnf_sha256":sha,
            "converted_ganak_cnf_sha256":sha256(ganak_cnf).hexdigest(),
            "same_semantic_source_weights_and_clauses":proof,
            "ganak_complex_output":x.group(0),
            "ganak_native_status":next((l for l in cp.stdout.splitlines()
                                      if l.startswith("s ")),None),
            "components":result,
            "stdout_sha256":sha256(cp.stdout.encode()).hexdigest()
        }
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,indent=2)+"\n")
    report["status"]=STATUS
    out.write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("binary","original-cnfs","source-report","ganak-cnfs","out"):
        p.add_argument("--"+k,required=True,type=Path)
    a=p.parse_args()
    res=examine(a.binary,a.original_cnfs,a.source_report,a.ganak_cnfs,a.out)
    print(json.dumps({"status":res["status"],"cases":list(res["cases"])}))

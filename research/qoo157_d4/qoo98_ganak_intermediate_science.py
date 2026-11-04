"""QOO-98 Ganak Arjun/Puura intermediate CNF read-only structural science.

Reads pinned original QuPRS weighted-CNF provenance, invokes *unchanged*
official Ganak 2.8.0 with --arjundebugcnf. This output is UNTRUSTED AS A
WEIGHT-PRESERVING RESIDUAL until independent complex WMC certification.
No performance timing, no upstream modifications, no solver ranking.
"""
from __future__ import annotations
import argparse, json, os, re, subprocess
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from qoo98_ganak_native_mode6_admission import OUTPUT, compare

CASES={
  "qaoa7_neq": (("arjun1_puura1",1,1),
               ("arjun1_puura0",1,0),
               ("arjun0_puura0",0,0)),
  "qft16_eq": (("arjun1_puura1",1,1),
               ("arjun0_puura0",0,0)),
}

def digest(data): return sha256(data).hexdigest()

def structural_fingerprint(path:Path):
    """Syntactic only: a header, clauses, support comment, and hashes.

    Never treats projected support or literal weights as already preserved.
    """
    raw=path.read_bytes()
    lines=raw.decode("utf-8",errors="replace").splitlines()
    res={"sha256":digest(raw),"bytes":len(raw),
         "unverified_as_weighted_residual":True}
    headers=[l.split() for l in lines if l.startswith("p cnf ")]
    if len(headers)!=1 or len(headers[0])!=4:
        res["parse"]="NO_UNIQUE_P_CNF_HEADER"
        res["first_lines"]=lines[:12]
        return res
    n,c=int(headers[0][2]),int(headers[0][3])
    clauses=[];used=set();unusual=[]
    for l in lines:
        s=l.strip()
        if not s or s.startswith("c") or s.startswith("p "):continue
        bits=s.split()
        if not bits or bits[-1]!="0":
            unusual.append(s[:100]);continue
        try:
            signed=list(map(int,bits[:-1]))
        except ValueError:
            unusual.append(s[:100]);continue
        clauses.append(signed)
        used.update(abs(v) for v in signed if v)
    # Arjun's debug file is not an ordinary standalone WMC instance.
    # In particular, the original count may require an extra multiplicative
    # factor, and red clauses are serialized as comments. Preserve the raw
    # provenance; do not silently replay this file with another solver.
    weights=[l for l in lines if l.startswith("c p weight ")]
    multiplier=[l for l in lines if l.startswith("c MUST MULTIPLY BY ")]
    redundant=[l for l in lines if l.startswith("c red ")]
    projections=[l for l in lines if l.startswith(
        ("c p show ","c p optshow ","c p exist "))]
    res.update({
        "header_vars":n,"header_clauses":c,"observed_clauses":len(clauses),
        "active_clause_variables":len(used),
        "literals":sum(map(len,clauses)),
        "units":sum(len(x)==1 for x in clauses),
        "binary":sum(len(x)==2 for x in clauses),
        "empty_clauses":sum(not x for x in clauses),
        "native_weight_comment_lines":len(weights),
        "weight_lines_sha256":digest(("\n".join(weights)+"\n").encode()),
        "multiplier_comment_count":len(multiplier),
        "multiplier_comment_examples":multiplier[:2],
        "multiplier_lines_sha256":digest(("\n".join(multiplier)+"\n").encode()),
        "redundant_clause_comment_count":len(redundant),
        "projection_lines_sha256":digest(("\n".join(projections)+"\n").encode()),
        "projection_comment_lines":[l[:200] for l in lines
                 if l.startswith(("c ind ","c p show ","c p optshow ","c p exist "))][:15],
        "debug_dump_stage":"GANAK_POST_REMOVE_EQUIV_WEIGHTS",
        "debug_dump_is_not_replay_certified":True,
        "other_comment_examples":[l[:200] for l in lines if l.startswith("c ")][:15],
        "unexpected_clause_lines":unusual[:8],
        "parse":"HEADER_AND_CLAUSE_SYNTAX_ONLY"
    })
    if len(clauses)!=c or unusual or any(v>n for v in used):
        res["parse"]="INCOMPLETE_SYNTAX_DO_NOT_COMPARE"
    return res

def source(case,science,report,source_dir,adapted_dir):
    saved=report["source_cases"][case]
    original=source_dir/(case+".cnf")
    adapted=adapted_dir/("original_"+case+".cnf")
    assert digest(original.read_bytes())==saved["source_sha256"]
    assert digest(original.read_bytes())==science["cases"][case]["same_cnf_sha256"]
    assert digest(adapted.read_bytes())==saved["serialization"]["ganak_dialect_sha256"]
    anchor=science["cases"][case]["precision_pairs"]["38"]["observations"]["gpmc-38"]
    with localcontext() as ctx:
        ctx.prec=110
        expected=tuple(Decimal(Fraction(anchor[k]).numerator)/
            Decimal(Fraction(anchor[k]).denominator) for k in ("real","imag"))
    return original,adapted,expected

def run(binary,case,variant,arjun,puura,adapted,expected,root):
    output=root/case
    output.mkdir(parents=True,exist_ok=True)
    debug=output/(variant+".debug.cnf")
    stdout_file=output/(variant+".stdout.log")
    stderr_file=output/(variant+".stderr.log")
    cmd=[str(binary),"--mode=6","--mpfrprec=127","--threads=1",
         "--arjun",str(arjun),"--puura",str(puura),
         "--verb","1","--arjundebugcnf",str(debug),str(adapted)]
    rec={"case":case,"variant":variant,"arjun":arjun,"puura":puura,
         "requested_mpfr_bits":127,"threads":1,
         "binary_sha256":digest(binary.read_bytes()),
         "source_ganak_dialect_sha256":digest(adapted.read_bytes()),
         "intermediate_is_not_semantically_certified":True,
         "timing_disallowed":True}
    try:
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=32,check=False)
        stdout_file.write_text(cp.stdout);stderr_file.write_text(cp.stderr)
        rec["returncode"]=cp.returncode
        rec["stdout_sha256"]=digest(cp.stdout.encode())
        rec["stderr_sha256"]=digest(cp.stderr.encode())
        rec["trace_indicators"]=[l[:300] for l in cp.stdout.splitlines()
            if any(w in l.lower() for w in
                   ("arjun t:","puura","sampl_var","sampling","indep",
                    "clauses","vars", "td width"))][:75]
        matches=[m for l in cp.stdout.splitlines() if
                 (m:=OUTPUT.fullmatch(l))]
        if cp.returncode or len(matches)!=1:
            rec["count_status"]="NATIVE_EXIT_OR_PRINT_ERROR"
            rec["count_matches"]=len(matches)
        else:
            d={"status":"COMPLETED","real":matches[0].group(1),
               "imag":matches[0].group(2)}
            x=compare(d,expected,large=True)
            rec["count_status"]=x["status"]
            rec["native_complex_count"]=[d["real"],d["imag"]]
            rec["print_components"]=x.get("components")
    except subprocess.TimeoutExpired as exc:
        rec["count_status"]="BOUNDED_TIMEOUT_NO_BENCHMARK"
        rec["timeout_seconds"]=32
        if isinstance(exc.stdout,bytes):stdout_file.write_bytes(exc.stdout)
        if isinstance(exc.stderr,bytes):stderr_file.write_bytes(exc.stderr)
    if debug.exists():
        rec["debug_structure"]=structural_fingerprint(debug)
    else:rec["debug_structure"]={"status":"DEBUG_DUMP_NOT_PRODUCED"}
    return rec

def audit(binary,archive,manifest,science,report,source_dir,adapted_dir,out):
    ss=sha256(binary.read_bytes()).hexdigest()
    pinned=report["official_binary_sha256"]
    assert ss==pinned,("unapproved Ganak binary",ss,pinned)
    assert report["status"]=="NATIVE_PRINT_SCREEN_PASS_PRECISION_LIMITED"
    assert science["complete"] is True
    assert all(case in report["source_cases"] for case in CASES)
    release=subprocess.run([str(binary),"--version"],text=True,capture_output=True,timeout=7)
    assert release.returncode==0 and "Ganak SHA1: b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281" in release.stdout
    data={"status":"INCOMPLETE","science_only":True,
          "binary_sha256":pinned,
          "source_archive":13317939531,
          "not_a_timing_experiment":True,
          "intermediate_complex_weight_semantics":"NOT_VERIFIED",
          "intermediate_projection_semantics":"NOT_VERIFIED",
          "cases":{}}
    out.mkdir(parents=True,exist_ok=True)
    result=out/"native-intermediate-audit.json"
    for case,arms in CASES.items():
        _,adapted,expected=source(case,science,report,source_dir,adapted_dir)
        for variant,arjun,puura in arms:
            rec=run(binary,case,variant,arjun,puura,adapted,expected,out)
            data["cases"].setdefault(case,{})[variant]=rec
            result.write_text(json.dumps(data,indent=2)+"\n")
    incomplete=[(case,arm) for case,arms in data["cases"].items()
                for arm,r in arms.items()
                if r["count_status"]!="PRINT_CONCORDANT_UNCERTIFIED"]
    data["status"]="ALL_FIVE_NATIVE_COUNT_SCREENS_CONCORDANT" if not incomplete else "INCOMPLETE_NATIVE_STAGE_EVIDENCE"
    data["non_admitted"]=incomplete
    result.write_text(json.dumps(data,indent=2)+"\n")
    return data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for opt in ("binary","source-science","native-report","source-dir","native-dir","out"):
        p.add_argument("--"+opt,type=Path,required=True)
    a=p.parse_args()
    science=json.loads(a.source_science.read_text())
    report=json.loads(a.native_report.read_text())
    x=audit(a.binary,None,None,science,report,a.source_dir,a.native_dir,a.out)
    print(json.dumps({"status":x["status"],
        "arms":{k:{n:{"count":r["count_status"],
                      "debug":r.get("debug_structure",{}).get("parse","NO_DEBUG")}
                      for n,r in v.items()} for k,v in x["cases"].items()}}))
    if x["status"]!="ALL_FIVE_NATIVE_COUNT_SCREENS_CONCORDANT":
        raise SystemExit(1)

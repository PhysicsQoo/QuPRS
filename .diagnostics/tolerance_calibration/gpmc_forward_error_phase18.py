#!/usr/bin/env python3
"""Research-only Phase 18: GPMC complex-DAG scope audit and semiring lifting.

Source scope:
  - fixed pinned GPMC commit; only mode=1 (non-projected WMC)
  - verifies the only scalar Complex arithmetic operators are audited + and *
  - direct .real/.imag mutation outside ComplexMPFR.cc is unsupported
  - external printer log10 does not contribute to computed WMC
  - symbolic Boolean SAT/learned-clause correctness is NOT formally proved

Native checks:
  - compare original and instrumented GPMC both on signed/complex weights and
    on the NONNEGATIVE L1-companion weights for identical fixed CNFs
  - exact Fraction enumerator independently verifies each transformed WMC
  - sample DAG q and MPFR exceptional flags in both cases
  - observed q <= 4*n+8 is exploratory, NOT a universal structural theorem.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
from collections import Counter
import subprocess
import tempfile

from exact_gpmc_cnf_oracle import count_printed_cnf_exact
from gpmc_native_phase15 import fixed_cases, random_cases, fixture, encode, read_solver
from gpmc_dag_exponent_probe import annotate, PROBE

GPMC_PIN = "a1bda3489e959d3695b6798d327c5a1fc1bed305"
FILES = ["core/Counter.cc","core/Component.h","core/ComponentManager.cc",
         "core/ComponentCache.cc","core/Instance.cc","preprocessor/Preprocessor.cc",
         "c-mpfr/ComplexMPFR.cc","core/Main.cc"]

CHECKS = {
    "preprocessing_scale": ("preprocessor/Preprocessor.cc",
        ["ins->gweight *=", "ins->lit_weights", "pickDefVars", "MergeAdjEquivs"]),
    "branch_weight": ("core/Component.h",
        ["branch_weight_ *= w", "models_[cur_branch_] *= branch_weight_",
         "models_[cur_branch_] *= nmodels", "return models_[0] + models_[1]"]),
    "conditional_branch": ("core/Counter.cc",
        ["cmpmgr.topDecision().mulLitsWeights()", "cmpmgr.topDecision().hasModel()",
         "cmpmgr.cacheModelCountOf", "npmodels = cmpmgr.topDecision().totalModels() * gweight"]),
    "cache_reuse": ("core/ComponentManager.cc",
        ["cache_.requestValueOf", "increaseModels(tmp_model_count, true)",
         "if(isPVar(v))"]),
    "weighted_input": ("core/Instance.cc",
        ["lit_weights[toInt(l)] = Complex(tokens[4], tokens[5])",
         "gweight =Complex(tokens[3], tokens[4])"]),
    "numeric_operators": ("c-mpfr/ComplexMPFR.cc",
        ["Complex Complex::operator+(", "Complex &Complex::operator+=(",
         "Complex Complex::operator*(", "Complex &Complex::operator*=(",
         "Complex Complex::operator<<(",
         "Complex &Complex::operator=(const int",
         "Complex &Complex::operator=(const std::string"]),
}


def source_audit(root:Path) -> dict:
    c=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],capture_output=True,text=True,check=True)
    if c.stdout.strip()!=GPMC_PIN:
        raise AssertionError("unverified native GPMC source identity")
    data={p:(root/p).read_text() for p in FILES}
    hits={}
    for name,(path,needles) in CHECKS.items():
        for word in needles:
            if data[path].count(word)!=1 and not (word in ("ins->lit_weights", "ins->gweight *=") and data[path].count(word)>1):
                raise AssertionError("source audit mismatch: "+name+" "+word+
                                     " count="+str(data[path].count(word)))
        hits[name]=True
    for name in ["core/Counter.cc","core/ComponentManager.cc","core/Component.h",
                 "preprocessor/Preprocessor.cc","core/Instance.cc"]:
        # No bypass via direct component mutation in active solver core.
        # No regex against "double" or SAT heuristics, which are not Complex.
        import re
        bypass=re.findall(r"(?<![a-zA-Z_])\w+\.(?:real|imag)\b",data[name])
        if bypass:
            raise AssertionError("untracked direct Complex component access: "+
                                 name+" "+repr(bypass))
    if "mpfr::log10" not in data["core/Main.cc"]:
        raise AssertionError("printer diagnostic path moved")
    return {
        "gpmc_git_commit":GPMC_PIN,
        "checks":hits,
        "source_file_sha256":{p:sha256(data[p].encode()).hexdigest() for p in FILES},
        "arithmetic_source_syntactically_covered":True,
        "universal_semiring_correctness_proven":False,
        "complete_solver_forward_error_certified":False,
        "open_assumptions":["SAT/BCP/learned clauses model soundness",
                            "weighted preprocessing preserves nonnegative companion",
                            "cache identity and component decomposition",
                            "MPFR normal nearest with all intermediate exponent flags",
                            "source-to-MPFR quantization and decimal printer bounds"],
    }


def l1_case(case):
    result=fixture(case["name"]+"-positive-companion",
                   case["n"],case["clauses"])
    for orig,tag in ((case["positive"],"positive"),(case["negative"],"negative")):
        dest=result[tag]
        for v in range(1,case["n"]+1):
            x,y=orig.get(v,(1,0))
            dest[v]=(abs(x)+abs(y),0)
    return result


def once(exe:Path, cnf:Path, prefix:Path, flags:tuple):
    cmd=[str(exe),"-mode=1","-prec=90","-cs=16",*flags,str(cnf)]
    cp=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
    prefix.with_suffix(".stdout").write_text(cp.stdout)
    prefix.with_suffix(".stderr").write_text(cp.stderr)
    if cp.returncode:
        raise RuntimeError(f"Native GPMC exit={cp.returncode}: {cnf.name}: {cp.stderr[-900:]}")
    val,sat,_=read_solver(cp.stdout)
    matches=PROBE.findall(cp.stderr)
    if len(matches)>1:
        raise AssertionError("duplicate native q evidence")
    return {"value":val, "sat":sat,
            "trace":list(map(int,matches[0])) if matches else None}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--gpmc-source",required=True,type=Path)
    p.add_argument("--baseline",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--random",type=int,default=40)
    a=p.parse_args()
    out=a.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    audit=source_audit(a.gpmc_source.resolve())
    (out/"source-audit.json").write_text(json.dumps(audit,indent=2)+"\n")
    records=[]
    stats=Counter()
    with tempfile.TemporaryDirectory(prefix="gpmc-p18-") as d:
        base=Path(d)
        src=base/"gpmc"
        annotate(a.gpmc_source.resolve(),src)
        for label,cmd in [
            ("configure",["cmake","-S",str(src),"-B",str(base/"build"),"-DCMAKE_BUILD_TYPE=Release"]),
            ("build",["cmake","--build",str(base/"build"),"-j","4"]),
        ]:
            cp=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
            (out/(label+".stdout")).write_text(cp.stdout)
            (out/(label+".stderr")).write_text(cp.stderr)
            if cp.returncode:
                raise RuntimeError(f"native instrumented {label}: "+cp.stderr[-2000:])
        measured=base/"build/gpmc"
        audit["native_probe_sha256"]=sha256(measured.read_bytes()).hexdigest()
        audit["baseline_sha256"]=sha256(a.baseline.read_bytes()).hexdigest()
        for case in fixed_cases()+random_cases(a.random):
            for flavor,instance in [("original",case),("positive-companion",l1_case(case))]:
                text=encode(instance)
                path=out/(instance["name"]+".cnf")
                path.write_text(text)
                oracle=count_printed_cnf_exact(text)
                if oracle["status"]!="observed":
                    raise AssertionError("exact oracle skipped")
                exact=(oracle["real"],oracle["imag"])
                sat=oracle["satisfying_assignments"]>0
                for mode,flags in [("default",()),("preproc-mainloop-off",("-varlim=0",))]:
                    prefix=instance["name"]+"-"+mode
                    b=once(a.baseline.resolve(),path,out/(prefix+"-baseline"),flags)
                    q=once(measured,path,out/(prefix+"-instrumented"),flags)
                    if not (b["value"]==q["value"]==exact and b["sat"]==q["sat"]==sat):
                        raise AssertionError("native semiring mismatch "+prefix)
                    if not q["trace"]:
                        raise AssertionError("instrumented root q absent "+prefix)
                    amp,pbits,uf,of,nan,erange=q["trace"]
                    if (uf,of,nan,erange)!=(0,0,0,0):
                        raise AssertionError("nonfinite MPFR trace "+prefix)
                    if pbits!=299:
                        raise AssertionError("unexpected native precision "+prefix)
                    row={
                        "case":case["name"],"flavor":flavor,
                        "mode":mode,"q":amp,"n":case["n"],"p":pbits,
                        "native_vs_exact_fraction_pass":True,
                        "cnf_sha256":sha256(text.encode()).hexdigest(),
                        "tested_q_le_4n_plus_8":amp<=4*case["n"]+8,
                    }
                    records.append(row)
                    stats["native_solver_executions"]+=2
                    stats["tested_q_conjecture_failures"]+=int(not row["tested_q_le_4n_plus_8"])
                    stats["max_q"]=max(stats["max_q"],amp)
                    if not row["tested_q_le_4n_plus_8"]:
                        print("P18_Q_STRUCTURAL_CONJECTURE_COUNTEREXAMPLE "+
                              json.dumps(row),flush=True)
        stats["unique_original_cases"]=len(fixed_cases())+a.random
        stats["native_comparison_pairs"]=len(records)
    (out/"source-audit.json").write_text(json.dumps(audit,indent=2)+"\n")
    report={
        "status":"PASS_NATIVE_SAMPLED_SEMIRING_AND_OPERATION_COVERAGE",
        "audit":audit,
        "statistics":dict(stats),
        "cases":records,
        "structural_q_4n_plus_8_is_proven":False,
        "universal_WMC_semiring_equivalence_proven":False,
        "no_production_gpmc_changes":True,
    }
    (out/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
    print("P18_SOURCE_SEMIRING_SUMMARY "+
          json.dumps({"status":report["status"],"statistics":report["statistics"],
                      "q_4n_plus_8_proven":False,
                      "universal_WMC_proven":False},sort_keys=True),flush=True)


if __name__=="__main__":
    main()

"""QOO-157 P1: pinned BiPe v1.0.0 native work counters, no speed timing.

The pinned upstream BiPe PreprocStats prints a native 'c [STATS]' line
only if --preproc.verbosity=3. This option also computes degeneracy, so
do NOT compare the diagnostic invocation's process or internal t_total
against official CodSpeed without instrumentation. We parse and preserve
only structural work counts; ignore diagnostic t_total.
"""
from __future__ import annotations
from decimal import Decimal,localcontext
from fractions import Fraction
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
import subprocess

from gpmc_td_ablation import COMPLEX
from qoo157_preprocess_compare import D4_RESULT
from qoo157_bipe_options import OPTIONS
from gpmc_vs_td_factorial import close_enough

CASES=("qaoa7_neq","qft16_eq")
STAT_RE=re.compile(r"(?m)^c \[STATS\]\s+(.+)$")
FIELDS=("method","vars","cls","lits","proj","tw","gates","elim",
        "bip_input","bva")


def observe(binary:str,cnf:Path,variant:str):
    if variant not in OPTIONS:raise ValueError("unsupported")
    proc=subprocess.run(
        [binary,"-i",str(cnf),*OPTIONS[variant],"--preproc.verbosity=3"],
        capture_output=True,text=True,timeout=40,check=False)
    if proc.returncode:
        raise RuntimeError(f"BiPe stats {variant}: rc={proc.returncode}: {proc.stderr[:350]}")
    matches=D4_RESULT.findall(proc.stdout)
    if len(matches)!=1:raise ValueError("one native complex count required")
    parsed=COMPLEX.fullmatch(matches[0].strip())
    if not parsed:raise ValueError("bad printed complex count")
    count=tuple(Decimal(x) for x in parsed.groups())
    if not all(x.is_finite() for x in count):raise ValueError("non-finite")
    stats=STAT_RE.findall(proc.stdout)
    if len(stats)!=1:
        raise ValueError(f"expected exactly one upstream BiPe v1.0.0 STATS line: {stats}")
    pairs=dict(t.split("=",1) for t in stats[0].split())
    if not all(k in pairs for k in FIELDS+("t_total",)):
        raise ValueError("native STATS fields missing")
    # Stats emitted under verbosity>=3, and its estimation of TW adds
    # diagnostic work. Never reuse native t_total as performance proof.
    meta={k:pairs[k] for k in FIELDS}
    if variant=="none" and meta["method"]!="none":
        raise ValueError("none mode did not select none preprocessing")
    if variant!="none" and meta["method"]!="sharp-equiv":
        raise ValueError("BiPe expected sharp-equiv for active modes")
    if "->" not in meta["vars"] or "->" not in meta["cls"]:
        raise ValueError("incomplete formula dimensions")
    return {
        "complex_printed_real":str(count[0]),
        "complex_printed_imag":str(count[1]),
        "native_stats_without_t_total":meta,
        "diagnostic_t_total_discarded":True,
        "native_stdout_sha256":sha256(proc.stdout.encode()).hexdigest(),
        "cli_flags":[*OPTIONS[variant],"--preproc.verbosity=3"]
    }


def audit(binary:Path,cnf_dir:Path,source_report:Path,out:Path):
    source=json.loads(source_report.read_text())
    if source.get("complete") is not True:
        raise ValueError("original science archive missing")
    result={
        "status":"INCOMPLETE",
        "pinned_d4_upstream":"be15f91f3e9769e1f5cb175fa27e3eca3a1ea690",
        "pinned_bipe_commit":"219cc2a5f15a563e1965e5a5137f0fbadf0d166f",
        "d4_research_binary_sha256":sha256(binary.read_bytes()).hexdigest(),
        "effective_decimal_digits":38,"actual_gmp_bits":128,
        "no_codspeed_no_performance_ranking":True,
        "BiPe_diagnostic_verbosity_adds_TW_work":True,
        "cases":{}
    }
    for case in CASES:
        orig=cnf_dir/(case+".cnf")
        digest=sha256(orig.read_bytes()).hexdigest()
        e=source["cases"][case]
        if digest!=e["same_cnf_sha256"]:
            raise ValueError("original source SHA mismatched")
        obs=e["precision_pairs"]["38"]["observations"]["d4-38"]
        with localcontext() as c:
            c.prec=110
            anchor=tuple(Decimal(Fraction(obs[k]).numerator)/
                         Decimal(Fraction(obs[k]).denominator)
                         for k in ("real","imag"))
        row={"source_cnf_sha256":digest,"variants":{}}
        result["cases"][case]=row
        for variant in OPTIONS:
            o=observe(str(binary),orig,variant)
            ok,delta,bound=close_enough((
                Decimal(o["complex_printed_real"]),
                Decimal(o["complex_printed_imag"])),anchor)
            o["count_screen_status"]="COUNT_CONCORDANT_UNCERTIFIED" if ok else "FAILED"
            o["count_screen_delta"]=delta
            o["count_screen_bound"]=bound
            row["variants"][variant]=o
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(json.dumps(result,indent=2)+"\n")
            if not ok:raise ValueError(f"native statistics mode count changed: {case}/{variant}")
    result["status"]="BIPe_V100_PINNED_NATIVE_STATS_COUNT_SCREEN_PASS"
    out.write_text(json.dumps(result,indent=2)+"\n")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--binary",type=Path,required=True)
    p.add_argument("--cnf-dir",type=Path,required=True)
    p.add_argument("--original-science",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=audit(a.binary,a.cnf_dir,a.original_science,a.out)
    print(json.dumps({"status":result["status"],
        "cases":{c:{v:obs["native_stats_without_t_total"] for v,obs in r["variants"].items()}
                 for c,r in result["cases"].items()}}))

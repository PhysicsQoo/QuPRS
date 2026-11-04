"""QOO-157 P1: native BiPe v1.0.0 untimed counters versus same residual hash.

Do NOT treat t_total printed by BiPe as a performance benchmark.
Verbosity3 incurs extra degeneracy computations and may change behavior.
Only official CodSpeed v5 can provide performance comparisons.
"""
from __future__ import annotations
import argparse
from decimal import Decimal,localcontext
from fractions import Fraction
from hashlib import sha256
import json, os
from pathlib import Path
import re
import subprocess

from qoo157_bipe_options import OPTIONS
from qoo157_d4_residual_identity import parse_formula
from qoo157_preprocess_compare import D4_RESULT
from gpmc_td_ablation import COMPLEX
from gpmc_vs_td_factorial import close_enough

CASES=("qaoa7_neq","qft16_eq")
VARIANTS=("auto_default","manual_sharp","auto_no_vivif","auto_no_probing")
STATUS="P1_BIPE_V1_PINNED_STATS_AND_RESIDUAL_SCIENCE_PASS"
STAT=re.compile(
    r"^c \\[STATS\\] method=(\\S+) "
    r"vars=(\\d+)->(\\d+) cls=(\\d+)->(\\d+) "
    r"lits=(\\d+)->(\\d+) proj=(\\d+)->(\\d+) "
    r"tw=(-?\\d+)->(-?\\d+) "
    r"gates=(-?\\d+)/(-?\\d+)/(-?\\d+) "
    r"elim=(-?\\d+)g/(-?\\d+)r "
    r"bip_input=(-?\\d+) bva=(-?\\d+)/(-?\\d+) "
    r"t_total=([0-9.+eE-]+)$",
    re.MULTILINE
)
LABELS=("method","vars_in","vars_out","clauses_in","clauses_out",
        "literals_in","literals_out","projection_in","projection_out",
        "treewidth_degeneracy_in","treewidth_degeneracy_out",
        "and_or_gates","xor_gates","equiv_gates",
        "eliminated_gates","eliminated_resolution",
        "bipartition_input","bva_vars","bva_clauses_removed",
        "bipe_instrumented_t_total_unusable_for_performance")


def audit(binary:Path,cnfdir:Path,archive:Path,canonical:Path,output:Path,dumps:Path):
    a=json.loads(archive.read_text())
    prior=json.loads(canonical.read_text())
    if a.get("complete") is not True:
        raise ValueError("missing source count provenance")
    if prior.get("status")!="COMPLETE_RESIDUAL_CONTENT_AUDIT_SCIENCE_PASS":
        raise ValueError("missing independent native residual SHA reference")
    report={"status":"INCOMPLETE",
            "source_CNF_artifact":13317939531,
            "prior_residual_artifact":13329836269,
            "upstream_d4":"be15f91f3e9769e1f5cb175fa27e3eca3a1ea690",
            "bipe_v1_tag_commit":"219cc2a5f15a563e1965e5a5137f0fbadf0d166f",
            "binary_sha256":sha256(binary.read_bytes()).hexdigest(),
            "effective_decimal_digits":38,"gmp_actual_bits":128,
            "P1_not_timing":True,
            "verbosity3_has_extra_degeneracy_work":True,
            "no_ad_hoc_time_comparison":True,
            "cases":{}}
    for case in CASES:
        file=cnfdir/(case+".cnf")
        sha=sha256(file.read_bytes()).hexdigest()
        expected=a["cases"][case]
        if sha!=expected["same_cnf_sha256"] or sha!=prior["cases"][case]["original_cnf_sha256"]:
            raise ValueError("source CNF sha changed")
        p=expected["precision_pairs"]["38"]["observations"]["d4-38"]
        if p["status"]!="COMPLETED":raise ValueError("source d4-38 count not admitted")
        with localcontext() as ctx:
            ctx.prec=120
            ref=tuple(Decimal(Fraction(p[x]).numerator)/Decimal(Fraction(p[x]).denominator)
                      for x in ("real","imag"))
        row={"cnf_sha256":sha,"variants":{}}
        report["cases"][case]=row
        for variant in VARIANTS:
            outfile=dumps/(case+"_"+variant+".residual")
            outfile.parent.mkdir(parents=True,exist_ok=True)
            env=os.environ.copy()
            env["QOO157_RESIDUAL_DUMP"]=str(outfile.resolve())
            cp=subprocess.run([str(binary),"-i",str(file),*OPTIONS[variant],
                                "--preproc.verbosity=3"],
                               env=env,capture_output=True,text=True,
                               check=False,timeout=45)
            if cp.returncode:raise ValueError(f"{case}/{variant}: rc={cp.returncode} {cp.stderr[:300]}")
            matches=D4_RESULT.findall(cp.stdout)
            if len(matches)!=1:raise ValueError(f"{case}/{variant}: multiple or no complex counts")
            m=COMPLEX.fullmatch(matches[0].strip())
            if m is None:raise ValueError(f"{case}/{variant}: unparsable complex count")
            count=(Decimal(m.group(1)),Decimal(m.group(2)))
            if not all(x.is_finite() for x in count):raise ValueError("nonfinite WMC")
            ok,delta,threshold=close_enough(count,ref)
            if not ok:raise ValueError(f"{case}/{variant}: complex WMC changed: {delta}>{threshold}")
            lines=STAT.findall(cp.stdout)
            if len(lines)!=1:raise ValueError(f"{case}/{variant}: must have exactly one BiPe v1 STATS line")
            vals=dict(zip(LABELS,lines[0]))
            # Do not put t_total in metrics to be compared or ranked.
            _discarded=vals.pop("bipe_instrumented_t_total_unusable_for_performance")
            vals={k:(v if k=="method" else int(v)) for k,v in vals.items()}
            if vals["method"]!="sharp-equiv":raise ValueError("BiPe method unexpectedly changed")
            if not outfile.is_file():raise ValueError("source residual not saved")
            payload=outfile.read_bytes()
            parsed=parse_formula(payload)
            previous=prior["cases"][case]["variants"][variant]
            if parsed["canonical_combined_sha256"]!=previous["canonical"]["canonical_combined_sha256"]:
                raise ValueError(f"{case}/{variant}: native formula differs from archival baseline")
            if sha256(payload).hexdigest()!=previous["residual_dump_sha256"]:
                raise ValueError(f"{case}/{variant}: native residual byte dump changes under verbose3")
            row["variants"][variant]={
                "flags":[*OPTIONS[variant],"--preproc.verbosity=3"],
                "native_preproc_stats":vals,
                "residual_sha256":sha256(payload).hexdigest(),
                "canonical_clause_multiset_sha256":parsed["canonical_clause_multiset_sha256"],
                "canonical_combined_sha256":parsed["canonical_combined_sha256"],
                "source_complex_count_screen":"COUNT_CONCORDANT_UNCERTIFIED",
                "count_real":str(count[0]),"count_imag":str(count[1]),
                "count_delta":delta,"count_threshold":threshold,
                "stdout_sha256":sha256(cp.stdout.encode()).hexdigest()
            }
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(report,indent=2)+"\\n")
        canonical_hashes={x["canonical_combined_sha256"] for x in row["variants"].values()}
        raw_hashes={x["residual_sha256"] for x in row["variants"].values()}
        if len(canonical_hashes)!=1 or len(raw_hashes)!=1:
            raise ValueError(case+": supposedly identical source formula variants actually differ")
        row["canonical_and_byte_identical_in_four_options"]=True
    report["status"]=STATUS
    output.write_text(json.dumps(report,indent=2)+"\\n")
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for k in ("binary","cnf-dir","source-science","canonical-reference","out","dump-dir"):
        parser.add_argument("--"+k,type=Path,required=True)
    x=parser.parse_args()
    result=audit(x.binary,x.cnf_dir,x.source_science,x.canonical_reference,x.out,x.dump_dir)
    print(json.dumps({"status":result["status"],
        "case_summary":{c:{v:r["native_preproc_stats"] for v,r in x["variants"].items()}
                        for c,x in result["cases"].items()}}))

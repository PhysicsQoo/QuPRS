"""Research-only same-process GPMC complex-operation accounting and controlled A/B.

The solver is still called exactly once per experimental trial; a
scratch, uncommitted, source-identical GPMC copy gets *only* four
operator counters. No code in public QuPRS/dev/main or the pinned
Gitlink is modified. An operation-count-based roundoff estimate is
CONDITIONAL on the remaining GPMC implementation/MPFR proof
obligations and is NOT a production numerical certificate.
"""
from __future__ import annotations
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import statistics
import subprocess
import time
import tempfile

PINNED_CASES={
"qpeexact8-baseline":("34d38d1718f1796d6af46cfa079aa2093aa00e5997f5b428e8af4b1672a35ee7",11,17,22),
"qpeexact8-self_negative":("b965d82a7bf4900350a2cbef028ff51506b9bb0f426859c1be9432207872d2d7",8,2,16),
"qft16-baseline":("20ee9e55eb1fc644d08daf130d180ded46f06f67897fa46f57b4f4ef4ef7f8f1",70,400,102),
"qft16-self_negative":("8e65b1d5cfdc99c4d980bc4fea24162afc4f9583e0ebf17686fc8a9f1bc6555c",64,385,96),
}
GPMC_PREFIX="c s exact double prec-sci "
ROUNDING_COEFFICIENT=16
MAX_WEIGHT_MAG=Fraction(1)+Fraction(1,2**40)
ORDER=(("baseline","probe"),("probe","baseline"),("baseline","probe"))

def fail(cmd,**opts):
    p=subprocess.run(cmd,text=True,capture_output=True,**opts)
    if p.returncode:raise RuntimeError(("command failed",cmd,p.returncode,p.stdout[-1200:],p.stderr[-1600:]))
    return p

def install_probe(original:Path):
    text=original.read_text()
    hdr='#include "mpfr/mpreal.h"\n'
    if text.count(hdr)!=1:raise RuntimeError("probe C++ header mismatch")
    declaration=(
        "#include <cstdio>\n#include <cstdint>\n"
        "static volatile std::uint64_t quprs_research_adds = 0;\n"
        "static volatile std::uint64_t quprs_research_multiplies = 0;\n"
        "struct QPRSResearchOperationReport {\n"
        "  ~QPRSResearchOperationReport() {\n"
        "    std::fprintf(stderr, \"QUPRS_RESEARCH_OPS adds=%llu muls=%llu prec_bits=%ld\\n\",\n"
        "      (unsigned long long)quprs_research_adds,\n"
        "      (unsigned long long)quprs_research_multiplies,\n"
        "      (long)mpfr::mpreal::get_default_prec());\n"
        "  }\n"
        "};\n"
        "static QPRSResearchOperationReport qprs_research_operation_report;\n"
    )
    text=text.replace(hdr,hdr+declaration)
    count={
        "Complex Complex::operator+(const Complex &v) const\n{":"quprs_research_adds",
        "Complex &Complex::operator+=(const Complex &v)\n{":"quprs_research_adds",
        "Complex Complex::operator*(const Complex &v) const\n{":"quprs_research_multiplies",
        "Complex &Complex::operator*=(const Complex &v)\n{":"quprs_research_multiplies",
    }
    for signature,counter in count.items():
        if text.count(signature)!=1:
            raise RuntimeError(("missing instrumentable Complex operator",signature))
        text=text.replace(signature,signature+"\n    ++"+counter+";")
    original.write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()


def full_count(stdout):
    values=[line[len(GPMC_PREFIX):].strip().replace(" ","")
            for line in stdout.splitlines() if line.startswith(GPMC_PREFIX)]
    if len(values)!=1:raise ValueError(("expected a unique weighted output",values[:2]))
    return values[0]


def inspect_cnf(path:Path,case):
    expect,exp_models,exp_m,twice=PINNED_CASES[case]
    contents=path.read_bytes()
    if hashlib.sha256(contents).hexdigest()!=expect:
        raise AssertionError(("CNF byte identity moved",case))
    weights={}
    for line in contents.decode().splitlines():
        a=line.split()
        if a[:3]==["c","p","weight"]:
            lit=int(a[3])
            if lit>0:
                if lit in weights:raise ValueError("duplicate phase")
                x=Fraction(Decimal(a[4]));y=Fraction(Decimal(a[5]))
                if x*x+y*y>MAX_WEIGHT_MAG*MAX_WEIGHT_MAG:
                    raise AssertionError(("unexpected magnitude",case,lit))
                weights[lit]=(x,y)
            else:
                if Fraction(Decimal(a[4]))!=1 or Fraction(Decimal(a[5]))!=0:
                    raise AssertionError(("negative phase weight not unity",case,lit))
    if len(weights)!=exp_m:raise AssertionError(("weight count moved",len(weights),exp_m))
    return 2**exp_models,len(weights),twice,expect


def source_bound(ops,p_bits,nsat,m,twice):
    # Conservative engineering *candidate*, NOT unconditional MPFR proof.
    # Candidate assumes:
    # - complete counting of all rounded arithmetic for a positive-semiring
    #   sum/product computation (cached DAG may re-use subresults);
    # - MPFR arithmetic and decimal parsing are correctly rounded at p bits
    #   and do not underflow/overflow;
    # - per-Complex sum/product error <= 16*2^-p times the exact
    #   absolute-value local polynomial (requires code-level proof);
    # - input-weight numeric error is paid once per positive literal;
    # - each satisfying assignment contributes a product of at most m weights,
    #   and Nsat is a proven upper bound for the CNF;
    # - normalization exponent is exact and meaningful.
    k=ops+m+1
    t=Fraction(ROUNDING_COEFFICIENT*k,2**p_bits)
    if t>=1:raise ArithmeticError("precision not sufficient for candidate")
    multiplier=t/(1-t)
    absolute=nsat*(MAX_WEIGHT_MAG**m)*multiplier
    norm=Fraction(2)**(twice//2)
    normalized=absolute/norm
    with localcontext() as ctx:
        ctx.prec=48
        display=format(Decimal(normalized.numerator)/Decimal(normalized.denominator),".18E")
    return {"candidate_normalized_count_error_radius":display,
            "hypothetical_rounding_constant":ROUNDING_COEFFICIENT,
            "operation_accounting_K":ops,
            "extra_positive_weight_parses":m,
            "candidate_rel_error":"gamma(K)=t/(1-t), t=16*(K+m+1)*2^-p",
            "certified_solver_arithmetic_error":False,
            "reason":"native GPMC operation-complete forward-error proof not established"}


def main(args):
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    source=args.gpmc_source
    if not (source/"c-mpfr/ComplexMPFR.cc").is_file():raise RuntimeError("GPMC source absent")
    scratch=Path(tempfile.mkdtemp(prefix="qprs-gpmc-accounting-",dir=str(out.parent))) / "GPMC"
    shutil.copytree(source,scratch,
        ignore=shutil.ignore_patterns(".git","build","bin","__pycache__"))
    flags=["cmake","-S",str(scratch),"-B",str(scratch/"build"),"-DCMAKE_BUILD_TYPE=Release"]
    original_source_sha=hashlib.sha256((scratch/"c-mpfr/ComplexMPFR.cc").read_bytes()).hexdigest()
    start=time.monotonic()
    fail(flags,timeout=70)
    fail(["cmake","--build",str(scratch/"build"),"-j","4"],timeout=180)
    baseline=out/"gpmc-baseline";shutil.copy2(scratch/"build"/"gpmc",baseline)
    modified_source_sha=install_probe(scratch/"c-mpfr/ComplexMPFR.cc")
    fail(["cmake","--build",str(scratch/"build"),"-j","4"],timeout=180)
    probed=out/"gpmc-probe";shutil.copy2(scratch/"build"/"gpmc",probed)
    builds=time.monotonic()-start
    samples=[];summaries=[]
    for case in PINNED_CASES:
        path=args.artifact_folder/(case+".cnf")
        nsat,m,twice,cnfhash=inspect_cnf(path,case)
        results=[]
        for index,order in enumerate(ORDER):
            for flavor in order:
                exe=baseline if flavor=="baseline" else probed
                call=["/usr/bin/time","-f","QUPRS_METRIC wall=%e rss_kb=%M",
                      str(exe),"-mode=1","-prec=90",str(path)]
                p=fail(call,timeout=35)
                label=f"{case}-{index}-{flavor}"
                (out/(label+".stdout")).write_text(p.stdout)
                (out/(label+".stderr")).write_text(p.stderr)
                stat=re.search(r"QUPRS_METRIC wall=([\d.]+) rss_kb=(\d+)",p.stderr)
                if not stat:raise AssertionError("GNU time metrics missing")
                count=full_count(p.stdout)
                row={"case":case,"flavor":flavor,"replicate":index,
                  "same_CNF_sha256":cnfhash,
                  "weighted_count_exact_print":count,
                  "wall_seconds":float(stat.group(1)),
                  "peak_rss_kb":int(stat.group(2))}
                if flavor=="probe":
                    found=re.findall(r"QUPRS_RESEARCH_OPS adds=(\d+) muls=(\d+) prec_bits=(\d+)",p.stderr)
                    if len(found)!=1:raise AssertionError(("native probe line missing",case))
                    adds,muls,prec=map(int,found[0])
                    row.update({"native_complex_adds":adds,"native_complex_muls":muls,
                                "native_MPFR_precision_bits":prec,
                                **source_bound(adds+muls,prec,nsat,m,twice)})
                results.append(row);samples.append(row)
                print("GPMC_SINGLE_RUN_ACCOUNTING_SAMPLE "+json.dumps(row,sort_keys=True),flush=True)
        if len({r["weighted_count_exact_print"] for r in results})!=1:
            raise AssertionError(("instrumentation changed solver output",case))
        norm={}
        for flavor in ("baseline","probe"):
            v=[x for x in results if x["flavor"]==flavor]
            norm[flavor]={"median_wall_seconds":statistics.median(x["wall_seconds"] for x in v),
                          "median_peak_rss_kb":statistics.median(x["peak_rss_kb"] for x in v)}
        b,p=norm["baseline"],norm["probe"]
        row={"case":case,"samples_per_flavor":3,
             "all_six_printed_counts_identical":True,
             "baseline_median_seconds":b["median_wall_seconds"],
             "instrumented_median_seconds":p["median_wall_seconds"],
             "ratio_instrumented_over_baseline":p["median_wall_seconds"]/b["median_wall_seconds"] if b["median_wall_seconds"] else None,
             "baseline_peak_RSS_kB":b["median_peak_rss_kb"],
             "instrumented_peak_RSS_kB":p["median_peak_rss_kb"],
             "ratio_RSS_instrumented_over_baseline":p["median_peak_rss_kb"]/b["median_peak_rss_kb"],
             "production_overhead_measured":False,
             "native_runtime_overhead_research_probe_only":True}
        summaries.append(row)
        print("GPMC_SINGLE_RUN_ACCOUNTING_SUMMARY "+json.dumps(row,sort_keys=True),flush=True)
    record={"source_gitlink":"a1bda3489e959d3695b6798d327c5a1fc1bed305",
      "original_ComplexMPFR_cc_sha256":original_source_sha,
      "instrumented_ComplexMPFR_cc_sha256":modified_source_sha,
      "original_binary_sha256":hashlib.sha256(baseline.read_bytes()).hexdigest(),
      "instrumented_binary_sha256":hashlib.sha256(probed.read_bytes()).hexdigest(),
      "scratch_build_seconds":round(builds,3),
      "results":summaries,"samples":samples,
      "arithmetic_bounds_conditional_not_certified":True,
      "no_additional_native_solver_in_production":True,
      "experimental_repeat_runs_not_public_API_double_solver":True}
    (out/"gpmc-accounting-vs-baseline.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    baseline.unlink()
    probed.unlink()
    shutil.rmtree(scratch.parent)
    assert len(samples)==24
    print("GPMC_SINGLE_RUN_ACCOUNTING_FOUR_CASES_COMPLETE",flush=True)

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--gpmc-source",required=True,type=Path)
    a.add_argument("--artifact-folder",required=True,type=Path)
    a.add_argument("--output",required=True,type=Path)
    main(a.parse_args())

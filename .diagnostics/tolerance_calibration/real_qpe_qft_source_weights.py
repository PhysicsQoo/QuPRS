"""Experimental real-corpus weight fidelity: QPEexact8 Rust, QFT16 Python.

Strictly report-only. Preserve exact source coefficients; never snap based on
floating proximity, and never use A/B Solver differences as a formal error bound.
Only this experimental process may deliberately run multiple native GPMC
calls on different weight candidates. Public production remains one-pass.
"""
from __future__ import annotations
from contextlib import contextmanager
from fractions import Fraction
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import subprocess
import tempfile
import time
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import mpmath as mp


def write(out, family, **props):
    record={"family":family,**props}
    print("REAL_SOURCE_WEIGHT "+json.dumps(record,sort_keys=True,default=str),flush=True)
    with (out/"real-source-weight-records.jsonl").open("a") as stream:
        stream.write(json.dumps(record,sort_keys=True,default=str)+"\n")
    return record


def positive_weights(cnf):
    result={}
    for line in cnf.splitlines():
        if line.startswith("c p weight "):
            t=line.split()
            i=int(t[3])
            if i>0:
                if i in result:raise ValueError(("duplicate positive weight",i))
                result[i]=(t[4],t[5])
    return result


def substitute_weights(cnf, proposed):
    lines=[]; replaced=set()
    for line in cnf.splitlines():
        if line.startswith("c p weight "):
            tokens=line.split()
            i=int(tokens[3])
            if i in proposed and i>0:
                re_s,im_s=proposed[i]
                line=f"c p weight {i} {re_s} {im_s} 0"
                replaced.add(i)
        lines.append(line)
    if replaced != set(proposed): raise AssertionError((replaced,set(proposed)))
    return "\n".join(lines)+"\n"


def count_native(cnf,label,out,exe):
    target=out/(label+".cnf")
    target.write_text(cnf)
    started=time.monotonic()
    p=subprocess.run(
        [str(exe),"-mode=1","-prec=90",str(target)],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
        timeout=25,check=False,
    )
    (out/(label+".stdout")).write_text(p.stdout)
    (out/(label+".stderr")).write_text(p.stderr)
    if p.returncode:
        raise RuntimeError(f"GPMC {label} returned {p.returncode}: {p.stderr[-500:]}")
    from QuPRS.utils.precision_count import parse_printed_solver_output
    parsed=parse_printed_solver_output(p.stdout)
    with mp.workdps(125):
        real_decimal=mp.nstr(mp.mpf(parsed.real.numerator)/parsed.real.denominator,95)
        imag_decimal=mp.nstr(mp.mpf(parsed.imag.numerator)/parsed.imag.denominator,95)
    return {
      "label":label,"cnf_sha256":hashlib.sha256(cnf.encode()).hexdigest(),
      "real_decimal":real_decimal,
      "imag_decimal":imag_decimal,
      "elapsed_seconds":round(time.monotonic()-started,5),
      "stdout_sha256":hashlib.sha256(p.stdout.encode()).hexdigest(),
    }


def magnitude_record(count,twice):
    with mp.workdps(125):
        value=mp.mpc(mp.mpf(count["real_decimal"]),mp.mpf(count["imag_decimal"]))
        normal=mp.power(2,mp.mpf(twice)/2)
        mag=abs(value)/normal
        defect=1-mag
        distance_sq=1-mag**2
        return {
            "normalized_trace_magnitude":mp.nstr(mag,95),
            "normalized_magnitude_defect":mp.nstr(defect,95),
            "candidate_distance_sq":mp.nstr(distance_sq,95),
            "candidate_distance_status": (
                "printed_nonphysical_overshoot" if distance_sq < 0
                else "distance_at_most_1e-8" if distance_sq <= mp.mpf("1e-16")
                else "distance_above_1e-8"
            ),
        }


def get_native_source(path):
    lines=Path(path).read_text().splitlines()
    phases={};meta=None
    for line in lines:
        if "SOURCE_WEIGHT_AUDIT\tqpeexact8\t" in line:
            p=line.split("SOURCE_WEIGHT_AUDIT\tqpeexact8\t",1)[1].split("\t")
            if len(p)!=7:raise AssertionError(p)
            var,cn,cd,rn,rd,re_bits,im_bits=p
            if int(var) in phases:raise AssertionError(("duplicate phase",var))
            phases[int(var)]=(Fraction(int(cn),int(cd)),
                              Fraction(int(rn),int(rd)))
        if "SOURCE_QPE_MITER\t" in line:
            p=line.split("SOURCE_QPE_MITER\t",1)[1].split("\t")
            if len(p)!=4:raise AssertionError(p)
            meta=tuple(map(int,p))
    if meta is None or (meta[0],meta[1])!=(31,17):
        raise AssertionError(("source native shape",meta))
    if len(phases)!=17:raise AssertionError(len(phases))
    return phases,meta


def source_phases_to_weights(phases,digits=95):
    all_weight={}
    quarter={}
    categories={"exact_quarter":0,"exact_eighth_not_quarter":0,
                "source_radians_nonzero":0,"other_rational_cycles":0}
    with mp.workdps(125):
        for variable,(cycles,radians) in phases.items():
            mod=cycles % 1
            if radians:
                categories["source_radians_nonzero"]+=1
            elif (4*mod).denominator==1:
                categories["exact_quarter"]+=1
            elif (8*mod).denominator==1:
                categories["exact_eighth_not_quarter"]+=1
            else:
                categories["other_rational_cycles"]+=1
            angle=2*(mp.pi*mp.mpf(cycles.numerator)/cycles.denominator
                  + mp.mpf(radians.numerator)/radians.denominator)
            real,imag=mp.cos(angle),mp.sin(angle)
            all_weight[variable]=(mp.nstr(real,digits),mp.nstr(imag,digits))
            if not radians and (4*mod).denominator==1:
                root=int((4*mod)%4)
                quarter[variable]=[("1","0"),("0","1"),("-1","0"),("0","-1")][root]
                all_weight[variable]=quarter[variable]
    return all_weight,quarter,categories


def qpe_rust(out,crate_log):
    from QuPRS import check_equivalence
    from QuPRS.utils import WMC
    from precision_followup_v2 import capture_native_gpmc,sources
    phases,(nvars,weights,twice,active)=get_native_source(crate_log)
    root=out/"rust-qpeexact8-source-miter.cnf"
    original=root.read_text()
    if len(positive_weights(original))!=weights:
        raise AssertionError("wrong Rust native source CNF")
    exact,cliff,types=source_phases_to_weights(phases)
    orig_weights=positive_weights(original)
    # Never treat close numerical values as exact Clifford phases.
    changes=[]
    with mp.workdps(110):
        for k in cliff:
            r0,i0=orig_weights[k];r1,i1=cliff[k]
            delta=abs(mp.mpc(mp.mpf(r0),mp.mpf(i0))-
                      mp.mpc(mp.mpf(r1),mp.mpf(i1)))
            changes.append(mp.nstr(delta,50))
    source_hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in sources("qpeexact8")[:2]]
    write(out,"RUST_QPE_SOURCE_MAP",miter_vars=nvars,weights=weights,
          normalization_twice=twice,active_path_variables=active,
          classification="source_exact_not_numeric_nearest_root",phase_categories=types,
          quarter_weight_count=len(cliff),
          max_removed_quarter_error=max(changes,key=mp.mpf) if changes else "0",
          source_qasm_sha256=source_hashes)
    with WMC("gpmc") as exe:
        base=count_native(original,"research-rust-qpe-baseline",out,exe)
        quarter=count_native(substitute_weights(original,cliff),
                             "research-rust-qpe-quarter",out,exe)
        high=count_native(substitute_weights(original,exact),
                           "research-rust-qpe-highprecision",out,exe)
    for item in [base,quarter,high]:
        write(out,"RUST_QPE_COUNT_AB",case=item["label"],**item,
              **magnitude_record(item,twice))
    # Match experiment miter to actual pinned dev public baseline via one
    # independent Dev API call with a redirected native *single* process.
    left,right,strategy,_=sources("qpeexact8")
    with capture_native_gpmc(out,"qpeexact8-dev-baseline"):
        result=check_equivalence(str(left),str(right),backend="rust",
            method="hybrid",strategy=strategy,tool_name="gpmc",
            timeout=35,approximate_distance_tolerance=1e-8)
    public=(out/"rust-qpeexact8-dev-baseline.cnf").read_text()
    dev_weight=positive_weights(public)
    if len(dev_weight)!=weights:raise AssertionError("different miter weight count")
    public_stdout=(out/"rust-qpeexact8-dev-baseline.stdout.txt").read_text()
    public_count_lines=[s for s in public_stdout.splitlines() if s.startswith("c s exact")]
    from QuPRS.utils.precision_count import parse_printed_solver_output
    dev_count=parse_printed_solver_output(public_stdout)
    with mp.workdps(110):
        dev_complex=mp.mpc(mp.mpf(dev_count.real.numerator)/dev_count.real.denominator,
                           mp.mpf(dev_count.imag.numerator)/dev_count.imag.denominator)
        observed=mp.mpc(mp.mpf(base["real_decimal"]),mp.mpf(base["imag_decimal"]))
        rel=abs(observed-dev_complex)/mp.power(2,mp.mpf(twice)/2)
    write(out,"RUST_QPE_DEV_MATCH",dev_verdict=result.equivalent,
        dev_reason=result.wmc_precision_reason,
        dev_solver_invoked=result.wmc_solver_invoked,
        dev_public_raw_lines=public_count_lines,
        dev_cnf_sha256=hashlib.sha256(public.encode()).hexdigest(),
        research_cnf_sha256=hashlib.sha256(original.encode()).hexdigest(),
        dev_vs_research_normalized_count_gap=mp.nstr(rel,55),
        sources_are_not_identical_builds=True,
        dev_raw_cnf_has_same_shape=(public.splitlines()[0]==original.splitlines()[0]),
    )


def qft_python(out):
    from QuPRS import check_equivalence
    from QuPRS.interface import ps2wmc
    from QuPRS.utils import WMC
    import sympy as sp
    from precision_followup_v2 import sources
    left,right,strategy,hashes=sources("qft16")
    result=check_equivalence(
        str(left),str(right),backend="python",method="wmc_only",
        strategy=strategy,tool_name="gpmc",timeout=45,
        approximate_distance_tolerance=1e-8)
    if not result.CNF or result.expect is None:
        raise AssertionError("QFT public WMC CNF unavailable")
    cnf=result.CNF
    phase_terms=ps2wmc.P_to_wlogi(result.final_pathsum.P)
    native=list(positive_weights(cnf).items())
    if len(phase_terms)!=400 or len(native)!=400:
        raise AssertionError(("QFT phase count mismatch",len(phase_terms),len(native)))
    proposed={};unknown_source=0;exact_quarters=0;near_not_source=0
    for (phase,control),(var,(a,b)) in zip(phase_terms,native):
        expr=sp.sympify(str(phase))
        if expr.is_Rational and (4*expr).is_Integer:
            exact_quarters+=1
            val=int((4*expr)%4)
            proposed[var]=[("1","0"),("0","1"),("-1","0"),("0","-1")][val]
        else:
            unknown_source+=1
            v=complex(float(a),float(b))
            if min(abs(v-c) for c in (1,1j,-1,-1j)) < 1e-12:
                near_not_source+=1
    write(out,"QFT_SOURCE_AUDIT",case="qft16",backend="python",
          original_qasm_sha256=hashes,
          phase_terms=len(phase_terms),exact_quarter_terms=exact_quarters,
          not_proven_exact_terms=unknown_source,
          numerical_near_root_but_unproven_count=near_not_source,
          source_preserving_exact_quarter_rewrite_count=len(proposed),
          public_verdict=result.equivalent,
          printed_verdict=result.wmc_printed_verdict,
          numerical_reason=result.wmc_precision_reason)
    if int(2*result.expect)!=2*result.expect:raise AssertionError("normal exponent")
    twice=int(2*result.expect)
    # One control counting invocation on the *identical* original public CNF;
    # one candidate counting invocation only if exact source quarter cycles.
    with WMC("gpmc") as exe:
        base=count_native(cnf,"public-python-qft16-baseline",out,exe)
        write(out,"QFT_COUNT_AB",case="baseline",**base,**magnitude_record(base,twice))
        if proposed:
            candidate=count_native(substitute_weights(cnf,proposed),
                "public-python-qft16-quarter",out,exe)
            write(out,"QFT_COUNT_AB",case="source_quarter_only",
                  **candidate,**magnitude_record(candidate,twice))
        else:
            write(out,"QFT_COUNT_AB",case="source_quarter_only",
                  observation="skipped_no_source_exact_quarter",
                  no_numeric_proximity_snapping=True)
    # Explicit 1q source counterexample must remain not equivalent.
    header='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    negative=check_equivalence(header,header+"rz(0.01) q[0];",
        backend="python",method="wmc_only",strategy="Naive",
        tool_name="gpmc",timeout=30,approximate_distance_tolerance=1e-8)
    if negative.equivalent!="not_equivalent":
        raise AssertionError(("source-negative control is not separable",negative.equivalent))
    write(out,"SOURCE_NEGATIVE_CONTROL",verdict=negative.equivalent,
          expected_distance="sin(0.005)>1e-8",
          independent_phase_nonzero=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--rust-native-log",type=Path,required=True)
    o=ap.parse_args()
    o.output.mkdir(parents=True,exist_ok=True)
    qpe_rust(o.output,o.rust_native_log)
    qft_python(o.output)
    print("REAL_QPE_QFT_WEIGHT_STUDY_COMPLETE",flush=True)


if __name__=="__main__":
    main()

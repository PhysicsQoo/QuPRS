"""Directed MPFR source-phase enclosure and same-run GPMC d-DNNF witness.

Research only. QPEexact8 original and physically altered source miters,
extracted from exact rational Rust phase coefficients by #[cfg(test)] logs.
No extra production solver call, no heuristic snapping, no fixed guard.

MPFR ctypes ABI is restricted to the pinned Linux x86_64 research runner.
Directed rounding + global |sin'|,|cos'|<=1 encloses *true* source phases.
The printed-CNF-to-exact WMC step is conditional on faithful d-DNNF output.
"""
from __future__ import annotations
import argparse
import ctypes as C
from decimal import Decimal,localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from dnnf_exact_arithmetic_research import parse_weight_cnf,parse_evaluate
from structure_aware_source_bound import simplified_graph_proof
from QuPRS.utils import WMC

BITS=384
DOWN=3
UP=2
EPS=Fraction(1,10**8)
M=Fraction(1)+Fraction(1,2**40)
ONE=(Fraction(1),Fraction(0))


class MpfrStruct(C.Structure):
    _fields_=[("prec",C.c_long),("sign",C.c_int),
              ("exp",C.c_long),("limbs",C.POINTER(C.c_ulong))]


def bind_mpfr():
    lib=C.CDLL("libmpfr.so.6")
    specs={
        "mpfr_init2":(None,[C.POINTER(MpfrStruct),C.c_long]),
        "mpfr_clear":(None,[C.POINTER(MpfrStruct)]),
        "mpfr_set_str":(C.c_int,[C.POINTER(MpfrStruct),C.c_char_p,C.c_int,C.c_int]),
        "mpfr_const_pi":(C.c_int,[C.POINTER(MpfrStruct),C.c_int]),
        "mpfr_add":(C.c_int,[C.POINTER(MpfrStruct),C.POINTER(MpfrStruct),C.POINTER(MpfrStruct),C.c_int]),
        "mpfr_sub":(C.c_int,[C.POINTER(MpfrStruct),C.POINTER(MpfrStruct),C.POINTER(MpfrStruct),C.c_int]),
        "mpfr_mul":(C.c_int,[C.POINTER(MpfrStruct),C.POINTER(MpfrStruct),C.POINTER(MpfrStruct),C.c_int]),
        "mpfr_div":(C.c_int,[C.POINTER(MpfrStruct),C.POINTER(MpfrStruct),C.POINTER(MpfrStruct),C.c_int]),
        "mpfr_mul_2ui":(C.c_int,[C.POINTER(MpfrStruct),C.POINTER(MpfrStruct),C.c_ulong,C.c_int]),
        "mpfr_sin":(C.c_int,[C.POINTER(MpfrStruct),C.POINTER(MpfrStruct),C.c_int]),
        "mpfr_cos":(C.c_int,[C.POINTER(MpfrStruct),C.POINTER(MpfrStruct),C.c_int]),
        "mpfr_get_str":(C.c_void_p,[C.c_void_p,C.POINTER(C.c_long),C.c_int,C.c_size_t,C.POINTER(MpfrStruct),C.c_int]),
        "mpfr_free_str":(None,[C.c_void_p]),
    }
    for name,(ret,args) in specs.items():
        func=getattr(lib,name);func.restype=ret;func.argtypes=args
    return lib


class Directed:
    def __init__(self):
        self.lib=bind_mpfr()
        self.items=[]
    def new(self):
        v=MpfrStruct();self.lib.mpfr_init2(C.byref(v),BITS)
        self.items.append(v)
        return v
    def close(self):
        for v in reversed(self.items):self.lib.mpfr_clear(C.byref(v))
        self.items=[]
    def num(self,n,rnd):
        v=self.new()
        ret=self.lib.mpfr_set_str(C.byref(v),str(n).encode(),10,rnd)
        if ret not in (-1,0,1):raise ValueError("invalid MPFR integer input")
        return v
    def run(self,fn,x,y=None,rnd=DOWN):
        z=self.new()
        if fn=="mul_2ui":
            self.lib.mpfr_mul_2ui(C.byref(z),C.byref(x),y,rnd)
        elif y is None:
            getattr(self.lib,"mpfr_"+fn)(C.byref(z),C.byref(x),rnd)
        else:
            getattr(self.lib,"mpfr_"+fn)(C.byref(z),C.byref(x),C.byref(y),rnd)
        return z
    def exact_binary_fraction(self,v):
        exp=C.c_long()
        ptr=self.lib.mpfr_get_str(None,C.byref(exp),2,BITS+3,C.byref(v),DOWN)
        if not ptr:raise ValueError("cannot extract exact binary MPFR mantissa")
        try:s=C.string_at(ptr).decode()
        finally:self.lib.mpfr_free_str(ptr)
        sign=-1 if s.startswith("-") else 1
        digits=s.lstrip("-")
        return Fraction(sign*int(digits,2))*Fraction(2)**(exp.value-len(digits))
    def rational(self,q):
        def extremum(rnd):
            numerator=self.num(q.numerator,rnd)
            # The denominator rounding for a negative ratio reverses.
            den_round=(UP if rnd==DOWN else DOWN) if q>=0 else (DOWN if rnd==DOWN else UP)
            denominator=self.num(q.denominator,den_round)
            return self.run("div",numerator,denominator,rnd)
        return extremum(DOWN),extremum(UP)
    def add(self,a,b):
        return self.run("add",a[0],b[0],DOWN),self.run("add",a[1],b[1],UP)
    def mul(self,a,b):
        lows=[self.run("mul",x,y,DOWN) for x in a for y in b]
        highs=[self.run("mul",x,y,UP) for x in a for y in b]
        return (min(lows,key=self.exact_binary_fraction),
                max(highs,key=self.exact_binary_fraction))
    def trig(self,cycles,radians,name):
        pi=(self.new(),self.new())
        self.lib.mpfr_const_pi(C.byref(pi[0]),DOWN)
        self.lib.mpfr_const_pi(C.byref(pi[1]),UP)
        angle=self.add(self.mul(self.rational(cycles),pi),self.rational(radians))
        angle=(self.run("mul_2ui",angle[0],1,DOWN),
               self.run("mul_2ui",angle[1],1,UP))
        width=self.run("sub",angle[1],angle[0],UP)
        # sin/cos are globally 1-Lipschitz; directed trig of the
        # lower endpoint +/- the upward-rounded argument interval width
        # encloses the exact mathematical trig for every possible angle.
        center_lo=self.run(name,angle[0],rnd=DOWN)
        center_hi=self.run(name,angle[0],rnd=UP)
        low=self.run("sub",center_lo,width,DOWN)
        high=self.run("add",center_hi,width,UP)
        return self.exact_binary_fraction(low),self.exact_binary_fraction(high)


def phases_from_log(content,label):
    phases={}
    for line in content.splitlines():
        marker="SOURCE_WEIGHT_AUDIT\t"+label+"\t"
        if marker not in line:continue
        parts=line.split(marker,1)[1].split("\t")
        if len(parts)!=7:raise ValueError(("native audit format",parts))
        var,cn,cd,rn,rd,_,_=parts
        index=int(var)
        if index in phases:raise ValueError("duplicate native phase weight")
        phases[index]=(Fraction(int(cn),int(cd)),Fraction(int(rn),int(rd)))
    return phases


def status_from_rationals(z,E,twice):
    r,i=z;c2=r*r+i*i
    th=Fraction(2)**twice*(1-EPS*EPS)
    negative_gap=th-c2-E*E
    positive_gap=c2-th-E*E
    if negative_gap>0 and negative_gap**2>4*E*E*c2:
        return "conditional_not_equivalent"
    if positive_gap>=0 and positive_gap**2>=4*E*E*th:
        return "conditional_within_distance"
    return "unknown"


def frac_decimal(x):
    if not x:return "0"
    with localcontext() as c:
        c.prec=40
        return format(Decimal(x.numerator)/Decimal(x.denominator),".19E")


def check_case(out,source_log,label,cnf_file,expected_n,expected_m,twice,exe):
    phases=phases_from_log(source_log,label)
    cnf=cnf_file.read_text()
    n,weights=parse_weight_cnf(cnf)
    positive={i:w for i,w in weights.items() if i>0}
    if (n,len(positive),len(phases))!=(expected_n,expected_m,expected_m):
        raise AssertionError(("source-CNF mismatch",n,len(positive),len(phases)))
    if set(positive)!=set(phases):
        raise AssertionError("CNF phase identity not matched")
    if any(weights.get(-i)!=ONE for i in positive):
        raise AssertionError("unexpected negative phase weight")
    if any(x*x+y*y>M*M for x,y in positive.values()):
        raise AssertionError("weight magnitude exceeds explicit M")
    interval=Directed()
    try:
        gaps=[]
        for var,(cycles,rads) in sorted(phases.items()):
            rlo,rhi=interval.trig(cycles,rads,"cos")
            ilo,ihi=interval.trig(cycles,rads,"sin")
            re,im=positive[var]
            d_re=max(abs(re-rlo),abs(re-rhi))
            d_im=max(abs(im-ilo),abs(im-ihi))
            gap=d_re+d_im  # exact rational L1 upper bounds Euclidean complex error.
            gaps.append(gap)
        delta=max(gaps)
    finally:
        interval.close()
    # Fixed source fields are exact rationals as the Rust encoder reports.
    # Require the actually computed bound, not a guessed uniform epsilon.
    if delta>Fraction(1,2**49):
        raise AssertionError(("source delta >2^-49",label,frac_decimal(delta)))
    target=out/(label+".cnf")
    target.write_text(cnf)
    nnf=out/(label+".nnf")
    process=subprocess.run([str(exe),"-mode=1","-prec=90","-ddnnf",
           "-nnfout="+str(nnf),str(target)],capture_output=True,
           text=True,timeout=50)
    (out/(label+".stdout")).write_text(process.stdout)
    (out/(label+".stderr")).write_text(process.stderr)
    if process.returncode or not nnf.is_file():
        raise RuntimeError(("dDNNF single solver call failed",label,process.returncode))
    nsat,checked=simplified_graph_proof(nnf,n)
    exact,stats=parse_evaluate(nnf,n,weights)
    error=nsat*len(positive)*delta*M**(len(positive)-1)
    status=status_from_rationals(exact,error,twice)
    row={
        "source_case":label,
        "original_source_phase_weight_count":len(phases),
        "actual_rigorous_max_complex_l1_error":frac_decimal(delta),
        "source_weight_bound_2exp_minus49_PROVEN_FOR_THIS_PINNED_MITER":True,
        "per_weight_max_under_2exp_minus51":delta <= Fraction(1,2**51),
        "n_sat_graph_exact":str(nsat),
        "nnf_decomposable_AND_checked":checked["nnf_AND_decomposability_verified"],
        "nnf_disjoint_OR_checked":checked["nnf_decision_OR_disjointness_verified"],
        "nnf_mapping_checked":checked["nnf_all_original_vars_unique"],
        "cnf_sha256":hashlib.sha256(cnf.encode()).hexdigest(),
        "nnf_sha256":hashlib.sha256(nnf.read_bytes()).hexdigest(),
        "normalization_twice":twice,
        "rigorous_conditional_WMC_source_weight_count_radius":frac_decimal(error),
        "rigorous_conditional_normalized_count_radius":frac_decimal(error / Fraction(2)**(twice//2)),
        "status_IF_dDNNF_faithful":status,
        "original_CNF_to_dDNNF_equivalence_NOT_yet_proven":True,
        "source_rational_coefficient_semantics_PARSER_CONDITIONAL":True,
        "solver_calls_in_research":1,
        "production_extra_solver_calls":0,
        "nnf_nodes":stats["nnf_nodes"],
    }
    print("DIRECTED_MPFR_SOURCE_PROOF "+json.dumps(row,sort_keys=True),flush=True)
    return row


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--rust-native-log",type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    source_log=a.rust_native_log.read_text()
    with WMC("gpmc") as exe:
        records=[
            check_case(a.output,source_log,"qpeexact8",
                a.output/"rust-qpeexact8-source-miter.cnf",31,17,22,exe),
            check_case(a.output,source_log,"qpeexact8_self_negative",
                a.output/"rust-qpeexact8-self-negative-source-miter.cnf",
                10,2,16,exe),
        ]
    (a.output/"directed-source-interval-and-single-run-nnf.json").write_text(
        json.dumps({"records":records,"source_phase_to_printed_weight_interval_proven":True,
            "compiled_dnnf_original_cnf_semantics_independently_proven":False,
            "not_a_production_classifier":True},sort_keys=True,indent=2)+"\n")
    print("DIRECTED_MPFR_TWO_ORIGINAL_SOURCE_MITERS_COMPLETE",flush=True)


if __name__=="__main__":
    main()

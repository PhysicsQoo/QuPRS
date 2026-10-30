"""Research-only MPFR decimal-input and GPMC stdout binary-value certification.
Exact source-pinned 4 CNFs, one native GPMC invocation each, no production edit.
A scratch copy instruments only Complex output to capture MPFR binary values and flags.
"""
from __future__ import annotations
import argparse,ctypes as C,hashlib,json,re,shutil,subprocess,tempfile
from pathlib import Path
from decimal import Decimal,localcontext
from fractions import Fraction

P=299
CASES={
"qpeexact8-baseline":"34d38d1718f1796d6af46cfa079aa2093aa00e5997f5b428e8af4b1672a35ee7",
"qpeexact8-self_negative":"b965d82a7bf4900350a2cbef028ff51506b9bb0f426859c1be9432207872d2d7",
"qft16-baseline":"20ee9e55eb1fc644d08daf130d180ded46f06f67897fa46f57b4f4ef4ef7f8f1",
"qft16-self_negative":"8e65b1d5cfdc99c4d980bc4fea24162afc4f9583e0ebf17686fc8a9f1bc6555c"}
class M(C.Structure):
    _fields_=[("prec",C.c_long),("sign",C.c_int),("exp",C.c_long),("limbs",C.POINTER(C.c_ulong))]
def bits_to_fraction(digits,ex):
    sign=-1 if digits.startswith("-") else 1
    digits=digits.lstrip("-")
    if not digits or any(x not in "01" for x in digits):raise ValueError("binary digits invalid")
    return Fraction(sign*int(digits,2))*Fraction(2)**(ex-len(digits))
def readable(x):
    if x==0:return "0"
    with localcontext() as ctx:
        ctx.prec=42
        return format(Decimal(x.numerator)/Decimal(x.denominator),".16E")
class Mpfr:
    def __init__(self):
        lib=C.CDLL("libmpfr.so.6")
        for name,ret,types in (
            ("mpfr_init2",None,[C.POINTER(M),C.c_long]),
            ("mpfr_clear",None,[C.POINTER(M)]),
            ("mpfr_set_str",C.c_int,[C.POINTER(M),C.c_char_p,C.c_int,C.c_int]),
            ("mpfr_get_str",C.c_void_p,[C.c_void_p,C.POINTER(C.c_long),C.c_int,C.c_size_t,C.POINTER(M),C.c_int]),
            ("mpfr_free_str",None,[C.c_void_p])):
            fn=getattr(lib,name);fn.restype=ret;fn.argtypes=types
        self.lib=lib
    def decimal_to_exact_binary(self,x):
        a=M();self.lib.mpfr_init2(C.byref(a),P)
        try:
            ret=self.lib.mpfr_set_str(C.byref(a),x.encode(),10,0)
            if ret!=0:raise ValueError(("MPFR cannot parse decimal",x))
            exp=C.c_long()
            raw=self.lib.mpfr_get_str(None,C.byref(exp),2,0,C.byref(a),0)
            if not raw:raise ValueError("MPFR cannot extract exact value")
            try:mantissa=C.string_at(raw).decode()
            finally:self.lib.mpfr_free_str(raw)
            return bits_to_fraction(mantissa,exp.value)
        finally:self.lib.mpfr_clear(C.byref(a))

def source_weight_audit(cnf,mp):
    count=0;maxgap=Fraction(0);bound=Fraction(1,2**P)
    for line in cnf.read_text().splitlines():
        a=line.split()
        if a[:3]!=["c","p","weight"]:continue
        count+=1
        x,y=Fraction(Decimal(a[4])),Fraction(Decimal(a[5]))
        xx,yy=mp.decimal_to_exact_binary(a[4]),mp.decimal_to_exact_binary(a[5])
        diff=(xx-x)**2+(yy-y)**2
        if diff>bound**2*(x*x+y*y):
            raise AssertionError(("input nearest-p299 enclosure failed",a[3]))
        maxgap=max(maxgap,abs(xx-x)+abs(yy-y))
    return {"literal_weight_records":count,"all_decimal_to_mpfr_input_bounds_pass":True,
            "max_input_weight_complex_l1_rounding":readable(maxgap)}

CXX=r"""
    mpfr_exp_t ere=0,eim=0;
    char *bre=mpfr_get_str(NULL,&ere,2,0,c.real.mpfr_srcptr(),MPFR_RNDN);
    char *bim=mpfr_get_str(NULL,&eim,2,0,c.imag.mpfr_srcptr(),MPFR_RNDN);
    if (!bre || !bim) std::abort();
    std::fprintf(stderr,"QUPRS_MPFR_AUDIT rnd=%d uf=%d of=%d nan=%d erange=%d realnum=%d imagnum=%d rprec=%ld iprec=%ld rex=%ld rbits=%s iex=%ld ibits=%s\n",
      (int)mpfr_get_default_rounding_mode(),(int)mpfr_underflow_p(),
      (int)mpfr_overflow_p(),(int)mpfr_nanflag_p(),(int)mpfr_erangeflag_p(),
      (int)mpfr_number_p(c.real.mpfr_srcptr()),(int)mpfr_number_p(c.imag.mpfr_srcptr()),
      (long)mpfr_get_prec(c.real.mpfr_srcptr()),(long)mpfr_get_prec(c.imag.mpfr_srcptr()),
      (long)ere,bre,(long)eim,bim);
    mpfr_free_str(bre);mpfr_free_str(bim);
"""
def instrument(original,scratch):
    shutil.copytree(original,scratch,ignore=shutil.ignore_patterns(".git","build","bin"))
    path=scratch/"c-mpfr/ComplexMPFR.cc"
    source=path.read_text()
    marker="std::ostream &operator<<(std::ostream &os, Complex const &c)\n{"
    if source.count(marker)!=1:raise ValueError("Complex stream source signature not unique")
    modified='#include <cstdio>\n#include <cstdlib>\n'+source.replace(marker,marker+CXX)
    path.write_text(modified)
    return hashlib.sha256(source.encode()).hexdigest(),hashlib.sha256(modified.encode()).hexdigest()
def parse_output(stdout):
    prefix="c s exact double prec-sci "
    hits=[x[len(prefix):].strip().replace(" ","") for x in stdout.splitlines() if x.startswith(prefix)]
    if len(hits)!=1 or not hits[0].endswith("i"):raise ValueError("GPMC complex output missing")
    body=hits[0][:-1]
    ends=[i for i in range(1,len(body)) if body[i] in "+-" and body[i-1] not in "eE"]
    if len(ends)!=1:raise ValueError("unsupported complex output")
    return body[:ends[0]],body[ends[0]:]
def format_check(bits,ex,printed):
    binary=bits_to_fraction(bits,int(ex))
    exact_print=Fraction(Decimal(printed))
    gap=abs(binary-exact_print)
    if exact_print==0:
        if binary:raise AssertionError("nonzero MPFR value printed zero")
        radius=Fraction(0)
    else:
        # .90Rg rounds to 90 significant decimal digits (possibly stripped).
        radius=Fraction(10)**(Decimal(printed).adjusted()-89)/2
        if gap>radius:raise AssertionError(("MPFR print radius",printed,readable(gap),readable(radius)))
    return {"gap":readable(gap),"90significant_decimal_halfunit_bound":readable(radius)}
def main(args):
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    mp=Mpfr();scratch=Path(tempfile.mkdtemp(prefix="qprs-mpfr-io-",dir=str(out.parent)))/"GPMC"
    try:
        before,after=instrument(args.gpmc_source,scratch)
        for cmd in (["cmake","-S",str(scratch),"-B",str(scratch/"build"),"-DCMAKE_BUILD_TYPE=Release"],
                    ["cmake","--build",str(scratch/"build"),"-j","4"]):
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
            if p.returncode:raise RuntimeError(("GPMC scratch build failed",p.stderr[-1700:]))
        records=[]
        for label,expected_sha in CASES.items():
            cnf=args.artifact_folder/(label+".cnf")
            if hashlib.sha256(cnf.read_bytes()).hexdigest()!=expected_sha:raise ValueError("CNF changed")
            inputs=source_weight_audit(cnf,mp)
            p=subprocess.run([str(scratch/"build/gpmc"),"-mode=1","-prec=90",str(cnf)],
                             capture_output=True,text=True,timeout=45)
            (out/(label+".stdout")).write_text(p.stdout)
            (out/(label+".stderr")).write_text(p.stderr)
            if p.returncode:raise RuntimeError(("solver failed",label,p.stderr[-300:]))
            evidence=[x.split("QUPRS_MPFR_AUDIT ",1)[1] for x in p.stderr.splitlines()
                      if "QUPRS_MPFR_AUDIT " in x]
            if len(evidence)!=1:raise ValueError(("exact MPFR output evidence missing",label))
            fields=dict(x.split("=",1) for x in evidence[0].split())
            valid={"rnd":"0","uf":"0","of":"0","nan":"0","erange":"0",
                   "realnum":"1","imagnum":"1","rprec":"299","iprec":"299"}
            if any(fields.get(k)!=v for k,v in valid.items()):
                raise AssertionError(("unexpected MPFR rounding, exponent or flags",label,fields))
            re,im=parse_output(p.stdout)
            print_metrics=[format_check(fields["rbits"],fields["rex"],re),
                           format_check(fields["ibits"],fields["iex"],im)]
            row={"case":label,"original_cnf_sha256":expected_sha,"input_weight_evidence":inputs,
                 "native_MPFR_status":valid,"stdout_component_evidence":print_metrics,
                 "decimal_input_to_p299_checked":True,"p299_to_stdout_checked":True,
                 "one_native_solver_call_per_research_case":True,
                 "whole_solver_arithmetic_not_yet_proven":True}
            records.append(row)
            print("GPMC_MPFR_IO_CONTRACT "+json.dumps(row,sort_keys=True),flush=True)
        (out/"gpmc-input-output-mpfr-contract.json").write_text(
            json.dumps({"records":records,"original_complex_source_sha":before,
                        "instrumented_source_sha":after,
                        "no_production_modification":True},indent=2,sort_keys=True)+"\n")
        print("FOUR_GPMC_MPFR_INPUT_OUTPUT_CASES_CHECKED",flush=True)
    finally:shutil.rmtree(scratch.parent,ignore_errors=True)
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--gpmc-source",type=Path,required=True)
    parser.add_argument("--artifact-folder",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    main(parser.parse_args())

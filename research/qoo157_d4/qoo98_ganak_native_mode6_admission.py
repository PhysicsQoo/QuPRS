"""QOO-98: native Ganak 2.8.0 Mode6 output-admission (untimed scientific audit).

A pinned, unchanged binary; exact Fraction-complex tiny WMC oracle and
bounded original-CNF printed-reference screen. Printed digits != internal bits.
"""
from __future__ import annotations
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import product
from pathlib import Path
from hashlib import sha256
import argparse, json, re, subprocess

UPSTREAM="b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281"
CASES=("grover4_eq","qaoa7_neq","qpeexact8_eq","qft16_eq")
OUTPUT=re.compile(r"^c s exact (?:half|single|double|quadruple|octuple) float ([+-]?\d\.\d{8}[eE][+-]\d+) \+ ([+-]?\d\.\d{8}[eE][+-]\d+)i\s*$")
ONE=(Fraction(1),Fraction(0));ZERO=(Fraction(0),Fraction(0))

def mul(a,b):return(a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0])
def fmt(x):
    with localcontext() as c:
        c.prec=110
        return Decimal(x.numerator)/Decimal(x.denominator)
def half(text):
    exp=int(re.search(r"[eE]([+-]\d+)$",text).group(1))
    return Decimal(5).scaleb(exp-9)
def count_small(n,clauses,weights):
    ans=ZERO
    for truth in product((False,True),repeat=n):
        if not all(any(truth[abs(l)-1]==(l>0) for l in c) for c in clauses):continue
        weight=ONE
        for v in range(1,n+1):
            weight=mul(weight,weights.get(v if truth[v-1] else -v,ONE))
        ans=(ans[0]+weight[0],ans[1]+weight[1])
    return ans
def fixture(name,n,clauses,weights):
    lines=[f"p cnf {n} {len(clauses)}","c t wmc"]
    lines += [f"c p weight {l} {fmt(w[0])} {fmt(w[1])} 0" for l,w in sorted(weights.items())]
    lines += [" ".join(map(str,c))+" 0" for c in clauses]
    return name,("\n".join(lines)+"\n").encode(),count_small(n,clauses,weights)

def to_ganak_weight_grammar(raw):
    """Translate GPMC paired real/imag weight tokens to Ganak signed-complex-i.

    The original Boolean clauses, variable and clause IDs, and all literal
    weights are unchanged. This is the same dialect as QuPRS GanakAdapter.
    """
    out=[];unchanged=[];weight_semantics=[];seen=set()
    for line in raw.decode("utf-8").splitlines():
        parts=line.split()
        if parts[:3]==["c","p","weight"]:
            if len(parts)!=7 or parts[-1]!="0":
                raise ValueError("unsupported GPMC weight record")
            lit=int(parts[3])
            real=Decimal(parts[4]);imag=Decimal(parts[5])
            if not real.is_finite() or not imag.is_finite() or lit==0 or lit in seen:
                raise ValueError("nonfinite, invalid or duplicate weight")
            seen.add(lit)
            sign="-" if imag<0 else "+"
            imag_abs=str(abs(imag))
            replacement=f"c p weight {lit} {parts[4]} {sign} {imag_abs}i 0"
            # Independently check new serialized tokens recover exact
            # original finite-decimal rational components.
            converted=replacement.split()
            assert converted[:4]==parts[:4] and converted[-1]=="0"
            assert Fraction(Decimal(converted[4]))==Fraction(real)
            assert Fraction(Decimal(converted[6][:-1]))*(1 if converted[5]=="+" else -1)==Fraction(imag)
            out.append(replacement)
            weight_semantics.append((lit,str(Fraction(real)),str(Fraction(imag))))
        elif parts[:2]==["p","cnf"] or parts==["c","t","wmc"] or (
            parts and parts[0] not in ("c","p")
        ):
            out.append(line)
            unchanged.append(line)
        else:
            raise ValueError("unsupported source CNF metadata: "+line[:100])
    if not any(x.startswith("p cnf ") for x in unchanged):
        raise ValueError("missing source CNF header")
    result=("\n".join(out)+"\n").encode()
    return result,{
        "original_sha256":sha256(raw).hexdigest(),
        "ganak_dialect_sha256":sha256(result).hexdigest(),
        "unchanged_nonweight_lines_sha256":sha256(("\n".join(unchanged)+"\n").encode()).hexdigest(),
        "exact_literal_weight_values_sha256":sha256(json.dumps(sorted(weight_semantics)).encode()).hexdigest(),
        "literal_weight_entries":len(weight_semantics),
        "translation":"QuPRS GanakAdapter signed a +/- bi tokens, exact decimals; Boolean CNF unchanged"
    }

def fixtures():
    f=lambda x,y:(Fraction(x),Fraction(y))
    return [
      fixture("negative_real_complex_unit",1,[(1,)],{1:f("-2.5","1.125"),-1:f(5,-1)}),
      fixture("free_complex_sum",1,[],{1:f("1.25","2.5"),-1:f("-1.5","-0.25")}),
      fixture("weighted_equal",2,[(1,-2),(-1,2)],{1:f(2,3),-1:f(-1,1),2:f(1,-2),-2:f(3,0)}),
      fixture("weighted_antiequal",2,[(1,2),(-1,-2)],{1:f(2,1),-1:f(-3,1),2:f(1,2),-2:f(-2,-1)}),
      fixture("near_cancellation",1,[],{1:f("1.00000000000000000001","0.00000000000000000002"),-1:f(-1,0)}),
      fixture("zero_cancellation",1,[],{1:f(1,1),-1:f(-1,-1)}),
      fixture("free_unweighted",1,[],{}),
    ]

def native(binary,cnf,bits):
    cp=subprocess.run([str(binary),"--mode=6",f"--mpfrprec={bits}",str(cnf)],
       capture_output=True,text=True,timeout=25,check=False)
    if cp.returncode:
        return {"status":"NATIVE_ERROR","returncode":cp.returncode,"stderr":cp.stderr[-400:]}
    matches=[OUTPUT.fullmatch(l) for l in cp.stdout.splitlines()]
    found=[m for m in matches if m]
    if len(found)!=1:return {"status":"PRINT_FORMAT_UNRECOGNIZED","exact_lines":[l for l in cp.stdout.splitlines() if l.startswith("c s exact ")][:3]}
    m=found[0]
    return {"status":"COMPLETED","real":m.group(1),"imag":m.group(2),
        "sat_line":[l for l in cp.stdout.splitlines() if l in ("s SATISFIABLE","s UNSATISFIABLE")],
        "stdout_sha256":sha256(cp.stdout.encode()).hexdigest()}

def compare(result,expected,large=False):
    if result["status"]!="COMPLETED":return result
    checks=[]
    for component,value in zip(("real","imag"),expected):
        printed=result[component]
        reference=fmt(value) if isinstance(value,Fraction) else value
        # Extra historical 1e-12 count-scale is not part of print rounding,
        # and is NEVER interpreted as an internal MPFR arithmetic bound.
        screen=max(Decimal(1),abs(reference))*Decimal("1e-12") if large else Decimal(0)
        gap=abs(Decimal(printed)-reference)
        checks.append({"part":component,"difference":str(gap),
            "output_half_ulp":str(half(printed)),"historical_extra":str(screen),
            "within_print_plus_history":gap<=half(printed)+screen})
    result["components"]=checks
    result["status"]="PRINT_CONCORDANT_UNCERTIFIED" if all(x["within_print_plus_history"] for x in checks) else "PRINT_DISAGREEMENT"
    return result

def audit(binary,manifest,archive,cnfdir,science,fixturesdir,out):
    fields=[s.split() for s in manifest.read_text().splitlines() if s.startswith("linux x86_64 ")]
    if len(fields)!=1 or len(fields[0])!=5:raise ValueError("bad pinned manifest")
    _,_,name,sha_archive,sha_binary=fields[0]
    if name!="ganak-v2.8.0-linux-amd64.tar.gz":raise ValueError("asset mismatch")
    if sha256(archive.read_bytes()).hexdigest()!=sha_archive:raise ValueError("archive SHA mismatch")
    if sha256(binary.read_bytes()).hexdigest()!=sha_binary:raise ValueError("binary SHA mismatch")
    ver=subprocess.run([str(binary),"--version"],capture_output=True,text=True,timeout=5)
    if ver.returncode or "Ganak SHA1: "+UPSTREAM not in ver.stdout:raise ValueError("embedded SHA mismatch")
    src=json.loads(science.read_text())
    if src.get("complete") is not True:raise ValueError("source original archive not complete")
    result={"status":"INCOMPLETE","pinned_ganak_sha":UPSTREAM,
      "official_binary_sha256":sha_binary,"official_archive_sha256":sha_archive,
      "requested_mpfr_bits":127,"mode6_output_format":"%.8Re + %.8Rei",
      "actual_print_significant_digits":9,
      "fair_38d_output_ranking":"NOT_COMPARABLE_FOR_38D_OUTPUT",
      "internal_arithmetic_certified":False,"uses_codspeed":False,
      "fixtures":{},"source_cases":{}}
    fixturesdir.mkdir(parents=True,exist_ok=True)
    for name,data,expected in fixtures():
        p=fixturesdir/(name+".cnf")
        translated,serialization=to_ganak_weight_grammar(data)
        p.write_bytes(translated)
        obs={str(bits):compare(native(binary,p,bits),expected) for bits in (127,256)}
        result["fixtures"][name]={"source_sha256":sha256(data).hexdigest(),"serialization":serialization,"exact_WMC":[str(x) for x in expected],"native":obs}
        out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+"\n")
    for case in CASES:
        p=cnfdir/(case+".cnf");digest=sha256(p.read_bytes()).hexdigest()
        archived=src["cases"][case]
        if digest!=archived["same_cnf_sha256"]:raise ValueError("original CNF SHA mismatch")
        anchor=archived["precision_pairs"]["38"]["observations"]["gpmc-38"]
        with localcontext() as c:
            c.prec=100
            expected=tuple(fmt(Fraction(anchor[k])) for k in ("real","imag"))
        native_file=fixturesdir/("original_"+case+".cnf")
        translated,serialization=to_ganak_weight_grammar(p.read_bytes())
        native_file.write_bytes(translated)
        result["source_cases"][case]={"source_sha256":digest,"serialization":serialization,"reference_is_exact":False,
           "native":compare(native(binary,native_file,127),expected,True)}
        out.write_text(json.dumps(result,indent=2)+"\n")
    failed=[k+"/"+bits for k,v in result["fixtures"].items() for bits,d in v["native"].items() if d["status"]!="PRINT_CONCORDANT_UNCERTIFIED"]
    failed += [k for k,v in result["source_cases"].items() if v["native"]["status"]!="PRINT_CONCORDANT_UNCERTIFIED"]
    result["status"]="NATIVE_PRINT_SCREEN_PASS_PRECISION_LIMITED" if not failed else "NATIVE_PRINT_SCREEN_INCONCLUSIVE"
    result["failed_screens"]=failed
    out.write_text(json.dumps(result,indent=2)+"\n")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("binary","manifest","archive","original-dir","source-science","fixtures-dir","out"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    result=audit(a.binary,a.manifest,a.archive,a.original_dir,a.source_science,a.fixtures_dir,a.out)
    print(json.dumps({"status":result["status"],"fixtures":len(result["fixtures"]),
      "source_cases":len(result["source_cases"]),"failed":result["failed_screens"]}))
    if result["status"]!="NATIVE_PRINT_SCREEN_PASS_PRECISION_LIMITED":raise SystemExit(1)

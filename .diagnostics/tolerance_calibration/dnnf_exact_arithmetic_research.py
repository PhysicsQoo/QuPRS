"""Research-only exact rational evaluator for GPMC emitted d-DNNF.

No WMC proof is claimed until mapping/preprocessing and the d-DNNF
determinism/decomposability/correctness have independent validation.
An exact d-DNNF evaluation eliminates arithmetic rounding *conditional
on the circuit representing the original printed weighted CNF*.
"""
from __future__ import annotations
from collections import Counter
from decimal import Decimal,localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

MAX_NNF_BYTES=40_000_000
MAX_NODES=350_000

def parse_weight_cnf(cnf: str):
    n=None; numclauses=None; clause_count=0; weights={}
    for line in cnf.splitlines():
        a=line.split()
        if not a:continue
        if a[:2]==["p","cnf"]:
            if n is not None:raise ValueError("duplicate header")
            n=int(a[2]);numclauses=int(a[3])
        elif a[:3]==["c","p","weight"]:
            lit=int(a[3])
            weights[lit]=(Fraction(Decimal(a[4])),Fraction(Decimal(a[5])))
        elif a[0]!="c":
            assert a[-1]=="0",line
            clause_count+=1
    if n is None or numclauses!=clause_count:
        raise ValueError(("CNF clause header mismatch",n,numclauses,clause_count))
    if any(i==0 or abs(i)>n for i in weights):raise ValueError("invalid weight literal")
    return n,weights


def plus(a,b):
    return a[0]+b[0],a[1]+b[1]

def times(a,b):
    return a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]

ONE=(Fraction(1),Fraction(0))
ZERO=(Fraction(0),Fraction(0))

def compact_rat(x, digits=45):
    if x==0:return "0"
    with localcontext() as ctx:
        ctx.prec=digits
        return format(Decimal(x.numerator)/Decimal(x.denominator),".25E")


def parse_evaluate(nnf_path:Path, original_var_count:int,weights):
    if nnf_path.stat().st_size>MAX_NNF_BYTES:raise ValueError("nnf too large")
    mapping={}; fixed=[];free=[];deleted=[];ops=[];header=None;root=None
    with nnf_path.open() as f:
        for line in f:
            a=line.split()
            if not a or a[0]=="c":continue
            head=a[0]
            if head=="p":
                if a[1]!="vmap":raise ValueError(a)
                if int(a[2])!=original_var_count:raise ValueError("unexpected original variable count")
            elif head=="v":
                orig=int(a[1]);v=int(a[2]);sgn=1 if v>0 else -1
                mapping.setdefault(abs(v),[]).append(sgn*orig)
            elif head=="a":fixed.extend(int(x) for x in a[1:-1])
            elif head=="f":free.append([int(x) for x in a[1:-1]])
            elif head=="d":deleted.extend(int(x) for x in a[1:-1])
            elif head=="nnf":
                header=tuple(map(int,a[1:]))
            elif head in ("L","A","O"):
                if len(ops)>=MAX_NODES:raise ValueError("NNF too many nodes")
                if head=="L":
                    value=int(a[1]);ops.append((head,value,()))
                elif head=="A":
                    arity=int(a[1]);children=tuple(map(int,a[2:]))
                    if len(children)!=arity:raise ValueError("AND arity mismatch")
                    if any(x>=len(ops) for x in children):raise ValueError("AND topological order")
                    ops.append((head,0,children))
                else:
                    arity=int(a[2]);children=tuple(map(int,a[3:]))
                    if len(children)!=arity or (len(children)!=2 and arity!=0):raise ValueError("OR arity")
                    if any(x>=len(ops) for x in children):raise ValueError("OR topological order")
                    ops.append((head,int(a[1]),children))
            else:raise ValueError(("unexpected NNF line",head))
    if not ops or header is None or header[0]!=len(ops):
        raise ValueError(("missing/mismatched NNF header",header,len(ops)))
    if deleted:raise ValueError(("unsupported deleted preprocessor variables",len(deleted)))
    # Multi-var simplified LIT mappings are products of the corresponding
    # source literals, just as GPMC's own dDNNF enumerator canonicalizes.
    seen={abs(v) for group in mapping.values() for v in group}
    seen|={abs(x) for x in fixed}
    seen|={abs(x) for group in free for x in group}
    # A variable absent from every category makes reconstruction ambiguous.
    if seen!=set(range(1,original_var_count+1)):
        raise ValueError(("mapping incomplete",len(seen),original_var_count,
                          sorted(set(range(1,original_var_count+1))-seen)[:15]))
    def w(lit):
        return weights.get(lit,ONE)
    values=[]
    support=[]
    for typ,param,children in ops:
        if typ=="L":
            literals=mapping.get(abs(param))
            if literals is None:
                raise ValueError(("unmapped simplified variable",param))
            sign=1 if param>0 else -1
            val=ONE
            for lit in literals:
                val=times(val,w(sign*lit))
            supp=frozenset(abs(x) for x in literals)
        elif typ=="A":
            val=ONE;supp=frozenset()
            for x in children:
                # Genuine decomposability is testable in polynomial time;
                # enforce it, do not trust the output format's name.
                if supp.intersection(support[x]):
                    raise ValueError(("non-decomposable AND",len(values),x))
                supp=supp.union(support[x])
                val=times(val,values[x])
        else:
            val=ZERO;supp=frozenset()
            for x in children:
                val=plus(val,values[x])
                supp=supp.union(support[x])
            # Determinism of OR is NOT verified by this local support check.
        values.append(val);support.append(supp)
    result=values[-1]
    for lit in fixed:result=times(result,w(lit))
    for group in free:
        if not group:raise ValueError("empty free group")
        pos=ONE;neg=ONE
        for lit in group:
            pos=times(pos,w(lit))
            neg=times(neg,w(-lit))
        result=times(result,plus(pos,neg))
    stats={"nnf_nodes":len(ops),"nnf_edges":sum(len(c) for _,_,c in ops),
           "nnf_original_vars":original_var_count,
           "nnf_simplified_vars":header[2],
           "nnf_mapped_vars":len(seen),
           "nnf_fixed_literals":len(fixed),"nnf_free_groups":len(free),
           "nnf_root_support":len(support[-1]),
           "nnf_or_nodes":sum(t=="O" for t,_,_ in ops),
           "nnf_and_nodes":sum(t=="A" for t,_,_ in ops),
           "nnf_output_mapping_complete":True,
           "nnf_and_decomposability_checked":True,
           "nnf_or_determinism_not_independently_proven":True}
    return result,stats


def gpmc_ddnnf(exe,cnf:str,label,out:Path,timeout=50):
    path=out/(label+".cnf");path.write_text(cnf)
    nnf=out/(label+".nnf")
    args=[str(exe),"-mode=1","-prec=90","-ddnnf",
          "-nnfout="+str(nnf),str(path)]
    start=time.monotonic()
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     text=True,timeout=timeout,check=False)
    (out/(label+".dnnf.stdout")).write_text(p.stdout)
    (out/(label+".dnnf.stderr")).write_text(p.stderr)
    if p.returncode!=0:raise RuntimeError(("GPMC dDNNF failed",p.returncode,p.stderr[-700:]))
    if not nnf.is_file():raise RuntimeError("GPMC did not emit a dDNNF")
    n,weights=parse_weight_cnf(cnf)
    val,stats=parse_evaluate(nnf,n,weights)
    from QuPRS.utils.precision_count import parse_printed_solver_output
    printed=parse_printed_solver_output(p.stdout)
    gap=(abs(val[0]-printed.real),abs(val[1]-printed.imag))
    return {
       "case":label,
       "nnf_sha256":hashlib.sha256(nnf.read_bytes()).hexdigest(),
       "cnf_sha256":hashlib.sha256(cnf.encode()).hexdigest(),
       "wmc_exact_rational_from_nnf_real":compact_rat(val[0]),
       "wmc_exact_rational_from_nnf_imag":compact_rat(val[1]),
       "gpmc_printed_real":compact_rat(printed.real),
       "gpmc_printed_imag":compact_rat(printed.imag),
       "absolute_component_difference_real":compact_rat(gap[0]),
       "absolute_component_difference_imag":compact_rat(gap[1]),
       "wnnf_decimal_input_exact_arithmetic":True,
       "is_original_source_certified":False,
       "nnf_encoding_correctness_certified":False,
       "gpmc_count_arithmetic_certified_if_nnf_is_faithful":True,
       "elapsed":round(time.monotonic()-start,3),
       **stats
    }


def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    from QuPRS import check_equivalence
    from QuPRS.utils import WMC
    from qpe_split_and_source_negative_study import add_non_global_rz
    from precision_followup_v2 import sources,capture_native_gpmc

    records=[]
    with WMC("gpmc") as exe:
        for name,backend,method in [
            ("qpeexact8","rust","hybrid"),
            ("qft16","python","wmc_only"),
        ]:
            l,r,strategy,hashes=sources(name)
            for candidate in ("baseline","self_negative"):
                out=a.output
                left=l.read_text()
                right=r.read_text() if candidate=="baseline" else add_non_global_rz(left)
                if backend=="rust":
                    with capture_native_gpmc(out,name+"-"+candidate):
                        result=check_equivalence(left,right,backend=backend,method=method,
                            strategy=strategy,tool_name="gpmc",timeout=45,
                            approximate_distance_tolerance=1e-8)
                    cnf=(out/("rust-"+name+"-"+candidate+".cnf")).read_text()
                else:
                    result=check_equivalence(left,right,backend=backend,method=method,
                        strategy=strategy,tool_name="gpmc",timeout=45,
                        approximate_distance_tolerance=1e-8)
                    cnf=result.CNF
                if not cnf:raise AssertionError("real CNF absent")
                label=f"{name}-{candidate}"
                start=time.monotonic()
                try:
                    row=gpmc_ddnnf(exe,cnf,label,out)
                    row["status"]="exact_rational_nnf_observed"
                except (ValueError,RuntimeError,subprocess.TimeoutExpired) as e:
                    row={"case":label,"status":"not_verified",
                         "reason":f"{type(e).__name__}: {str(e)[:600]}"}
                row.update({"backend":backend,"method":method,
                            "public_verdict":result.equivalent,
                            "public_printed_verdict":result.wmc_printed_verdict,
                            "public_precision_reason":result.wmc_precision_reason,
                            "qasm_source_hashes":hashes,
                            "expected_self_negative_D":"sin(0.005)" if candidate=="self_negative" else None,
                            "elapsed_end_to_end_circuit":round(time.monotonic()-start,3)})
                records.append(row)
                print("DNNF_EXACT_RESEARCH "+json.dumps(row,sort_keys=True),flush=True)
    (a.output/"dnnf-exact-research.json").write_text(json.dumps(
       {"records":records,"scope":"exact arithmetic on GPMC dDNNF if CNF mapping is valid; independent check of dDNNF determinism lacking",
        "no_production_extra_solver":True},indent=2,sort_keys=True)+"\n")
    assert len(records)==4
    print("FOUR_DNNF_TRIALS_RECORDED",flush=True)


if __name__=="__main__":
    main()

"""Research-only exact printed-CNF WMC arithmetic vs native GPMC.

Families have exact separable weighted counts (rational Gaussian integers),
so no exponentially large enumerator or high-precision-solver oracle is needed.
Each selected working precision is one independent research-only Solver call.
The observed residual is NOT a universal solver error upper bound.
"""
from __future__ import annotations
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import math
import subprocess
import tempfile
import time

from QuPRS.utils import WMC
from QuPRS.utils.precision_count import parse_printed_solver_output

CASES = (
    ("balanced_64",64,0,"balanced"),
    ("balanced_256",256,0,"balanced"),
    ("balanced_512",512,0,"balanced"),
    ("cancel_64",64,2,"real_cancel"),
    ("cancel_256",256,4,"real_cancel"),
    ("cancel_512",512,4,"real_cancel"),
    ("complex_cancel_128",128,2,"complex_cancel"),
)
PRECISIONS = (30,90)


def mul(a,b):
    return (a[0]*b[0]-a[1]*b[1], a[0]*b[1]+a[1]*b[0])


def cnf_and_exact(n,k,kind):
    # Unweighted free variables receive equal positive and negative weights,
    # so their independent contribution is precisely (1/2 + 1/2)=1.
    out=[f"p cnf {n} 0","c t wmc"]
    target=(Fraction(1),Fraction(0))
    delta=Fraction(1,10**20)
    for i in range(1,n+1):
        if i<=k and kind=="real_cancel":
            pos=(Fraction(1),Fraction(0))
            neg=(-Fraction(1)+delta,Fraction(0))
        elif i<=k and kind=="complex_cancel":
            pos=(Fraction(1),Fraction(1))
            neg=(-Fraction(1)+delta,-Fraction(1))
        else:
            pos=(Fraction(1,2),Fraction(0))
            neg=(Fraction(1,2),Fraction(0))
        # All selected decimal fractions terminate exactly in base 10.
        def decimal_weight(value):
            with localcontext() as ctx:
                ctx.prec=80
                return format(Decimal(value.numerator)/Decimal(value.denominator),"f")
        out.append(f"c p weight {i} {decimal_weight(pos[0])} {decimal_weight(pos[1])} 0")
        out.append(f"c p weight -{i} {decimal_weight(neg[0])} {decimal_weight(neg[1])} 0")
        target=mul(target,(pos[0]+neg[0],pos[1]+neg[1]))
    return "\n".join(out)+"\n",target


def decimal_scientific(f):
    with localcontext() as ctx:
        ctx.prec=24
        return str(Decimal(f.numerator)/Decimal(f.denominator))


def trial(name,n,k,kind,precision,out,exe):
    cnf,exact=cnf_and_exact(n,k,kind)
    path=out/(name+".cnf")
    path.write_text(cnf)
    args=[str(exe),"-mode=1",f"-prec={precision}",str(path)]
    t=time.monotonic()
    p=subprocess.run(args,capture_output=True,text=True,timeout=15,check=False)
    elapsed=time.monotonic()-t
    (out/f"{name}-p{precision}.stdout").write_text(p.stdout)
    (out/f"{name}-p{precision}.stderr").write_text(p.stderr)
    row={
        "case":name,"nvars":n,"n_cancel_factors":k,
        "kind":kind,"digits":precision,
        "cnf_sha256":hashlib.sha256(cnf.encode()).hexdigest(),
        "native_returncode":p.returncode,"native_wall_seconds":round(elapsed,4),
        "reference_scope":"exact rational weighted count of printed separable CNF",
        "reference_real":decimal_scientific(exact[0]),
        "reference_imag":decimal_scientific(exact[1]),
        "source_or_solver_certified":False,
    }
    if p.returncode!=0:
        row["observation"]="solver_nonzero"
        return row
    observed=parse_printed_solver_output(p.stdout)
    error=(observed.real-exact[0],observed.imag-exact[1])
    row.update({
        "observation":"native_count",
        "native_real":decimal_scientific(observed.real),
        "native_imag":decimal_scientific(observed.imag),
        "observed_component_abs_error_real":decimal_scientific(abs(error[0])),
        "observed_component_abs_error_imag":decimal_scientific(abs(error[1])),
        "native_printed_halfunit_real":decimal_scientific(observed.real_print_half_unit),
        "native_printed_halfunit_imag":decimal_scientific(observed.imag_print_half_unit),
        "conditional_n_only_error_model_log2":2*n+20-(int(precision*math.log2(10))-2),
    })
    return row


def run(out):
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    with WMC("gpmc") as exe:
        for name,n,k,kind in CASES:
            for precision in PRECISIONS:
                try:
                    row=trial(name,n,k,kind,precision,out,exe)
                except subprocess.TimeoutExpired:
                    row={"case":name,"digits":precision,"observation":"native_timeout"}
                except Exception as e:
                    row={"case":name,"digits":precision,"observation":"experiment_error",
                         "error":f"{type(e).__name__}: {e}"}
                results.append(row)
                print("EXACT_SEPARABLE_WMC "+json.dumps(row,sort_keys=True),flush=True)
    (out/"separable-exact-comparison.json").write_text(
        json.dumps({"results":results,
        "no_universal_arithmetic_certificate":True,
        "solver_calls":len(results),
        "exact_reference_source":"printed-decimal-weight CNF; independent product",
        },indent=2,sort_keys=True)+"\n")
    assert len(results)==14
    # Demand actual observations for the balanced/real cancellation controls;
    # report complex cancellation separately if the solver rejects signs.
    required=[r for r in results if r["kind"]!="complex_cancel"]
    assert all(r["observation"]=="native_count" for r in required), required
    # Balanced exact 1/2+1/2 count should be exactly 1 at all n,precision.
    for r in results:
        if r.get("kind")=="balanced":
            assert r["observed_component_abs_error_real"]=="0",r
            assert r["observed_component_abs_error_imag"]=="0",r
    print("EXACT_SEPARABLE_WMC_OBSERVATIONS_PASS",len(results),flush=True)


if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    run(ap.parse_args().output)

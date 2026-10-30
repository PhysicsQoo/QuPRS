"""Fixed-CNF exact a posteriori proof of original GPMC MPFR count error.

The independently checked original CNF <=> emitted d-DNNF for the two
QFT16 source-pinned pairs, and the small-QPE controls, establish that
exact rational evaluation of the d-DNNF is the exact WMC over the
printed CNF decimals. Evaluate it with Fraction, parse the ACTUAL
original MPFR binary result from the same single-run GPMC stdout
probe, and take the exact rational difference.

A POSTERIORI, FIXTURE-SPECIFIC CERTIFICATION ONLY: does not provide a
general solver forward-error bound or change a public verifier.
"""
from __future__ import annotations
import argparse
from decimal import Decimal,localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from dnnf_exact_arithmetic_research import parse_weight_cnf,parse_evaluate

CASES={
 "qpeexact8-baseline":(22,"34d38d1718f1796d6af46cfa079aa2093aa00e5997f5b428e8af4b1672a35ee7"),
 "qpeexact8-self_negative":(16,"b965d82a7bf4900350a2cbef028ff51506b9bb0f426859c1be9432207872d2d7"),
 "qft16-baseline":(102,"20ee9e55eb1fc644d08daf130d180ded46f06f67897fa46f57b4f4ef4ef7f8f1"),
 "qft16-self_negative":(96,"8e65b1d5cfdc99c4d980bc4fea24162afc4f9583e0ebf17686fc8a9f1bc6555c")
}
def fraction_from_mpfr_binary(bits,exp):
    sign=-1 if bits.startswith("-") else 1
    bits=bits.lstrip("-")
    if not bits or any(x not in "01" for x in bits):
        raise ValueError("invalid MPFR exact binary mantissa")
    return Fraction(sign*int(bits,2))*Fraction(2)**(int(exp)-len(bits))
def scientific(v):
    if v==0:return "0"
    with localcontext() as c:
        c.prec=46
        return format(Decimal(v.numerator)/Decimal(v.denominator),".23E")
def result_row(source,original,case,twice,sha,known):
    cpath=source/(case+".cnf")
    npath=source/(case+".nnf")
    if hashlib.sha256(cpath.read_bytes()).hexdigest()!=sha:
        raise AssertionError(("original source CNF changed",case))
    if known["original_cnf_sha256"]!=sha:
        raise AssertionError(("source and run mismatched",case))
    if not (known["decimal_input_to_p299_checked"] and known["p299_to_stdout_checked"]):
        raise AssertionError(("native MPFR I/O contract incomplete",case))
    for key,value in {"rnd":"0","uf":"0","of":"0","nan":"0","erange":"0",
                      "realnum":"1","imagnum":"1","rprec":"299","iprec":"299"}.items():
        if known["native_MPFR_status"].get(key)!=value:
            raise AssertionError(("native MPFR runtime not normal",case,key))
    stderr=(original/(case+".stderr")).read_text()
    evid=[line.split("QUPRS_MPFR_AUDIT ",1)[1]
          for line in stderr.splitlines() if "QUPRS_MPFR_AUDIT " in line]
    if len(evid)!=known["native_complex_stream_events"]:
        raise AssertionError(("stream events mismatch",case,len(evid)))
    data=dict(x.split("=",1) for x in evid[-1].split())
    actual=(fraction_from_mpfr_binary(data["rbits"],data["rex"]),
            fraction_from_mpfr_binary(data["ibits"],data["iex"]))
    n,weights=parse_weight_cnf(cpath.read_text())
    exact,stats=parse_evaluate(npath,n,weights)
    difference=(actual[0]-exact[0],actual[1]-exact[1])
    dreal,dimag=abs(difference[0]),abs(difference[1])
    norm=Fraction(2)**(twice//2)
    normalized_l1=(dreal+dimag)/norm
    # No floating-point in comparison or normalization.
    row={
        "case":case,
        "cnf_sha256":sha,
        "nnf_sha256":hashlib.sha256(npath.read_bytes()).hexdigest(),
        "native_mpfr_result_binary_sha256":hashlib.sha256(evid[-1].encode()).hexdigest(),
        "exact_NNF_nodes":stats["nnf_nodes"],
        "numerical_weights_in_CNF":len(weights),
        "mpfr_precision_bits":299,
        "actual_vs_exact_rational_real_component_gap":scientific(dreal),
        "actual_vs_exact_rational_imag_component_gap":scientific(dimag),
        "actual_vs_exact_rational_complex_L1_gap":scientific(dreal+dimag),
        "actual_vs_exact_rational_normalized_complex_L1_gap":scientific(normalized_l1),
        "exact_rational_difference_measured_not_heuristic":True,
        "fixed_cnf_to_nnf_boolean_equality_certified_separately":True,
        "independent_rational_NNF_arithmetic":True,
        "full_general_solver_error_theorem_not_proven":True,
        "runtime_gpmc_solves_in_this_replay":0,
    }
    print("GPMC_MPFR_EXACT_ERROR_ORACLE "+json.dumps(row,sort_keys=True),flush=True)
    return row
def main(args):
    args.output.mkdir(parents=True,exist_ok=True)
    data=json.loads((args.binary/"gpmc-input-output-mpfr-contract.json").read_text())
    known={x["case"]:x for x in data["records"]}
    if set(known)!=set(CASES):raise ValueError("incomplete binary result evidence")
    rows=[result_row(args.source,args.binary,c,twice,sha,known[c])
          for c,(twice,sha) in CASES.items()]
    (args.output/"gpmc-exact-p299-error-fixed-cases.json").write_text(
        json.dumps({"cases":rows,"not_general_solver_certificate":True,
                    "no_gpmc_invocations":True,
                    "reference_independent_fraction_WMC":True},indent=2,sort_keys=True)+"\n")
    assert len(rows)==4
    print("ALL_FOUR_GPMC_MPFR_FIXED_ERROR_BOUNDS_EXACT_RATIONAL",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--binary",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    main(p.parse_args())

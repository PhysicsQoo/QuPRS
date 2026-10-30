"""Research-only source QASM -> Qiskit float -> Python PathSum div_pi proof.

No production modification. For QFT16 original and transpiled actual QASM,
confirm all RX/RY/RZ Qiskit float angles are converted by the exact installed
QuPRS.utils.util.div_pi function to rational coefficients and then enclose
source angle minus (rational coefficient)*pi with directed MPFR 384-bit.

Under standard RX/RY/RZ gate semantics, sum |Delta theta|/2 bounds
unitary operator error from *both* QASM parse and div_pi rounding.
This does not prove entire PathSum gate implementation.
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
import numpy as np
from qiskit import qasm2
from QuPRS.utils.util import div_pi
from qft_qasm_angle_provenance_study import (
 INPUT_HASHES,GATE_LINE,OPS,exact_source_angle,interval_mpfr
)
from mpfr_directed_phase_bound import Directed

def d(x):
    with localcontext() as c:
        c.prec=44
        return format(Decimal(x.numerator)/Decimal(x.denominator),".19E")

def analyze(path,mp):
    data=path.read_text()
    lines=[]
    for raw in data.splitlines():
        s=raw.split("//",1)[0].strip()
        if not s or s in ('OPENQASM 2.0;','include "qelib1.inc";') or s.startswith(("qreg ","creg ")):continue
        match=GATE_LINE.fullmatch(s)
        if not match:raise ValueError(("unrecognized QASM gate",s))
        lines.append(match.groups())
    circuit=qasm2.loads(data)
    if len(lines)!=len(circuit.data):raise ValueError("Qiskit gate count mismatch")
    total=Fraction(0);greatest=Fraction(0);samples=[];maxidx=None;count=0
    for i,((name,expr,oper),instruction) in enumerate(zip(lines,circuit.data)):
        if name!=instruction.operation.name:raise ValueError(("gate identity mismatch",i,name))
        if name not in OPS:continue
        theta=instruction.operation.params[0]
        if not isinstance(theta,float):raise ValueError(("unbound Qiskit gate angle",i))
        cycle,remainder=exact_source_angle(expr)
        original_lo,original_hi=interval_mpfr((cycle,remainder),mp)
        converted=div_pi(theta)
        p,q=converted.as_numer_denom()
        rational=Fraction(int(p),int(q))
        numerical=Fraction.from_float(float(theta/np.pi))
        if rational!=numerical:
            raise AssertionError(("actual Python div_pi differs from measured ratio",name,i))
        mapped_lo,mapped_hi=interval_mpfr((rational,Fraction(0)),mp)
        bound=max(abs(original_lo-mapped_hi),abs(original_hi-mapped_lo))
        total+=bound;count+=1
        if bound>=greatest:
            greatest=bound;maxidx=i
        if bound>Fraction(1,10**13):
            samples.append({"gate_index":i,"gate":name,"source_angle":expr,
                            "source_to_pathsum_gap_upper":d(bound)})
    return {
        "source_qasm_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "rotation_count":count,"actual_Python_div_pi_invoked_per_rotation":True,
        "float_ratio_round_trip_to_exact_pathsum_rational_verified":True,
        "max_source_angle_to_PathSum_radian_error":d(greatest),
        "index_of_worst_gate":maxidx,
        "sum_source_to_PathSum_radian_errors":d(total),
        "operator_norm_upper_via_gate_telescope":d(total/2),
        "many_large_gap_sample":samples[:15],
    },total/2

def main(out):
    from precision_followup_v2 import sources
    left,right,_,hashes=sources("qft16")
    if tuple(hashes)!=INPUT_HASHES:raise AssertionError(("QASM source identity moved",hashes))
    mp=Directed()
    try:
        first,a=analyze(left,mp)
        second,b=analyze(right,mp)
    finally:
        mp.close()
    total=a+b
    report={
        "native_source":first,"transpiled_source":second,
        "QASM_to_Python_PathSum_div_pi_operator_bound_both":d(total),
        "epsilon_distance":1e-8,
        "source_conversion_bound_less_than_epsilon":total<Fraction(1,10**8),
        "all_rotations_preserve_QASM_to_Qiskit_gate_order":True,
        "only_angle_div_pi_transport_certified":True,
        "global_phase_and_gate_matrix_implementation_not_proven":True,
        "Qiskit_transpile_ideal_equivalence_not_proven":True,
        "no_production_code_change":True,
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"qft16-qasm-to-pathsum-divpi-source-gap.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("QASM_TO_PATHSUM_DIV_PI_PROVENANCE "+json.dumps({
        "native_rotations":first["rotation_count"],
        "transpiled_rotations":second["rotation_count"],
        "native_operator_upper":first["operator_norm_upper_via_gate_telescope"],
        "transpiled_operator_upper":second["operator_norm_upper_via_gate_telescope"],
        "both_operator_upper":d(total),
        "less_than_distance_epsilon":report["source_conversion_bound_less_than_epsilon"],
        "floating_angle_ratio_preserved_as_exact_SymEngine_rational":True
    },sort_keys=True),flush=True)
    if not report["source_conversion_bound_less_than_epsilon"]:
        raise AssertionError("source to PathSum angle uncertainty too large")
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    main(parser.parse_args().output)

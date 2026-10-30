"""Research-only QASM -> Qiskit numeric rotation angle provenance (QFT16).

For each rotation gate, parse original QASM2 textual angle as an exact
a*pi+b with rational coefficients; compare with the actual Qiskit binary64
rotation parameter by outward-rounding MPFR interval arithmetic.
The sum of half-angle errors bounds the circuit's operator-norm error
from source-angle rounding under ideal RX/RY/RZ semantics. It does NOT
certify Qiskit transpilation or the internal PathSum gate implementation.
"""
from __future__ import annotations
import argparse
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import sympy as sp
from qiskit import qasm2
from mpfr_directed_phase_bound import Directed, DOWN, UP

INPUT_HASHES=(
    "39b6889497a4e98098b6bb2b4563ace2fb660f4cc3fe8d0763d3f69fc200d865",
    "aa85188d731454bd85b0fe2ae089ab8e6b812501730eee5f1651ac11d7b7fcbc",
)
OPS=("rx","ry","rz")
GATE_LINE=re.compile(r"^\s*(\w+)(?:\(([^;]*)\))?\s+([^;]+);\s*$")

def as_decimal(x):
    with localcontext() as c:
        c.prec=45
        return format(Decimal(x.numerator)/Decimal(x.denominator),".20E")

def exact_source_angle(token):
    ex=sp.sympify(token.strip(),locals={"pi":sp.pi},
                  rational=True,evaluate=True)
    if ex.free_symbols or ex.has(sp.Float) or not ex.is_real:
        raise ValueError(("nonexact-source-angle",token,ex))
    ex=sp.expand(ex)
    coeff=sp.simplify(ex.coeff(sp.pi))
    remainder=sp.simplify(ex-coeff*sp.pi)
    if not (coeff.is_Rational and remainder.is_Rational):
        raise ValueError(("source-angle-not-a-pi-rational-plus-rational",token,ex))
    return Fraction(int(coeff.p),int(coeff.q)),Fraction(int(remainder.p),int(remainder.q))

def interval_mpfr(angle,mp):
    aa,bb=angle
    pi=(mp.new(),mp.new())
    mp.lib.mpfr_const_pi(__import__("ctypes").byref(pi[0]),DOWN)
    mp.lib.mpfr_const_pi(__import__("ctypes").byref(pi[1]),UP)
    interval=mp.add(mp.mul(mp.rational(aa),pi),mp.rational(bb))
    return mp.exact_binary_fraction(interval[0]),mp.exact_binary_fraction(interval[1])

def audit_one(path,mp):
    text=path.read_text()
    s=hashlib.sha256(path.read_bytes()).hexdigest()
    lines=[]
    for raw in text.splitlines():
        line=raw.split("//",1)[0].strip()
        if not line or line in ('OPENQASM 2.0;','include "qelib1.inc";') or line.startswith(("qreg ","creg ")):
            continue
        m=GATE_LINE.fullmatch(line)
        if not m:raise ValueError(("unknown QASM statement",line))
        gate,param,operand=m.groups()
        if gate in OPS and param is None:raise ValueError(("missing rotation",line))
        lines.append((gate,param,operand))
    qc=qasm2.loads(text)
    if len(lines)!=len(qc.data):
        raise AssertionError(("gate count mismatched source->Qiskit",len(lines),len(qc.data)))
    weights=[];err_sum=Fraction(0);maximum=Fraction(0);kind=Counter()
    for k,((g,param,oper),ins) in enumerate(zip(lines,qc.data)):
        op=ins.operation
        if g!=op.name:raise AssertionError(("gate identity changed",k,g,op.name))
        if g not in OPS:
            if param is not None:raise ValueError(("parameterized nonrotation needs separate handling",g,param))
            continue
        if len(op.params)!=1 or not isinstance(op.params[0],float):
            raise ValueError(("Qiskit parameter not Python float",k,g,op.params))
        a,b=exact_source_angle(param)
        lo,hi=interval_mpfr((a,b),mp)
        parsed=Fraction.from_float(op.params[0])
        gap=max(abs(parsed-lo),abs(parsed-hi))
        maximum=max(maximum,gap)
        err_sum+=gap
        typ=("rational_pi" if a else "decimal_radians")
        kind[typ]+=1
        weights.append({"gate_index":k,"gate":g,"source_angle":param,
                        "source_kind":typ,
                        "qiskit_float_hex":op.params[0].hex(),
                        "upper_angle_gap_radians":as_decimal(gap)})
    return {
        "source_qasm_sha256":s,"gate_count":len(lines),
        "rotation_count":len(weights),"rotation_kinds":dict(kind),
        "max_source_to_qiskit_binary64_radian_error":as_decimal(maximum),
        "sum_of_absolute_rotation_angle_errors":as_decimal(err_sum),
        "source_to_qiskit_op_norm_upper_via_half_angle":as_decimal(err_sum/2),
        "gate_name_sequence_verified":True,
        "all_rotations_are_rx_ry_rz":True,
        "qasm_to_qiskit_angle_interval_proven":True,
        "gate_matrix_semantics_not_independently_certified":True,
        "qiskit_transpiler_ideal_semantics_not_independently_certified":True,
        "rotations":weights,
    },err_sum/2

def main(out):
    from precision_followup_v2 import sources
    left,right,_,hashes=sources("qft16")
    if tuple(hashes)!=INPUT_HASHES:raise AssertionError(("unexpected QASM source pair",hashes))
    mp=Directed()
    try:
        a,ea=audit_one(left,mp)
        b,eb=audit_one(right,mp)
    finally:
        mp.close()
    total=ea+eb
    report={
        "native_source":a,"transpiled_source":b,
        "both_QASM_to_Qiskit_operator_norm_triangle_upper":as_decimal(total),
        "both_QASM_to_Qiskit_D_proj_upper_conditional_gate_matrix_identity":as_decimal(total),
        "epsilon_distance":1e-8,
        "pair_source_rounding_well_below_1e-8":total<Fraction(1,10**8),
        "QASM_input_to_PathSum_phase_arithmetic_NOT_proven":True,
        "transpiled_QASM_exactly_equal_to_native_QASM_NOT_proven":True,
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"qft16-qasm-to-qiskit-directed-provenance.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n")
    slim={"source_rotation_count":a["rotation_count"],
          "transpiled_rotation_count":b["rotation_count"],
          "source_rotation_kinds":a["rotation_kinds"],
          "transpiled_rotation_kinds":b["rotation_kinds"],
          "source_operator_bound":a["source_to_qiskit_op_norm_upper_via_half_angle"],
          "transpiled_operator_bound":b["source_to_qiskit_op_norm_upper_via_half_angle"],
          "total_operator_bound":as_decimal(total),
          "epsilon_distance":1e-8,
          "conditional_ideal_gate_semantics":True,
          "all_Qiskit_rotation_params_matched_source_gate_order":True}
    print("QASM_QFT16_DIRECTED_ANGLE_PROVENANCE "+json.dumps(slim,sort_keys=True),flush=True)
    if total>=Fraction(1,10**8):raise AssertionError("source rounding not negligible")
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--output",type=Path,required=True)
    main(a.parse_args().output)

"""Independent high-precision oracle for Rust's *actual* recorded phase weights.

This reads focused cargo-test stdout from the experiment branch. Values are
exact source phase rationals + f64 bit patterns emitted by the native encoder.
Clifford quarter cycles have an exact algebraic weight in {1,-1,i,-i}.
A numerical residual is not a complete source-to-WMC error certificate.
"""
from __future__ import annotations
from collections import defaultdict
from fractions import Fraction
import json
from pathlib import Path
import struct
from mpmath import mp


def f64_bits_to_mpf(bits):
    binary=struct.unpack("!d",int(bits).to_bytes(8,"big"))[0]
    rational=Fraction.from_float(binary)
    return mp.mpf(rational.numerator)/rational.denominator


def run(log,out):
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    cases={}
    for line in Path(log).read_text().splitlines():
        if "SOURCE_WEIGHT_AUDIT\t" in line:
            parts=line[line.index("SOURCE_WEIGHT_AUDIT\t"):].split("\t")
            if len(parts)!=9: raise ValueError(parts)
            _,case,var,cn,cd,rn,rd,re_bits,im_bits=parts
            rows.append((case,int(var),Fraction(int(cn),int(cd)),
                         Fraction(int(rn),int(rd)),re_bits,im_bits))
        elif "SOURCE_WEIGHT_CASE\t" in line:
            parts=line[line.index("SOURCE_WEIGHT_CASE\t"):].split("\t")
            if len(parts)!=4: raise ValueError(parts)
            cases[parts[1]]=(int(parts[2]),int(parts[3]))
    if not rows or "s_gate" not in cases or "t_gate" not in cases or "z_gate" not in cases:
        raise AssertionError(("Missing native Rust test cases",len(rows),cases))
    records=[]
    with mp.workdps(120):
        for case,var,cycle,radians,re_bits,im_bits in rows:
            angle=mp.mpf(2)*(mp.pi*mp.mpf(cycle.numerator)/cycle.denominator
                 + mp.mpf(radians.numerator)/radians.denominator)
            actual=mp.mpc(f64_bits_to_mpf(re_bits),f64_bits_to_mpf(im_bits))
            phase=cycle % 1
            exact_quarter=None
            if not radians and (4*phase).denominator==1:
                values=[mp.mpc(1,0),mp.mpc(0,1),mp.mpc(-1,0),mp.mpc(0,-1)]
                exact_quarter=values[int(phase*4)]
                reference=exact_quarter
            else:
                reference=mp.mpc(mp.cos(angle),mp.sin(angle))
            gap=abs(actual-reference)
            abs_defect=abs(abs(actual)**2-1)
            records.append({
                "case":case,"weight_variable":var,
                "source_phase_pi_cycles":str(cycle),
                "source_radians_coefficient":str(radians),
                "is_exact_clifford_quarter_cycle":exact_quarter is not None,
                "real_binary64_bits":re_bits,
                "imag_binary64_bits":im_bits,
                "actual_complex_weight_f64":[mp.nstr(actual.real,35),mp.nstr(actual.imag,35)],
                "independent_reference":[mp.nstr(reference.real,35),mp.nstr(reference.imag,35)],
                "observed_weight_complex_abs_gap":mp.nstr(gap,45),
                "observed_unit_magnitude_squared_defect":mp.nstr(abs_defect,45),
                "exact_quarter_turn_removes_this_weight_gap":exact_quarter is not None,
                "certifies_complete_WMC_error":False,
            })
    by=defaultdict(list)
    for r in records:by[r["case"]].append(r)
    for case,(terms,weights) in cases.items():
        if terms!=weights or len(by[case])!=weights:raise AssertionError((case,terms,weights,len(by[case])))
    for case,items in by.items():
        print("NATIVE_PHASE_FIDELITY "+json.dumps({"case":case,
            "weights":len(items),
            "quarter_turns":sum(r["is_exact_clifford_quarter_cycle"] for r in items),
            "max_gap":max((mp.mpf(r["observed_weight_complex_abs_gap"]) for r in items),default=mp.mpf(0)).__str__(),
        },sort_keys=True),flush=True)
    result={"records":records,"case_counts":cases,
       "reference":"actual native source rational coefficients; algebraic quarter cycles or 120-digit mpmath trig",
       "scope":"experimental-branch Rust WMC generator, not certified entire dev pipeline",
       "certifies_solver_or_source_error":False}
    (out/"rust-native-source-weight-gaps.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("RUST_NATIVE_PHASE_ORACLE_PASS",len(records),flush=True)


if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--log",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    opts=ap.parse_args()
    run(opts.log,opts.output)

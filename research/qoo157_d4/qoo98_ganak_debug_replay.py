"""QOO-98 independent Ganak debug-CNF native reread science.

Only print-limited count/factor reconstruction. Weighted residual equivalence,
projection equivalence and high-precision arithmetic are NOT established.
The original pinned binary and diagnostic CNFs are immutable inputs.
No performance timing may be reported from this script.
"""
from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path
from decimal import Decimal, localcontext
from hashlib import sha256
from qoo98_ganak_native_mode6_admission import OUTPUT, half

ARMS={
    "qaoa7_neq":("arjun0_puura0","arjun1_puura0","arjun1_puura1"),
    "qft16_eq":("arjun0_puura0","arjun1_puura1"),
}
FACTOR=re.compile(r"^c MUST MULTIPLY BY ([+-]?\d+(?:\.\d+)?[eE][+-]\d+) ([+-]) ([+-]?\d+(?:\.\d+)?[eE][+-]\d+)i 0$")
def hash_data(raw):return sha256(raw).hexdigest()

def load_debug(path,prior):
    raw=path.read_bytes()
    assert hash_data(raw)==prior["debug_structure"]["sha256"]
    lines=raw.decode("utf-8").splitlines()
    factors=[line for line in lines if line.startswith("c MUST MULTIPLY BY ")]
    assert len(factors)==1 and (m:=FACTOR.fullmatch(factors[0]))
    real,sign,imag=m.groups()
    signed_imag=Decimal(imag)*(1 if sign=="+" else -1)
    weight_lines=[s for s in lines if s.startswith("c p weight ")]
    assert weight_lines
    assert hash_data(("\n".join(weight_lines)+"\n").encode())==prior["debug_structure"]["weight_lines_sha256"]
    seen=set()
    for w in weight_lines:
        q=w.split()
        assert len(q)==8 and q[:3]==["c","p","weight"] and q[5] in ("+","-") and q[6].endswith("i") and q[-1]=="0"
        assert int(q[3]) not in seen
        seen.add(int(q[3]))
        assert Decimal(q[4]).is_finite() and Decimal(q[6][:-1]).is_finite()
    proj={}
    for typ in ("show","optshow","exist"):
        rows=[s for s in lines if s.startswith("c p "+typ+" ")]
        assert len(rows)==1
        p=rows[0].split()
        assert p[-1]=="0"
        indices=list(map(int,p[3:-1]))
        assert len(indices)==len(set(indices)) and all(i>0 for i in indices)
        proj[typ]={"size":len(indices),"sha256":hash_data(rows[0].encode())}
    return {
        "sha256":hash_data(raw),"multiplier_line":factors[0],
        "multiplier_real_str":real,"multiplier_imag_str":imag,
        "multiplier_complex_printed":[str(Decimal(real)),str(signed_imag)],
        "projection":proj,"weight_entries":len(weight_lines),
        "weight_sha256":hash_data(("\n".join(weight_lines)+"\n").encode()),
        "debug_input_weight_rounding_uncertified":True
    },(Decimal(real),signed_imag)

def run_pinned(binary,debug):
    cp=subprocess.run([str(binary),"--mode=6","--mpfrprec=127",
        "--threads=1","--arjun","0","--puura","0",str(debug)],
        text=True,capture_output=True,timeout=32,check=False)
    match=[m for line in cp.stdout.splitlines() if (m:=OUTPUT.fullmatch(line))]
    data={"status":"NATIVE_READER_UNRECOGNIZED","returncode":cp.returncode,
          "stdout_sha256":hash_data(cp.stdout.encode()),
          "stderr_sha256":hash_data(cp.stderr.encode()),
          "stdout_tail":cp.stdout[-900:],"stderr_tail":cp.stderr[-900:]}
    if cp.returncode==0 and len(match)==1:
        data["status"]="NATIVE_PRINTED_COMPLEX"
        data["real"],data["imag"]=match[0].groups()
    return data

def reconstruct(native,factor,meta,original):
    with localcontext() as ctx:
        ctx.prec=110
        a,b=Decimal(native["real"]),Decimal(native["imag"])
        c,d=factor
        reconstructed=(a*c-b*d,a*d+b*c)
        observed=(Decimal(original["real"]),Decimal(original["imag"]))
        ua,ub=half(native["real"]),half(native["imag"])
        uc,ud=half(meta["multiplier_real_str"]),half(meta["multiplier_imag_str"])
        error=(
           abs(c)*ua+abs(d)*ub+abs(a)*uc+abs(b)*ud+ua*uc+ub*ud,
           abs(d)*ua+abs(c)*ub+abs(b)*uc+abs(a)*ud+ua*ud+ub*uc
        )
        budget=tuple(error[i]+half((original["real"],original["imag"])[i])
                     for i in (0,1))
        differences=tuple(abs(reconstructed[i]-observed[i]) for i in (0,1))
    return {"printed_count_times_printed_factor":[str(x) for x in reconstructed],
        "original_native_print":[original["real"],original["imag"]],
        "delta":[str(x) for x in differences],
        "printed_count_factor_and_reference_half_ulp_budget":[str(x) for x in budget],
        "within_print_only_budget":[differences[i]<=budget[i] for i in (0,1)],
        "budget_excludes_each_debug_literal_weight_roundoff":True,
        "full_weighted_WMC_equivalence_certified":False}

def main():
    p=argparse.ArgumentParser()
    for n in ("binary","source-science","native-report","intermediate-report","debug-dir","out"):
        p.add_argument("--"+n,type=Path,required=True)
    args=p.parse_args()
    source=json.loads(args.source_science.read_text())
    native=json.loads(args.native_report.read_text())
    audit=json.loads(args.intermediate_report.read_text())
    assert source["complete"] is True
    assert native["status"]=="NATIVE_PRINT_SCREEN_PASS_PRECISION_LIMITED"
    assert hash_data(args.binary.read_bytes())==native["official_binary_sha256"]==audit["binary_sha256"]
    assert audit["status"]=="ALL_FIVE_NATIVE_COUNT_SCREENS_CONCORDANT"
    result={"status":"INCOMPLETE","binary_sha256":native["official_binary_sha256"],
       "requested_mpfr_bits":127,"mode6_print_significant_digits":9,
       "no_timing_observations":True,"full_residual_WMC_certified":False,
       "cross_solver_replay_admission":"NOT_CERTIFIED",
       "runs":{}}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    for case,arms in ARMS.items():
        original=native["source_cases"][case]
        assert original["native"]["status"]=="PRINT_CONCORDANT_UNCERTIFIED"
        assert original["source_sha256"]==source["cases"][case]["same_cnf_sha256"]
        for arm in arms:
            archived=audit["cases"][case][arm]
            assert archived["count_status"]=="PRINT_CONCORDANT_UNCERTIFIED"
            debug=args.debug_dir/case/(arm+".debug.cnf")
            meta,factor=load_debug(debug,archived)
            row={"original_source_sha256":original["source_sha256"],
                "debug":meta,"input_replay_weighted_semantic_status":"NOT_CERTIFIED"}
            try:
                rerun=run_pinned(args.binary,debug)
            except subprocess.TimeoutExpired:
                rerun={"status":"BOUNDED_32S_REPLAY_TIMEOUT_NOT_PERFORMANCE"}
            row["native_reader"]=rerun
            if rerun["status"]=="NATIVE_PRINTED_COMPLEX":
                row["reconstruction"]=reconstruct(rerun,factor,meta,original["native"])
            result["runs"].setdefault(case,{})[arm]=row
            args.out.write_text(json.dumps(result,indent=2)+"\n")
    verdict=[]
    for arms in result["runs"].values():
        for row in arms.values():
            obs=row["native_reader"]["status"]
            if obs=="NATIVE_PRINTED_COMPLEX":
                ok=row["reconstruction"]["within_print_only_budget"]
                obs="PRINT_FACTOR_SCREEN_PASS_WEIGHTS_UNBOUNDED" if all(ok) else "PRINT_FACTOR_SCREEN_DISAGREEMENT"
            verdict.append(obs)
    result["verdicts"]={i:verdict.count(i) for i in sorted(set(verdict))}
    result["status"]="NATIVE_DEBUG_READER_EVIDENCE_RECORDED"
    args.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"verdicts":result["verdicts"],
        "cross_solver_replay_admission":"NOT_CERTIFIED"}))

if __name__=="__main__":main()

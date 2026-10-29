"""Native weight-precision A/B on unmodified Rust-generated CNF and RR circuit events.

MP candidates here are **research-only mpmath trig replacement** in real Rust
CNF files; they are NOT a production native-Rust MPFR implementation. Every
weighted count is computed by the existing GPMC/Ganak executable.
"""
from __future__ import annotations

from contextlib import ExitStack
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from mpmath import mp
from qiskit import QuantumCircuit

from QuPRS import check_equivalence, config
from QuPRS.interface.ps2wmc import run_wmc
from QuPRS.pathsum import reduction as RED

OUT=Path("focused-tolerance-evidence")
OUT.mkdir(exist_ok=True)
LOG=OUT/"native-rust-weight.log"
RAW=OUT/"native-high-precision-weight-counts.jsonl"
SUMMARY=OUT/"native-high-precision-weight-summary.json"

def record(obj):
    with RAW.open("a") as f:
        f.write(json.dumps(obj, sort_keys=True, default=str)+"\n")
    print("NATIVE_WEIGHT_RR "+json.dumps({
        key:obj.get(key) for key in
        ("group","label","solver","variant","status","error","event_total")
    },sort_keys=True),flush=True)

def rational(pair):
    n,d=map(int,pair)
    return mp.mpf(n)/mp.mpf(d)

def parse_rust_test_log():
    cases={}
    current=None
    for raw in LOG.read_text().splitlines():
        if "RUST_PHASE\t" in raw:
            _, tail=raw.split("RUST_PHASE\t",1)
            label,source,cn,cd,rn,rd,mono=tail.split("\t",6)
            obj=cases.setdefault(label,{"phases":{},"cnfs":{},"terms":[]})
            obj["terms"].append(((cn,cd),(rn,rd),mono))
        elif "RUST_CNF_START\t" in raw:
            assert current is None
            label,solver=raw.split("RUST_CNF_START\t",1)[1].split("\t")
            current=(label,solver,[])
        elif "RUST_CNF_LINE\t" in raw and current:
            current[2].append(raw.split("RUST_CNF_LINE\t",1)[1])
        elif "RUST_CNF_END\t" in raw:
            assert current is not None
            label,solver=raw.split("RUST_CNF_END\t",1)[1].split("\t")
            assert (label,solver)==current[:2]
            cases[label]["cnfs"][solver]="\n".join(current[2])+"\n"
            current=None
    assert current is None
    expected={"sub_f64_defect","resolved_control","literal_alias_a","literal_alias_b"}
    assert set(cases)==expected,(set(cases),expected)
    for label,case in cases.items():
        assert set(case["cnfs"])=={"gpmc","ganak"}
        assert len(case["terms"])==2
        # Derive actual phase-var IDs from real CNF and 110-digit source
        # phases. The variable IDs are NOT the ordinal index of phase terms:
        # a monomial can allocate Tseitin input variables between them.
        # A two-term exhaustive assignment is deterministic and cheap.
        with mp.workdps(110):
            expected=[]
            for pi_ratio,rad,_ in case["terms"]:
                angle=2*mp.pi*rational(pi_ratio)+2*rational(rad)
                expected.append(mp.mpc(mp.cos(angle),mp.sin(angle)))
            observed=[]
            for line in case["cnfs"]["gpmc"].splitlines():
                if line.startswith("c p weight "):
                    t=line.split()
                    variable=int(t[3])
                    if variable>0:
                        observed.append((variable,mp.mpc(mp.mpf(t[4]),mp.mpf(t[5]))))
            assert len(observed)==len(expected),(label,observed)
            assignments=[
                (mp.fsum(abs(observed[j][1]-expected[i])
                         for i,j in enumerate(order)),order)
                for order in __import__("itertools").permutations(range(len(observed)))
            ]
            best,order=min(assignments,key=lambda a:a[0])
            assert best < mp.mpf("1e-12"),(label,best)
            case["phases"]={
                observed[j][0]:case["terms"][i][:2]
                for i,j in enumerate(order)
            }
    return cases

def mp_weights(phases,bits):
    data={}
    with mp.workprec(bits):
        for variable, (pi_ratio, rad) in phases.items():
            angle=2*mp.pi*rational(pi_ratio)+2*rational(rad)
            real,imag=mp.cos(angle),mp.sin(angle)
            digits=45 if bits==128 else 85
            data[variable]=(mp.nstr(real,digits),mp.nstr(imag,digits))
    return data

def replace_weights(original,solver,weights):
    lines=[]
    replaced=set()
    for line in original.splitlines():
        if not line.startswith("c p weight "):
            lines.append(line)
            continue
        t=line.split()
        assert t[:3]==["c","p","weight"]
        variable=int(t[3])
        if variable<=0 or variable not in weights:
            lines.append(line)
            continue
        real,imag=weights[variable]
        if solver=="gpmc":
            assert len(t)>=7
            line=f"c p weight {variable} {real} {imag} 0"
        else:
            sign="-" if imag.startswith("-") else "+"
            line=f"c p weight {variable} {real} {sign} {imag.lstrip('-')}i 0"
        lines.append(line)
        replaced.add(variable)
    assert replaced==set(weights), (replaced,set(weights))
    return "\n".join(lines)+"\n"

def mp_fraction(value):
    return mp.mpf(value.numerator)/mp.mpf(value.denominator)

def run_native(solver,cnf):
    temp=None
    try:
        with tempfile.NamedTemporaryFile(mode="w",suffix=".cnf",delete=False) as f:
            temp=f.name
            f.write(cnf)
        started=time.monotonic()
        count=run_wmc(temp,tool_name=solver,timeout=15,preserve_count=True)
        with mp.workdps(120):
            result=mp.mpc(mp_fraction(count.real),mp_fraction(count.imag))
            return {
                "solver_count_re":str(count.real),
                "solver_count_im":str(count.imag),
                "count_real_decimal":mp.nstr(result.real,95),
                "count_imag_decimal":mp.nstr(result.imag,95),
                "print_half_unit_re":str(count.real_print_half_unit),
                "print_half_unit_im":str(count.imag_print_half_unit),
                "elapsed_seconds":time.monotonic()-started,
                "solver_format":count.format_name,
            }
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)

def native_ab(cases):
    rows=[]
    for label, data in cases.items():
        # Angle literal exactly equals -4*pi*constant_phase_rad; here radians
        # coefficients are theta/4 (negative for global, positive for x).
        scalar=[r for idx,(c,r) in data["phases"].items()
                if int(c[0])==0 and int(r[0])<0]
        assert len(scalar)==1
        with mp.workdps(120):
            theta=-4*rational(scalar[0])
            trace=2*mp.cos(theta/2)
            expected=mp.mpc(trace,0)
            expected_norm=abs(trace)/2
            expected_dist=abs(mp.sin(theta/2))
            oracle={
                "trace_re":mp.nstr(trace,110),
                "normalized_magnitude":mp.nstr(expected_norm,110),
                "projective_distance":mp.nstr(expected_dist,110),
            }
        for solver,baseline in data["cnfs"].items():
            candidates={
                "rust_f64":baseline,
                "oracle_128_bit_weights":replace_weights(
                    baseline,solver,mp_weights(data["phases"],128)),
                "oracle_256_bit_weights":replace_weights(
                    baseline,solver,mp_weights(data["phases"],256)),
            }
            assert len({hashlib.sha256(v.encode()).hexdigest()
                        for v in candidates.values()})==3,(label,solver)
            for variant,cnf in candidates.items():
                row={
                    "group":"native_rust_cnf_weight_ab",
                    "label":label,"solver":solver,"variant":variant,
                    "source_sha256":os.environ.get("GITHUB_SHA"),
                    "cnf_sha256":hashlib.sha256(cnf.encode()).hexdigest(),
                    "independent_120_decimal_oracle":oracle,
                    "candidate":(
                        "actual rust f64" if variant=="rust_f64"
                        else "oracle trig produced by mpmath, not Rust MPFR"
                    ),
                    "certified_solver_error":False,
                }
                try:
                    actual=run_native(solver,cnf)
                    row.update(actual)
                    with mp.workdps(120):
                        count=mp.mpc(mp.mpf(actual["count_real_decimal"]),
                                     mp.mpf(actual["count_imag_decimal"]))
                        row["count_complex_abs_error"]=mp.nstr(
                            abs(count-expected),45)
                        row["normalized_trace_magnitude_error"]=mp.nstr(
                            abs(abs(count)/2-expected_norm),45)
                    row["status"]="observed"
                except Exception as e:
                    row["error"]=type(e).__name__+": "+str(e)[:600]
                    row["status"]="execution_error"
                record(row)
                rows.append(row)
    assert len(rows)==24
    assert all(r["status"]=="observed" for r in rows),"Native solver execution failure"
    # Two source-distinct literals collapsing in f64: high precision CNF can
    # distinguish them, though Ganak's short COUNT output may still mask it.
    for solver in ("gpmc","ganak"):
        old=[r for r in rows if r["solver"]==solver and
             r["variant"]=="rust_f64" and
             r["label"].startswith("literal_alias")]
        assert len(old)==2
        # Hash-map iteration can assign phase variables in different order.
        # The previous independent native test checks the actual positive
        # weight *multiset* collision, not raw CNF byte identity.
    return rows

def build_qc(gates, perturb=0.0):
    qc=QuantumCircuit(1)
    for gate in gates:
        if gate=="h":qc.h(0)
        elif gate=="s":qc.s(0)
        elif gate=="t":qc.t(0)
        else:raise ValueError(gate)
    if perturb:
        # Inserting Rz between S and final H.
        assert gates==("h","s","h")
        qc=QuantumCircuit(1)
        qc.h(0);qc.s(0);qc.rz(perturb,0);qc.h(0)
    return qc

def rr_full_circuits():
    baseline_hsh=build_qc(("h","s","h"))
    perturb=2*float(mp.pi)*1e-7
    cases=[
        ("h_h_identity",QuantumCircuit(1),build_qc(("h","h")), "0"),
        ("hsh_exact",baseline_hsh,build_qc(("h","s","h")),"0"),
        ("hsh_nonidentity",QuantumCircuit(1),baseline_hsh,"analytic_hsh"),
        ("hsh_vs_small_rz",baseline_hsh,build_qc(("h","s","h"),perturb),
         "analytic_2pi_1e-7"),
    ]
    rows=[]
    for name,reference,optimized,theta in cases:
        for tolerance in (1e-6,1e-10):
            for method in ("reduction_rules","hybrid","wmc_only"):
                events=[]
                omega=RED.match_omega
                hh=RED.match_HH
                normalizer=RED.reduce_expression
                def track_normalizer(expr,*args,**kwargs):
                    after=normalizer(expr,*args,**kwargs)
                    if str(expr)!=str(after):
                        events.append({
                            "rule":"phase_normalizer",
                            "before_phase":str(expr)[:480],
                            "after_phase":str(after)[:480],
                            "phase_delta_excerpt":str(expr-after)[:480],
                            "drop_small":kwargs.get("drop_small",True),
                            "approximate_rule_bound_certified":False,
                        })
                    return after
                def wrap(method_name, fn):
                    def inner(*args,**kwargs):
                        outcome=fn(*args,**kwargs)
                        if outcome[0] is not None:
                            events.append({
                                "rule":method_name,
                                "selected_variable":str(outcome[0]),
                                "phase_hash":hashlib.sha256(
                                    str(args[0]).encode()).hexdigest(),
                                "phase_excerpt":str(args[0])[:300],
                                "approximate_rule_bound_certified":False,
                            })
                        return outcome
                    return inner
                previous=config.get_tolerance()
                row={
                    "group":"native_full_circuit_rr",
                    "label":name,"solver":"gpmc" if method!="reduction_rules" else "none",
                    "variant":method,"rr_tolerance":tolerance,
                    "independent_projective_distance": (
                        "0" if theta=="0" else
                        mp.nstr(abs(mp.sin(mp.pi*mp.mpf("1e-7"))),90)
                        if theta=="analytic_2pi_1e-7" else
                        mp.nstr(mp.sqrt(mp.mpf("0.5")),90)
                    ),
                    "certified_global_rr_error":False,
                }
                try:
                    config.set_tolerance(tolerance)
                    with ExitStack() as stack:
                        stack.enter_context(patch.object(RED,"match_omega",
                                                        wrap("omega",omega)))
                        stack.enter_context(patch.object(RED,"match_HH",
                                                        wrap("HH",hh)))
                        stack.enter_context(patch.object(
                            RED,"reduce_expression",track_normalizer))
                        result=check_equivalence(
                            reference,optimized,
                            method=method,backend="python",strategy="Naive",
                            tool_name="gpmc",timeout=20,
                            approximate_distance_tolerance=1e-8,
                        )
                    row["status"]=result.equivalent
                    row["statistics"]=result.Statistics.get_reduction_counts()
                    row["events"]=events[:100]
                    row["event_total"]=len(events)
                    row["potential_false_positive"]=(
                        name=="hsh_vs_small_rz"
                        and result.equivalent in ("equivalent","equivalent*")
                    )
                    if row["potential_false_positive"]:
                        row["scientific_flag"]="APPROX_DISTANCE_FALSE_POSITIVE_CANDIDATE"
                except Exception as e:
                    row["error"]=type(e).__name__+": "+str(e)[:600]
                    row["status"]="execution_error"
                finally:
                    config.set_tolerance(previous)
                record(row);rows.append(row)
    assert len(rows)==24
    assert all(r["status"]!="execution_error" for r in rows)
    # A useful circuit-level RR control must trigger actual reduction rules.
    # Reaching HH or Omega through the full circuit is a research gate.
    controls=[r for r in rows if r["variant"]=="reduction_rules"]
    assert any(e["rule"]=="HH" for r in controls for e in r.get("events",[])), (
        "RR_FULL_CIRCUIT_HH_CONTROL_NOT_REACHED"
    )
    assert any(e["rule"]=="omega" for r in controls for e in r.get("events",[])), (
        "RR_FULL_CIRCUIT_OMEGA_CONTROL_NOT_REACHED"
    )
    return rows

def main():
    if RAW.exists():RAW.unlink()
    cases=parse_rust_test_log()
    rows=native_ab(cases)
    rr=rr_full_circuits()
    results={
        "source_sha":os.environ.get("GITHUB_SHA"),
        "native_solver_records":len(rows),
        "rr_circuit_records":len(rr),
        "native_ab_execution_errors":sum("error" in r for r in rows),
        "rr_execution_errors":sum("error" in r for r in rr),
        "hh_events":sum(e["rule"]=="HH" for r in rr for e in r.get("events",[])),
        "omega_events":sum(e["rule"]=="omega" for r in rr for e in r.get("events",[])),
        "phase_normalizer_events":sum(e["rule"]=="phase_normalizer" for r in rr for e in r.get("events",[])),
        "scientific_flags":[{"case":r["label"],"tolerance":r["rr_tolerance"],
            "method":r["variant"],"flag":r["scientific_flag"]}
            for r in rr if "scientific_flag" in r],
        "limitations":[
            "Precision candidates computed in mpmath, not yet the production Rust trig path",
            "Stock solver parser/count may round more than high precision input weights",
            "No certified full-solver arithmetic or RR error bound",
        ],
    }
    SUMMARY.write_text(json.dumps(results,indent=2,sort_keys=True)+"\n")
    print("NATIVE_WEIGHT_RR_SUMMARY "+json.dumps(results,sort_keys=True),flush=True)

if __name__=="__main__":
    main()

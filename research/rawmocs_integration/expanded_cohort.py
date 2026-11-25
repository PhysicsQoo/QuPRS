"""Expanded actual native Hybrid cohort and explicit general-route admission.
Censored and RR-only cases are evidence, never speedups. Cross-solver parity
is diagnostic, not an independent equivalence certificate.
"""
import argparse
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import statistics
import subprocess
import time
from compare import measure, bounded, digest
from QuPRS.interface.ps2wmc import run_wmc
from release_native_paired import parse
from decimal import Decimal, localcontext
from release_transfer import check_count

ARMS=("gpmc","rawmocs")
CASES={
    "qft16-memory":("qft",16,True,False),
    "qft20":("qft",20,True,False),
    "qft22":("qft",22,True,False),
    "qpeinexact20":("qpeinexact",20,False,False),
    "grover6":("grover-noancilla",6,True,False),
    "qaoa9":("qaoa",9,False,False),
    "vqe8":("vqe",8,False,False),
    "qnn8":("qnn",8,False,False),
    "wstate8":("wstate",8,False,False),
    "qft20-negative":("qft",20,True,True),
}
LIMIT=90
AS="3221225472"

def save(path,data):
    path.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")

def inspect(arm,out,err):
    row=parse(out,arm)
    if arm=="gpmc":
        assert re.findall(r"^c o precision (\d+)\s*$",out,re.M)==["30"]
    else:
        route,=re.findall(r"^RAWMOCS_COMPLETE route=(\w+) digits=30 bits=100 ",err,re.M)
        row["route"]=route
        row["telemetry"]=[s for s in err.splitlines() if s.startswith(("PREJOIN_","GENERAL_","RAWMOCS_"))]
    return row

def parity(g,r):
    scale=max(Fraction(1),*(abs(Fraction(x[k])) for x in (g,r) for k in ("real","imag")))
    return g["sat"]==r["sat"] and max(abs(Fraction(g[k])-Fraction(r[k])) for k in ("real","imag"))/scale<=Fraction(1,10**24)

def run(a,arm,lhs,rhs,label,capture):
    pref=a.out/label
    exe=a.raw if arm=="rawmocs" else a.gpmc
    cnf=pref.with_suffix(".cnf");out=pref.with_suffix(".solver.stdout");err=pref.with_suffix(".solver.stderr")
    env={**os.environ,"QUPRS_GPMC_PATH":str(a.gpmc),"QUPRS_RAWMOCS_PATH":str(a.raw)}
    if capture:
        wrapper=pref.with_suffix(".sh")
        wrapper.write_text("#!/bin/sh\nset -eu\nfor last do :; done\ncp -- \"$last\" "+shlex.quote(str(cnf))+
            "\n"+shlex.quote(str(exe))+" \"$@\" >"+shlex.quote(str(out))+" 2>"+shlex.quote(str(err))+
            "\ncat "+shlex.quote(str(out))+"\ncat "+shlex.quote(str(err))+" >&2\n")
        wrapper.chmod(0o755)
        env["QUPRS_"+arm.upper()+"_PATH"]=str(wrapper)
    rss=pref.with_suffix(".rss")
    cmd=["timeout","-k","2s",str(LIMIT+5),"prlimit","--as="+AS,"--","/usr/bin/time","-f","%M","-o",str(rss),str(a.bin),str(lhs),str(rhs),arm,str(LIMIT)]
    start=time.monotonic()
    row={"arm":arm,"capture":capture}
    try:
        proc=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=LIMIT+10)
        row.update(wall_s=time.monotonic()-start,exit=proc.returncode,stderr=proc.stderr[-2000:])
        pref.with_suffix(".stdout").write_text(proc.stdout)
        pref.with_suffix(".stderr").write_text(proc.stderr)
        if rss.exists():
            try:row["maxrss_kib"]=int(rss.read_text().strip().splitlines()[-1])
            except (ValueError,IndexError):pass
        if proc.returncode:
            row["status"]="CENSORED_TIMEOUT" if proc.returncode==124 else "EXECUTION_ERROR"
        else:
            line,=[s for s in proc.stdout.splitlines() if s.startswith("COHORT_RESULT ")]
            verdict,invoked,verify,ps,dimacs,tool,norm=line.split(" ",1)[1].split("\t")
            row.update(verdict=verdict,invoked=invoked=="true",verification_s=float(verify),pathsum_s=float(ps),dimacs_s=float(dimacs),tool_s=float(tool),normalization_twice_log2=int(norm))
            if verdict in ("Timeout","MemoryOut"):row["status"]="CENSORED_"+verdict.upper()
            elif invoked=="false":row["status"]="RR_OR_ANALYTIC_ONLY"
            elif invoked=="true" and verdict in ("equivalent","equivalent*","not_equivalent"):
                row["status"]="COMPLETED"
                if capture:
                    row.update(inspect(arm,out.read_text(),err.read_text()),cnf_sha256=digest(cnf))
            else:row["status"]="INCONCLUSIVE"
    except subprocess.TimeoutExpired:
        row.update(status="CENSORED_WATCHDOG",wall_s=time.monotonic()-start)
    except Exception as e:
        row.update(status="ERROR",error=f"{type(e).__name__}: {e}")
    if capture:
        if cnf.exists():row["captured_cnf_sha256"]=digest(cnf)
        if err.exists():row["solver_stderr_tail"]=err.read_text()[-4000:]
    save(pref.with_suffix(".json"),row)
    return row

def cohort(a,report):
    family,n,reverse,negative=CASES[a.case]
    filename=f"{family}_nativegates_ibm_qiskit_opt0_{n}.qasm"
    root=Path("benchmarks/MQTBench")
    lhs=root/filename
    rhs=root/("qiskit-2.6.1-opt0/Random_Rotation" if negative else "h,ry,rz,cx")/filename
    if reverse:lhs,rhs=rhs,lhs
    expected=("not_equivalent",) if negative else ("equivalent","equivalent*")
    report.update(source=[str(lhs),str(rhs)],source_sha256=[digest(lhs),digest(rhs)],expected=list(expected),preflight={})
    for arm in ARMS:
        report["preflight"][arm]=run(a,arm,lhs,rhs,"preflight-"+arm,True)
        save(a.out/"report.json",report)
    g,r=(report["preflight"][arm] for arm in ARMS)
    if not all(v["status"]=="COMPLETED" for v in (g,r)):
        report["status"]="RR_ONLY" if all(v["status"]=="RR_OR_ANALYTIC_ONLY" and v["verdict"] in expected for v in (g,r)) else "INCONCLUSIVE"
        if a.case=="qft22" and g["status"]=="COMPLETED":
            report["route_diagnostic"]=route_diagnostic(a,g)
        return
    if not (g["verdict"]==r["verdict"] and g["cnf_sha256"]==r["cnf_sha256"] and g["normalization_twice_log2"]==r["normalization_twice_log2"] and parity(g,r)):
        report["status"]="NUMERIC_OR_SOURCE_MISMATCH";return
    if g["verdict"] not in expected:
        report["status"]="SOURCE_EXPECTATION_MISMATCH"
        report["source_diagnostic"]=source_diagnostic(a,g,r)
        # Never promote the original EQ expectation or publish a speedup.
        return
    report["rows"]=[]
    for i,arm in enumerate(("gpmc","rawmocs","rawmocs","gpmc")):
        row=run(a,arm,lhs,rhs,f"native-{i}-{arm}",False)
        report["rows"].append(row)
        save(a.out/"report.json",report)
    if not all(v["status"]=="COMPLETED" and v["verdict"]==g["verdict"] for v in report["rows"]):
        report["status"]="INCONCLUSIVE";return
    report["median"]={arm:{k:statistics.median(v[k] for v in report["rows"] if v["arm"]==arm) for k in ("wall_s","tool_s","maxrss_kib")} for arm in ARMS}
    report["speedup"]=report["median"]["gpmc"]["wall_s"]/report["median"]["rawmocs"]["wall_s"]
    report["status"]="PAIRED_DIAGNOSTIC_PASS"
    if a.case=="qft16-memory":
        cnf=a.out/"preflight-gpmc.cnf"
        report["solver_memory"]={}
        for arm in ARMS:
            report["solver_memory"][arm]=measure(arm,30,a.raw,a.gpmc,a.out/("memory-"+arm),
                lambda selected: count_transport(cnf,selected))
        assert all(v["status"]=="COMPLETED" for v in report["solver_memory"].values())

def distance_from_count(row):
    # Exact squared midpoint, using the native verifier's actual residual
    # normalization, not a guessed nearest power of two.
    norm=Fraction(2)**row["normalization_twice_log2"]
    d2=1-(Fraction(row["real"])**2+Fraction(row["imag"])**2)/norm
    with localcontext() as ctx:
        ctx.prec=65
        x=Decimal(d2.numerator)/Decimal(d2.denominator)
        return {"signed_distance_squared":str(x),"projective_distance":str(max(Decimal(0),x).sqrt())}

def source_diagnostic(a,g,r):
    cnf=a.out/"preflight-gpmc.cnf"
    h=digest(cnf)
    assert h==g["cnf_sha256"]==r["cnf_sha256"]
    diag={"scope":"encoded residual CNF only, not source circuit certification",
          "distance":{arm:distance_from_count(row) for arm,row in zip(ARMS,(g,r))},
          "oracle_attempts":[],"witness_status":"UNAVAILABLE"}
    for name in ("original_exact_prejoin.py","original_fixed_interval.py"):
        proc=bounded([__import__("sys").executable,a.oracle/name,cnf,h],120)
        (a.out/(name+".stdout")).write_text(proc.stdout)
        (a.out/(name+".stderr")).write_text(proc.stderr)
        diag["oracle_attempts"].append({"script":name,"exit":proc.returncode,"stderr_tail":proc.stderr[-500:]})
        if proc.returncode!=0:continue
        ref=json.loads(proc.stdout)
        assert ref["source_sha256"]==h and ref["bits"]==550
        assert ref["width"]<=19 and ref["work"]<=40000000 and ref["peak"]<=2000000
        if name=="original_fixed_interval.py":assert ref["order_policy"] in ("fill-reverse","degree-reverse")
        else:assert ref["status"]=="INDEPENDENT_INTERVAL_COMPLETE"
        save(a.out/"independent-witness.json",ref)
        try:
            diag["witness_relative_upper"]={arm:check_count(row,ref,30) for arm,row in zip(ARMS,(g,r))}
        except AssertionError:
            diag["witness_status"]="MISMATCH";return diag
        def square_bounds(v):
            lo,hi=map(Fraction,v)
            return (Fraction(0) if lo<=0<=hi else min(lo*lo,hi*hi),max(lo*lo,hi*hi))
        rl,rh=square_bounds(ref["real"]);il,ih=square_bounds(ref["imag"])
        norm=Fraction(2)**g["normalization_twice_log2"]
        lo=1-(rh+ih)/norm;hi=1-(rl+il)/norm
        diag["independent_distance_squared_interval"]=[str(lo),str(hi)]
        diag["witness_status"]="PASS"
        diag["independent_residual_neq_at_1e-8"]=lo>Fraction(1,10**16)
        break
    return diag

def route_diagnostic(a,g):
    cnf=a.out/"preflight-gpmc.cnf"
    assert digest(cnf)==g["cnf_sha256"]
    diag={"cnf_sha256":digest(cnf),"scope":"same captured residual, 90s independent route probes","rows":[]}
    for mode in ("prejoin","general","auto"):
        rss=a.out/("route-"+mode+".rss")
        start=time.monotonic()
        proc=subprocess.run(["timeout","-k","2s","95s","prlimit","--as="+AS,"--",
            "/usr/bin/time","-f","%M","-o",str(rss),str(a.raw),"--digits","30","--solver",mode,
            "--timeout-ms","90000",str(cnf)],text=True,capture_output=True,timeout=100)
        (a.out/("route-"+mode+".stdout")).write_text(proc.stdout)
        (a.out/("route-"+mode+".stderr")).write_text(proc.stderr)
        row={"mode":mode,"exit":proc.returncode,"wall_s":time.monotonic()-start,"stderr_tail":proc.stderr[-4000:]}
        if rss.exists():row["maxrss_kib_raw"]=rss.read_text()
        if proc.returncode==0:
            row.update(inspect("rawmocs",proc.stdout,proc.stderr))
            row["gpmc_count_parity"]=parity(g,row)
        else:
            row["empty_numeric_stdout"]=not proc.stdout.strip()
        diag["rows"].append(row)
        save(a.out/"route-diagnostic.json",diag)
    return diag

def count_transport(cnf,selected):
    v=run_wmc(str(cnf),selected,timeout=30,preserve_count=True,precision_digits=30 if selected=="gpmc" else None)
    return {"transport_real":str(v.real),"transport_imag":str(v.imag)}

def fallback(a,report):
    wide=" ".join(map(str,range(1,11)))+" 0\n"
    fixtures=[
        ("wide_signed","p cnf 33 1\nc t wmc\nc p weight 1 -0.5 0.25 0\nc p weight -1 0.5 0 0\n"+wide,True,-2**22,2**30),
        ("wide_sat_zero","p cnf 33 1\nc t wmc\nc p weight 33 -1 0 0\nc p weight -33 1 0 0\n"+wide,True,0,0),
        ("wide_unsat","p cnf 33 3\nc t wmc\n"+wide+"1 0\n-1 0\n",False,0,0),
    ]
    report["fixtures"]=[]
    for name,raw,sat,re,im in fixtures:
        cnf=a.out/(name+".cnf");cnf.write_text(raw)
        row={"name":name,"expected":[sat,re,im],"cnf_sha256":digest(cnf),"arms":{}}
        report["fixtures"].append(row)
        if name=="wide_signed":
            refused=bounded([a.raw,"--digits","30","--solver","prejoin","--timeout-ms","10000",cnf],15)
            row["prejoin_refusal"]={"exit":refused.returncode,"stdout":refused.stdout,"stderr":refused.stderr}
            assert refused.returncode==6 and not refused.stdout.strip(),row
        for arm in ARMS:
            # Actual Python registered adapter and GPMC transport, exact analytic oracle.
            value=measure(arm,30,a.raw,a.gpmc,a.out/(name+"-"+arm),lambda selected:count_transport(cnf,selected),analytic_unsat_control=(name=="wide_unsat"))
            row["arms"][arm]=value;save(a.out/"report.json",report)
            assert value["status"]=="COMPLETED",value
            assert value["sat"]==sat and Fraction(value["real"])==re and Fraction(value["imag"])==im,value
            if arm=="rawmocs" and name in ("wide_signed","wide_sat_zero"):assert value["route"]=="general",value
    report["status"]="FALLBACK_ORACLE_PASS"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--case",choices=[*CASES,"fallback"],required=True)
    for name in ("raw","gpmc","out","bin"):p.add_argument("--"+name,required=True,type=lambda x:Path(x).resolve())
    p.add_argument("--oracle",type=lambda x:Path(x).resolve(),required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    os.environ["QUPRS_GPMC_PATH"]=str(a.gpmc)
    report={"case":a.case,"status":"RUNNING","digits":30,"limit_s":LIMIT,"address_space_bytes":int(AS),"binary_sha256":{arm:digest(a.raw if arm=="rawmocs" else a.gpmc) for arm in ARMS}}
    try:
        (fallback if a.case=="fallback" else cohort)(a,report)
    except Exception as e:
        report.update(status="ERROR",error=f"{type(e).__name__}: {e}")
        raise
    finally:
        save(a.out/"report.json",report)
        print("EXPANDED_COHORT_FINAL",json.dumps(report),flush=True)
    # Censoring and RR-only are scientifically useful, but mismatch must fail.
    assert report["status"] in ("FALLBACK_ORACLE_PASS","PAIRED_DIAGNOSTIC_PASS","RR_ONLY","INCONCLUSIVE","SOURCE_EXPECTATION_MISMATCH")

if __name__=="__main__":main()

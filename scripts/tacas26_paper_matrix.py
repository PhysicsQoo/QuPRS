#!/usr/bin/env python3
"""Source-pinned TACAS26 case ledger. Science verdicts only, NO performance timing."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import traceback

HISTORICAL_SHA="e928abc47dd15926364ec77905eb0d5dc92ce8cc"
SMOKE_IDS=(
 "table2:ghz32:positive:hybrid",
 "table2:ghz32:positive:reduction_rules",
 "table2:ghz32:positive:wmc_only",
 "table2:graphstate16:positive:hybrid",
 "table2:qaoa7:positive:hybrid",
 "table2:qpeinexact20:positive:hybrid",
 "table3_negative:ghz32:negative:hybrid",
 "table3_negative:ghz32:negative:wmc_only",
 "table3_negative:qwalk3:negative:hybrid",
 "figure3:tof_3:positive:reduction_rules",
)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def pinned(root, rel, sha1=None):
    path=(root/rel).resolve()
    if not path.is_relative_to(root.resolve()) or path.suffix!=".qasm" or not path.is_file():
        raise ValueError("Invalid/missing QASM: "+rel)
    raw=path.read_bytes()
    obj=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if sha1 and obj!=sha1:
        raise ValueError("Pinned QASM Git blob mismatch: "+rel)
    return {"relative":rel,"sha256":hashlib.sha256(raw).hexdigest(),
            "git_blob_sha1":obj,"historical_source":HISTORICAL_SHA}

def matrix(root):
    meta=json.loads((root/"benchmarks/codspeed/paper_difficulty.json").read_text())
    corpus=json.loads((root/"docs/development/paper-corpus-manifest.json").read_text())
    pairs={Path(x["source"]["path"]).name:x for x in
           corpus["cohorts"]["table2_mqt"]["cases"]}
    rows=[]
    def add(suite,id,kind,method,a,b,known_a=None,known_b=None,timeout=None):
        rows.append({"id":f"{suite}:{id}:{kind}:{method}",
                     "suite":suite,"case":id,"kind":kind,"method":method,
                     "a":a,"b":b,"sha_a":known_a,"sha_b":known_b,
                     "historical_hybrid_timeout":timeout,
                     "paper_expected":("equivalent*" if id=="qpeinexact20"
                         and suite=="table2" and method=="hybrid"
                         else "NOT_YET_TRANSCRIBED")})
    for x in meta["cases"]:
        pair=pairs.get(x["fixture"])
        if pair is None:raise ValueError("Missing Table2 fixture: "+x["fixture"])
        for method in ("hybrid","reduction_rules","wmc_only"):
            add("table2",x["id"],"positive",method,
                pair["source"]["path"],pair["transpiled"]["path"],
                pair["source"]["git_blob_sha1"],pair["transpiled"]["git_blob_sha1"],
                x["historical_positive_timeout"])
    supplement=corpus["additional_mqt_pair"]
    if len(meta["table3_only_cases"])!=1 or meta["table3_only_cases"][0]["id"]!="wstate32":
        raise ValueError("Expected WState32 Table3 supplement")
    add("table3_positive","wstate32","positive","hybrid",
        supplement["source"]["path"],supplement["transpiled"]["path"],
        supplement["source"]["git_blob_sha1"],supplement["transpiled"]["git_blob_sha1"],True)
    for x in meta["cases"]+meta["table3_only_cases"]:
        pair=pairs.get(x["fixture"],supplement)
        for method in ("hybrid","wmc_only"):
            add("table3_negative",x["id"],"negative",method,
                pair["source"]["path"],"benchmarks/MQTBench/Random_Rotation/"+x["fixture"],
                pair["source"]["git_blob_sha1"],None,x["historical_negative_timeout"])
    for x in corpus["cohorts"]["feynman_ci_sample"]["cases"]:
        add("figure3",x["id"],"positive","reduction_rules",
            x["source"]["path"],x["transpiled"]["path"],
            x["source"]["git_blob_sha1"],x["transpiled"]["git_blob_sha1"])
    counts={name:sum(x["suite"]==name for x in rows)
            for name in ("table2","table3_positive","table3_negative","figure3")}
    if counts!={"table2":108,"table3_positive":1,"table3_negative":74,"figure3":4}:
        raise ValueError("Paper coverage changed: "+str(counts))
    if len({x["id"] for x in rows})!=187 or not set(SMOKE_IDS).issubset({x["id"] for x in rows}):
        raise ValueError("Paper identities not unique or smoke source missing")
    return rows

def run_one(paper,case,outfile):
    result={"id":case["id"],"status":"ERROR","verdict":None,
            "source_sha":HISTORICAL_SHA,"original":None,"counterpart":None,
            "solver_calls":[],"complex_counts":[],"error":None,
            "performance":"NOT_MEASURED_ONLY_SCIENCE"}
    try:
        import numpy as np
        import qiskit
        import QuPRS
        from QuPRS import check_equivalence,config
        from QuPRS.interface import ps2wmc,load_qiskit
        from QuPRS.utils import WMC
        from QuPRS.utils.util import get_theta
        if Path(QuPRS.__file__).resolve()!=(paper/"src/QuPRS/__init__.py").resolve():
            raise ValueError("QuPRS imported from wrong source")
        if config.TOLERANCE!=1e-10 or "round(np.log2(abs_num), 3)" not in Path(load_qiskit.__file__).read_text():
            raise ValueError("Historical classifier semantics changed")
        result["original"]=pinned(paper,case["a"],case["sha_a"])
        result["counterpart"]=pinned(paper,case["b"],case["sha_b"])
        result["qiskit_version"]=qiskit.__version__
        with WMC() as exe: result["original_gpmc_sha256"]=digest(exe)
        run=ps2wmc.subprocess.run
        wmc=ps2wmc.run_wmc
        def record_run(command,*a,**kw):
            r=run(command,*a,**kw)
            if "-mode=1" in [str(s) for s in command]:
                result["solver_calls"].append({
                    "command":[str(s) for s in command],
                    "returncode":r.returncode,
                    "stdout":r.stdout if isinstance(r.stdout,str) else repr(r.stdout),
                    "stderr":r.stderr if isinstance(r.stderr,str) else repr(r.stderr)})
            return r
        def record_wmc(*a,**kw):
            value=wmc(*a,**kw)
            result["complex_counts"].append({"real":float(value[0]),"imag":float(value[1])})
            return value
        ps2wmc.subprocess.run=record_run
        ps2wmc.run_wmc=record_wmc
        try:
            data=check_equivalence(str(paper/case["a"]),str(paper/case["b"]),
                method=case["method"],strategy="Proportional",timeout=200)
        finally:
            ps2wmc.subprocess.run=run
            ps2wmc.run_wmc=wmc
        result["verdict"]=str(data.equivalent)
        result["expected_log2"]=float(data.expect) if data.expect is not None else None
        result["rounded_log2"]=float(data.log_wmc) if data.log_wmc is not None else None
        result["solver_invoked"]=bool(result["solver_calls"])
        result["status"]="RETURNED"
        if result["complex_counts"]:
            z=result["complex_counts"][-1]
            m=float(np.sqrt(z["real"]**2+z["imag"]**2))
            if m<=0 or not math.isfinite(m):raise ValueError("Invalid original solver magnitude")
            phase=float(get_theta(z["imag"]/m,z["real"]/m))
            raw=float(np.log2(m))
            result["original_phase_rad"]=phase
            result["raw_log2_abs_wmc"]=raw
            if result["expected_log2"] is not None:
                ok=abs(round(raw,3)-result["expected_log2"])<config.TOLERANCE
                prior=(("equivalent" if abs(phase)<config.TOLERANCE*2*np.pi
                       else "equivalent*") if ok else "not_equivalent")
                result["v091_replayed_verdict"]=prior
                if prior!=result["verdict"]:result["status"]="REPLAY_MISMATCH"
        if any(x["returncode"]!=0 for x in result["solver_calls"]):
            result["status"]="SOLVER_ERROR"
        if case["paper_expected"]!="NOT_YET_TRANSCRIBED" and result["verdict"]!=case["paper_expected"]:
            result["status"]="PAPER_MISMATCH"
    except BaseException as e:
        result["status"]="ERROR"
        result["error"]={"type":type(e).__name__,"message":str(e),
                         "traceback":traceback.format_exc()[-2500:]}
    finally:
        outfile.parent.mkdir(parents=True,exist_ok=True)
        outfile.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    return 0 if result["status"]=="RETURNED" else 2

def run_parent(current,paper,output,rows,shard,shards,limit,watchdog):
    if subprocess.run(["git","-C",str(paper),"rev-parse","HEAD"],
            check=True,capture_output=True,text=True).stdout.strip()!=HISTORICAL_SHA:
        raise ValueError("Wrong historical commit")
    cases=[row for i,row in enumerate(rows) if i%shards==shard]
    if not cases or len(cases)>limit:
        raise ValueError("Empty or too many jobs for fixed CI budget")
    output.mkdir(parents=True,exist_ok=True)
    (output/"case-plan.json").write_text(json.dumps(cases,indent=2,sort_keys=True)+"\n")
    log={"schema":"quprs-tacas26-source-matrix-v1","source":HISTORICAL_SHA,
         "shard":shard,"shards":shards,"count":len(cases),
         "overall_matrix_size":187,"performance":"NONE_NOT_CODSPEED","results":[]}
    for case in cases:
        for side in ("a","b"):pinned(paper,case[side],case["sha_"+side])
        label=case["id"].replace(":","_")
        dest=output/(label+".json")
        cmd=[sys.executable,str(current/"scripts/tacas26_paper_matrix.py"),
             "--child",case["id"],"--paper",str(paper),
             "--current",str(current),"--plan",str(output/"case-plan.json"),
             "--result",str(dest)]
        env=dict(os.environ,PYTHONPATH=str(paper/"src"),PYTHONNOUSERSITE="1")
        child=subprocess.Popen(cmd,cwd=paper,env=env,text=True,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:
            stdout,stderr=child.communicate(timeout=watchdog)
        except subprocess.TimeoutExpired:
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            stdout,stderr=child.communicate()
            dest.write_text(json.dumps({"id":case["id"],"status":"EXTERNAL_TIMEOUT",
                "verdict":None,"timeout_seconds":200,
                "science":"CENSORED_NOT_NOT_EQUIVALENT"})+"\n")
        (output/(label+".stdout")).write_text(stdout[-10000:])
        (output/(label+".stderr")).write_text(stderr[-10000:])
        observed=json.loads(dest.read_text()) if dest.is_file() else {
            "id":case["id"],"status":"MISSING_RESULT","verdict":None}
        log["results"].append({"id":case["id"],"status":observed["status"],
            "verdict":observed.get("verdict"),"source_result_file":dest.name})
        (output/"summary.json").write_text(json.dumps(log,indent=2,sort_keys=True)+"\n")
        print(json.dumps(log["results"][-1],sort_keys=True),flush=True)
    bad=[x for x in log["results"] if x["status"] not in ("RETURNED","EXTERNAL_TIMEOUT")]
    if bad:raise SystemExit("Missing, invalid or scientifically unexpected results: "+str(bad))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--current",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--paper",type=Path)
    p.add_argument("--list",action="store_true")
    p.add_argument("--child")
    p.add_argument("--plan",type=Path)
    p.add_argument("--result",type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--cohort",choices=("all","smoke"),default="smoke")
    p.add_argument("--method",choices=("all","hybrid","reduction_rules","wmc_only"),default="all")
    p.add_argument("--exclude-smoke",action="store_true")
    p.add_argument("--suite",choices=("all","table2","table3_positive","table3_negative","figure3"),default="all")
    p.add_argument("--shard",type=int,default=0)
    p.add_argument("--shards",type=int,default=1)
    p.add_argument("--max-cases",type=int,default=6)
    p.add_argument("--watchdog",type=int,default=215)
    args=p.parse_args()
    current=args.current.resolve()
    all_rows=matrix(current)
    if args.list:
        print(json.dumps({"total":len(all_rows),"cases":all_rows},indent=2,sort_keys=True));return
    if args.paper is None:p.error("Missing --paper historical checkout")
    paper=args.paper.resolve()
    if args.child:
        rows=json.loads(args.plan.read_text())
        case=next((x for x in rows if x["id"]==args.child),None)
        if case is None:raise ValueError("Unregistered historical case")
        raise SystemExit(run_one(paper,case,args.result))
    rows=[r for r in all_rows if (args.suite=="all" or r["suite"]==args.suite)
          and (args.cohort!="smoke" or r["id"] in SMOKE_IDS)
          and (args.method=="all" or r["method"]==args.method)
          and (not args.exclude_smoke or r["id"] not in SMOKE_IDS)]
    if args.shards<1 or not 0<=args.shard<args.shards or args.output is None:
        p.error("Missing output or invalid shard")
    run_parent(current,paper,args.output,rows,args.shard,args.shards,args.max_cases,args.watchdog)

if __name__=="__main__":main()

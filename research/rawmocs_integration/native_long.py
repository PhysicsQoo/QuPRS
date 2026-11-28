"""P4.5: original witnessed CNFs, three isolated QuPRS run_wmc arms."""
from contextlib import nullcontext
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

import psutil
import rawmocs
from QuPRS.interface.ps2wmc import run_wmc
from QuPRS.utils import solver_process
from rawmocs_quprs import registered_rawmocs, RawAdapter
from native_adapter import registered_native, NativeFailure
from release_transfer import check_count

ROOT=Path(".p4-long-evidence").resolve()
RAW=Path(".rawmocs-candidate/crates/rawmocs-cli/target/release/rawmocs").resolve()
GPMC=Path(".gpmc/build/gpmc").resolve()
ARMS=("gpmc","rawmocs","rawmocs_native")
LIMIT=int(os.environ.get("RAWMOCS_LONG_LIMIT_S", "120"))
assert LIMIT in (60,120), "unsupported long cohort budget"
AS_BYTES=3221225472
DIGITS=130

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def signature(r):return tuple(r[k] for k in ("sat","real","imag","route"))
def worker(arm,path,prefix):
    os.environ["QUPRS_GPMC_PATH"]=str(GPMC)
    external=[];native=[]
    old=solver_process.run;old_native=rawmocs.solve_file
    def observe(cmd,timeout):
        result=old(cmd,timeout);external.append(result)
        return result
    def observe_native(*a,**k):
        result=old_native(*a,**k);native.append(result)
        return result
    ctx=registered_native(DIGITS) if arm=="rawmocs_native" else (
        registered_rawmocs(RAW,digits=DIGITS,timeout_ms=LIMIT*1000,address_space_bytes=None)
        if arm=="rawmocs" else nullcontext())
    row={"arm":arm,"status":"IN_PROGRESS","baseline_parent_rss_kib":psutil.Process().memory_info().rss//1024}
    start=time.perf_counter_ns()
    try:
        with ctx,patch.object(solver_process,"run",observe),patch.object(rawmocs,"solve_file",observe_native):
            start=time.perf_counter_ns()
            value=run_wmc(path,arm,timeout=LIMIT,preserve_count=True,
                          precision_digits=DIGITS if arm=="gpmc" else None)
            row["wall_ns"]=time.perf_counter_ns()-start
        row.update(real=str(value.real),imag=str(value.imag),route=None,core_ns=None)
        if arm=="rawmocs_native":
            assert not external and len(native)==1
            n=native[0]
            assert n.digits==DIGITS and n.precision_bits==432
            row.update(sat=n.sat,route=n.route,core_ns=n.solve_ns)
        else:
            assert not native and len(external)==1
            result=external[0]
            assert result.returncode==0
            prefix.with_suffix(".solver.stdout").write_text(result.stdout)
            prefix.with_suffix(".solver.stderr").write_text(result.stderr)
            if arm=="rawmocs":
                sat,count=RawAdapter.parse_protocol(result.stdout);assert count==value
                (route,ns),=re.findall(r"^RAWMOCS_COMPLETE route=(\w+) digits=130 bits=432 solve_ns=(\d+)",result.stderr,re.M)
                row.update(sat=sat,route=route,core_ns=int(ns))
            else:
                assert re.findall(r"^c o precision (\d+)\s*$",result.stdout,re.M)==["130"]
                sat,=re.findall(r"^s (SATISFIABLE|UNSATISFIABLE)\s*$",result.stdout,re.M)
                row["sat"]=sat=="SATISFIABLE"
        row["status"]="COMPLETED"
    except solver_process.SolverTimeout as e:
        row.update(status="CENSORED_TIMEOUT",error=str(e))
    except NativeFailure as e:
        row.update(status="NATIVE_FAILURE",kind=e.kind,error=str(e))
    except Exception as e:
        row.update(status="EXECUTION_OR_PROTOCOL_ERROR",error=f"{type(e).__name__}: {str(e)[:1000]}")
    finally:
        row.setdefault("wall_ns",time.perf_counter_ns()-start)
        prefix.with_suffix(".worker.json").write_text(json.dumps(row,indent=2)+"\n")

def run(arm,path,prefix):
    # Fresh Python process for each arm; same per-process AS cap. Process-tree
    # RSS is sampled, not exact instantaneous max or a total AS guarantee.
    cmd=["prlimit",f"--as={AS_BYTES}","--",sys.executable,str(Path(__file__).resolve()),
         "worker",arm,str(path),str(prefix)]
    begin=time.monotonic();peak=0;samples=0;known={};timed_out=False
    with prefix.with_suffix(".stdout").open("w") as out,prefix.with_suffix(".stderr").open("w") as err:
        proc=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True)
        try:
            parent=psutil.Process(proc.pid)
            while proc.poll() is None:
                if time.monotonic()-begin>LIMIT+10:
                    timed_out=True;break
                try:
                    members=[parent,*parent.children(recursive=True)]
                    total=0
                    for member in members:
                        try:
                            known[member.pid]=member
                            total+=member.memory_info().rss
                        except psutil.NoSuchProcess:pass
                    peak=max(peak,total);samples+=1
                except psutil.NoSuchProcess:pass
                time.sleep(.05)
        finally:
            # QuPRS-managed child solvers can have their own session.
            if proc.poll() is None:
                try:
                    for child in parent.children(recursive=True):known[child.pid]=child
                except psutil.Error:pass
                for child in known.values():
                    if child.pid!=proc.pid:
                        try:child.kill()
                        except psutil.Error:pass
                proc.kill()
            proc.wait(timeout=5)
    p=prefix.with_suffix(".worker.json")
    row=json.loads(p.read_text()) if p.exists() and not timed_out and proc.returncode==0 else {
        "arm":arm,"status":"CENSORED_OUTER_TIMEOUT" if timed_out else "WORKER_EXIT",
        "exit_code":proc.returncode}
    row.update(sampled_tree_peak_rss_kib=peak//1024,rss_samples=samples,
               worker_total_wall_s=time.monotonic()-begin)
    return row

def main():
    ROOT.mkdir(exist_ok=True)
    inputs=Path(".p4-long-input")
    path,=inputs.rglob("*-gpmc.cnf");path=path.resolve()
    witness,=inputs.rglob("prejoin-reference.json")
    receipt,=inputs.rglob("prejoin-native-pilot.json")
    ref=json.loads(witness.read_text());prior=json.loads(receipt.read_text())
    expected=os.environ["CNF_SHA"];witness_sha=os.environ["WITNESS_SHA"]
    assert sha(path)==expected==ref["source_sha256"]==prior["source_sha256"]
    assert sha(witness)==witness_sha==prior["reference_sha256"]
    assert prior["status"]=="REPEAT_COMPLETE"
    assert ref["status"] in ("INDEPENDENT_INTERVAL_COMPLETE","INDEPENDENT_FIXED_INTERVAL_COMPLETE")
    assert ref["bits"]==550 and ref["width"]<=19 and ref["work"]<=40000000 and ref["peak"]<=2000000
    if ref["status"]=="INDEPENDENT_FIXED_INTERVAL_COMPLETE":
        assert ref["order_policy"] in ("fill-reverse","degree-reverse")
    cohort,=[c for c in prior["cohorts"] if c["bits"]==432]
    assert cohort["status"]=="SEVEN_MATCHED_PAIRS_PASS" and len(cohort["trials"])==7
    assert cohort["working_digits"]==130 and cohort["target_digits"]==100
    assert all(t["rows"][a]["status"]=="COMPLETED" and t["rows"][a]["witness"]["pass"]
               for t in cohort["trials"] for a in ("gpmc","prejoin"))
    report=dict(status="IN_PROGRESS",case=os.environ["CASE"],cnf_sha256=expected,witness_sha256=witness_sha,
                digits=130,bits=432,target_digits=100,limit_s=LIMIT,as_bytes_per_process=AS_BYTES,
                prior_gpmc_median_s=cohort["gpmc_median_s"],prior_rawmocs_median_s=cohort["rust_median_s"],
                rss_scope="sampled process-tree sum every 50ms, includes Python parent, may double-count shared pages",
                quprs_sha=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
                rawmocs_sha=subprocess.check_output(["git","-C",".rawmocs-candidate","rev-parse","HEAD"],text=True).strip(),
                gpmc_sha=subprocess.check_output(["git","-C",".gpmc","rev-parse","HEAD"],text=True).strip(),
                binaries={"gpmc":sha(GPMC),"rawmocs":sha(RAW),"native":sha(Path(rawmocs._native.__file__))},trials=[])
    def save():(ROOT/"long.json").write_text(json.dumps(report,indent=2)+"\n")
    save()
    for i in range(3):
        order=ARMS[i:]+ARMS[:i]
        trial=dict(order=list(order),rows={});report["trials"].append(trial)
        for arm in order:
            assert sha(path)==expected and sha(witness)==witness_sha
            row=run(arm,path,ROOT/f"{i}-{arm}")
            if row["status"]=="COMPLETED":
                try:
                    row["witness_upper"]=check_count(row,ref,100)
                    assert row["sampled_tree_peak_rss_kib"]>0
                except (AssertionError,ValueError) as e:
                    row.update(status="WITNESS_OR_RESOURCE_INCONCLUSIVE",error=str(e))
            trial["rows"][arm]=row;save()
            print("P4_LONG_ROW",report["case"],i,arm,row["status"],row.get("wall_ns"),flush=True)
        if any(r["status"]!="COMPLETED" for r in trial["rows"].values()):
            report["status"]="INCONCLUSIVE";save();return
        assert signature(trial["rows"]["rawmocs"])==signature(trial["rows"]["rawmocs_native"])
    for arm in ARMS:
        rows=[t["rows"][arm] for t in report["trials"]]
        assert all(signature(r)==signature(rows[0]) for r in rows)
    report["summary"]={a:{k:statistics.median(t["rows"][a][k] for t in report["trials"])
                          for k in ("wall_ns","sampled_tree_peak_rss_kib","baseline_parent_rss_kib")} for a in ARMS}
    report["status"]="THREE_MATCHED_TRIALS_PASS";save()
    print("P4_LONG_FINAL",report["case"],json.dumps(report["summary"]),flush=True)

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="worker":
        worker(sys.argv[2],Path(sys.argv[3]),Path(sys.argv[4]))
    else:main()

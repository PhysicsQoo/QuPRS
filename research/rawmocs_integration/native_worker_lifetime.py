"""P4.6d: process-lifetime mitigation probe, not an admitted in-process API."""
import gc
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import statistics
import subprocess
import sys
import time

import psutil

ROOT=Path(".p4-safety-evidence").resolve()
CNF_SHA="6fb69626195bee5b89ed3503ae8b1b4801d9267e7bd5ff3684af152afcd885e1"
REF_SHA="e59e2741a69dbb13b4f6d0b44562ac689541c4bcf7c43da476006ec8f1b87512"
LIMIT=32768
N=12

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def worker():
    import rawmocs
    from unittest.mock import patch
    from QuPRS.interface.ps2wmc import run_wmc
    from native_adapter import registered_native
    from release_transfer import check_count
    path,=Path(".p4-safety-input").rglob("*-gpmc.cnf")
    witness,=Path(".p4-safety-input").rglob("prejoin-reference.json")
    assert sha(path)==CNF_SHA and sha(witness)==REF_SHA
    ref=json.loads(witness.read_text())
    assert ref["source_sha256"]==CNF_SHA and ref["bits"]==550
    proc=psutil.Process()
    for line in sys.stdin:
        assert line.strip()=="solve"
        seen=[];old=rawmocs.solve_file
        def observe(*a,**k):
            n=old(*a,**k);seen.append(n);return n
        start=time.monotonic()
        with registered_native(130),patch.object(rawmocs,"solve_file",observe):
            count=run_wmc(path,"rawmocs_native",timeout=20,preserve_count=True)
        elapsed=time.monotonic()-start
        n,=seen
        assert n.digits==130 and n.precision_bits==432
        signature=dict(sat=n.sat,real=str(count.real),imag=str(count.imag),route=n.route)
        bound=check_count(signature,ref,100)
        del n,count,seen
        gc.collect()
        print(json.dumps(dict(signature=signature,witness_upper=bound,solver_wall_s=elapsed,
                              worker_rss_kib=proc.memory_info().rss//1024)),flush=True)

def run():
    ROOT.mkdir(exist_ok=True)
    parent=psutil.Process()
    report=dict(status="IN_PROGRESS",cnf_sha256=CNF_SHA,witness_sha256=REF_SHA,
                scope="isolated Linux worker experiment; no allocator tuning, no trim, no public API change",
                threshold_kib=LIMIT,wall_ratio_limit=1.05,rows={"persistent":[],"recycle3":[]})
    def save():(ROOT/"worker-lifetime.json").write_text(json.dumps(report,indent=2)+"\n")
    def rss_tree():
        total=parent.memory_info().rss
        for child in parent.children(recursive=True):
            try:total+=child.memory_info().rss
            except psutil.NoSuchProcess:pass
        return total//1024
    def retire(p):
        if p.poll() is None:
            p.stdin.close()
            try:p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=3)
                raise AssertionError("worker failed graceful retirement")
        assert p.returncode==0
        assert not psutil.pid_exists(p.pid) or not psutil.Process(p.pid).is_running()
        p.stdout.close()
    save();expected=None
    # Two independent sessions of six requests for each arm, alternating
    # which arm runs first. Recycling cap is explicit and not adaptive.
    for block,order in enumerate((("persistent","recycle3"),("recycle3","persistent"))):
        for arm in order:
            p=None;used=0
            with (ROOT/f"worker-{block}-{arm}.stderr").open("w") as err:
                try:
                    for i in range(6):
                        start=time.monotonic()
                        launched=p is None
                        if launched:
                            p=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),"worker"],
                                               stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                               stderr=err,text=True,bufsize=1,start_new_session=True)
                            used=0
                        p.stdin.write("solve\n");p.stdin.flush()
                        peak=rss_tree()
                        while True:
                            if time.monotonic()-start>30:raise TimeoutError("worker response timeout")
                            peak=max(peak,rss_tree())
                            if select.select([p.stdout],[],[],.05)[0]:
                                line=p.stdout.readline()
                                assert line,"worker exited before response"
                                row=json.loads(line);break
                            assert p.poll() is None
                        used+=1
                        if expected is None:expected=row["signature"]
                        assert row["signature"]==expected
                        row.update(block=block,iteration=i+1,worker_pid=p.pid,launched=launched,
                                   pre_retirement_tree_rss_kib=rss_tree(),sampled_peak_tree_rss_kib=peak)
                        # Charge graceful exit to request latency, retain the
                        # pre-retirement RSS separately so recycling cannot hide it.
                        retiring=(i==5 or (arm=="recycle3" and used==3))
                        if retiring:retire(p);p=None
                        row.update(retired=retiring,post_request_tree_rss_kib=rss_tree(),
                                   request_wall_s=time.monotonic()-start)
                        report["rows"][arm].append(row);save()
                        print("P4_WORKER_ROW",block,arm,i+1,row["request_wall_s"],
                              row["pre_retirement_tree_rss_kib"],row["post_request_tree_rss_kib"],flush=True)
                finally:
                    if p is not None and p.poll() is None:
                        os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=3)
    summary={}
    for arm,rows in report["rows"].items():
        assert len(rows)==N
        growth=[]
        for block in (0,1):
            session=[r for r in rows if r["block"]==block]
            first=max(r["pre_retirement_tree_rss_kib"] for r in session[:2])
            growth.append(max(0,max(r["pre_retirement_tree_rss_kib"] for r in session[2:])-first))
        summary[arm]=dict(max_raw_growth_kib=max(growth),
            max_pre_retirement_rss_kib=max(r["pre_retirement_tree_rss_kib"] for r in rows),
            median_pre_retirement_rss_kib=statistics.median(r["pre_retirement_tree_rss_kib"] for r in rows),
            max_sampled_peak_kib=max(r["sampled_peak_tree_rss_kib"] for r in rows),
            max_idle_rss_kib=max(r["post_request_tree_rss_kib"] for r in rows),
            median_request_wall_s=statistics.median(r["request_wall_s"] for r in rows),
            total_request_wall_s=sum(r["request_wall_s"] for r in rows),
            median_solver_wall_s=statistics.median(r["solver_wall_s"] for r in rows))
    old,new=summary["persistent"],summary["recycle3"]
    new["median_wall_ratio"]=new["median_request_wall_s"]/old["median_request_wall_s"]
    new["total_wall_ratio"]=new["total_request_wall_s"]/old["total_request_wall_s"]
    checks=dict(raw_growth=new["max_raw_growth_kib"]<=LIMIT,
                absolute_max=new["max_pre_retirement_rss_kib"]<=old["max_pre_retirement_rss_kib"],
                absolute_median=new["median_pre_retirement_rss_kib"]<=old["median_pre_retirement_rss_kib"],
                peak=new["max_sampled_peak_kib"]<=old["max_sampled_peak_kib"],
                median_wall=new["median_wall_ratio"]<=1.05,total_wall=new["total_wall_ratio"]<=1.05)
    passed=all(checks.values())
    report.update(status="WORKER_LIFETIME_SCREEN_PASS" if passed else "WORKER_LIFETIME_REVIEW",
                  summary=summary,checks=checks,admission="HOLD_IN_PROCESS")
    save()
    print("P4_WORKER_LIFETIME_FINAL",json.dumps(dict(status=report["status"],summary=summary,checks=checks)),flush=True)
    assert passed,"worker-lifetime candidate requires review"

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="worker":worker()
    else:run()

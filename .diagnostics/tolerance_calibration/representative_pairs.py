"""Source-pinned, resource-bounded Python Hybrid A/B pilot on three existing pairs.

A/B is diagnostic: source-phase preserving candidate vs historical gate snap.
This is *not* a precision-certified approximate-equivalence benchmark and
single trial walltimes are not performance regressions on a fixed host.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"tolerance-calibration-results"
OUT.mkdir(exist_ok=True)
CASES={
    "qft16":(
        "benchmarks/MQTBench/h,ry,rz,cx/qft_nativegates_ibm_qiskit_opt0_16.qasm",
        "benchmarks/MQTBench/qft_nativegates_ibm_qiskit_opt0_16.qasm",
        "Proportional",
    ),
    "qpeexact8":(
        "benchmarks/MQTBench/qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
        "benchmarks/MQTBench/h,ry,rz,cx/qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
        "Proportional",
    ),
    "graphstate16":(
        "benchmarks/MQTBench/graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
        "benchmarks/MQTBench/h,ry,rz,cx/graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
        "Naive",
    ),
}
QPE_SHA256=(
    "8d514d06f7c9e81abda1042796cc34227624c9ed66097bee1ce5e97a87884dda",
    "227ab45a4eb033889aa57bb53e54938e74d757fea30eaa3d276b495048dc6141",
)

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def worker(case,mode):
    from QuPRS import check_equivalence, config
    from QuPRS.pathsum.gates import single_qubit,two_qubit
    from QuPRS.utils.util import reduce_expression as original
    left,right,strategy=CASES[case]
    a,b=ROOT/left,ROOT/right
    if mode=="historical_snap":
        def local_snap(expr,*args,**kwargs):
            kwargs["drop_small"]=True
            return original(expr,*args,**kwargs)
        single_qubit.reduce_expression=local_snap
        two_qubit.reduce_expression=local_snap
    t0=time.perf_counter()
    try:
        # Historically QuPRS's API is allowed to return unknown for
        # incomplete RR; no force-exact "equivalent" expected for QPE/graph.
        result=check_equivalence(
            str(a),str(b),backend="python",method="hybrid",
            strategy=strategy,tool_name="gpmc",timeout=30,
            wmc_policy="legacy",wmc_magnitude_tolerance=1e-8,
            wmc_phase_tolerance=1e-8,
        )
        record={
            "case":case,"mode":mode,
            "status":str(result.equivalent),
            "walltime_seconds":time.perf_counter()-t0,
            "pathsum_time":result.pathsum_time,
            "solver_time":result.tool_time,
            "wmc_invoked":result.tool_time is not None,
            "reduction_counts":result.Statistics.get_reduction_counts(),
            "residual_phase_sha256":hashlib.sha256(
                str(result.final_pathsum.P).encode()
            ).hexdigest() if result.final_pathsum is not None else None,
            "source_sha256":(digest(a),digest(b)),
            "strategy":strategy,"rr_tolerance":config.get_tolerance(),
        }
        print("BENCH_RESULT="+json.dumps(record,default=str,sort_keys=True),flush=True)
        return 0
    except Exception as exc:
        print("BENCH_RESULT="+json.dumps({
            "case":case,"mode":mode,"status":"ERROR",
            "error":f"{type(exc).__name__}: {exc}",
            "walltime_seconds":time.perf_counter()-t0,
            "source_sha256":(digest(a),digest(b))
        },sort_keys=True),flush=True)
        return 2

def sampled_rss(pid):
    try:
        import psutil
        p=psutil.Process(pid)
        return sum(child.memory_info().rss for child in [p]+p.children(recursive=True)
                   if child.is_running())
    except Exception:
        return 0

def trial(case,mode,deadline_seconds=45,rss_cap_mib=3072):
    import psutil
    cmd=[sys.executable,"-u",__file__,"--worker",case,mode]
    start=time.monotonic()
    with tempfile.TemporaryFile(mode="w+t") as stdout, tempfile.TemporaryFile(mode="w+t") as stderr:
        proc=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,cwd=ROOT,
                              start_new_session=os.name=="posix")
        peak=0
        reason=None
        while proc.poll() is None:
            peak=max(peak,sampled_rss(proc.pid))
            if peak>rss_cap_mib*1024*1024:
                reason="RESOURCE_MEMORY_CAP"
                break
            if time.monotonic()-start>deadline_seconds:
                reason="INCONCLUSIVE_RESOURCE_TIMEOUT"
                break
            time.sleep(0.035)
        if reason and proc.poll() is None:
            if os.name=="posix":
                os.killpg(proc.pid,signal.SIGKILL)
            else:
                proc.kill()
            proc.wait(timeout=5)
        elapsed=time.monotonic()-start
        stdout.seek(0);stderr.seek(0)
        out=stdout.read();err=stderr.read()
    rows=[s.split("BENCH_RESULT=",1)[1] for s in out.splitlines()
          if "BENCH_RESULT=" in s]
    result=json.loads(rows[-1]) if rows else {"case":case,"mode":mode,
       "status":reason or "ERROR","reason":"no result marker"}
    result.update({
        "worker_exit_code":proc.returncode,
        "observed_elapsed_seconds":elapsed,
        "sampled_peak_process_tree_rss_mib":round(peak/1048576,3),
        "limit_reason":reason,
        "stderr_tail":err[-1200:],
        "stdout_tail":out[-500:] if not rows else "",
        "source_head":os.getenv("GITHUB_SHA"),
    })
    return result

def main():
    # All pairs come from an existing checked-in corpus and are not enlarged.
    identity={}
    for case,(source,target,strategy) in CASES.items():
        a,b=ROOT/source,ROOT/target
        if not a.is_file() or not b.is_file():
            raise FileNotFoundError((case,a,b))
        identity[case]={
            "paths":(source,target),"sha256":(digest(a),digest(b)),
            "strategy":strategy,
        }
    assert tuple(identity["qpeexact8"]["sha256"])==QPE_SHA256
    (OUT/"representative-identity.json").write_text(json.dumps({
        "source_ref":os.environ.get("GITHUB_SHA"),
        "python":sys.version,"platform":platform.platform(),
        "limits":{"wall_sec_per_worker":45,"rss_mib_per_worker":3072},
        "cases":identity,
        "limitations":"One paired hosted runner; not statistical timing or equivalence proof."
    },indent=2)+"\n")
    records=[]
    # Small balanced order to reduce persistent machine drift.
    for case,modes in [
        ("qft16",("historical_snap","phase_preserving")),
        ("qpeexact8",("phase_preserving","historical_snap")),
        ("graphstate16",("historical_snap","phase_preserving")),
    ]:
        for mode in modes:
            result=trial(case,mode)
            records.append(result)
            with (OUT/"representative-samples.jsonl").open("a") as f:
                f.write(json.dumps(result,sort_keys=True,default=str)+"\n")
            print("REPRESENTATIVE",json.dumps({
                key:result.get(key) for key in (
                    "case","mode","status","walltime_seconds",
                    "observed_elapsed_seconds","reduction_counts",
                    "sampled_peak_process_tree_rss_mib","limit_reason"
                )
            },default=str),flush=True)
    per_case={}
    for case in CASES:
        subset=[r for r in records if r["case"]==case]
        if len(subset)!=2:raise AssertionError((case,subset))
        status=[s["status"] for s in subset]
        valid=all(s.get("worker_exit_code")==0 and s.get("limit_reason") is None
                  and s.get("status") not in ("ERROR","timeout","memoryout") for s in subset)
        per_case[case]={
            "statuses":status,
            "both_completed":valid,
            "status_difference":valid and status[0]!=status[1],
            "runtime_ratio_candidate_over_legacy":(
                next(r["observed_elapsed_seconds"] for r in subset
                     if r["mode"]=="phase_preserving")/
                next(r["observed_elapsed_seconds"] for r in subset
                     if r["mode"]=="historical_snap")
            ) if valid else None,
            "limitations":"One sample per mode; observational only",
        }
    summary={"run_records":len(records),"results":per_case,
             "fully_completed_cases":sum(v["both_completed"] for v in per_case.values()),
             "conclusion":"REPORT_ONLY",
             "statuses_from_source_at":"Source-literal QASM input; not a global approximate-equivalence oracle"}
    (OUT/"representative-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("REPRESENTATIVE_SUMMARY",json.dumps(summary,sort_keys=True),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--worker",nargs=2,metavar=("CASE","MODE"))
    args=p.parse_args()
    if args.worker:
        case,mode=args.worker
        if case not in CASES or mode not in ("historical_snap","phase_preserving"):
            p.error("invalid benchmark case/mode")
        raise SystemExit(worker(case,mode))
    main()

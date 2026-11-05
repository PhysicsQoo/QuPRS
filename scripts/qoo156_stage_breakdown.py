#!/usr/bin/env python3
"""Experimental source-pinned CLK_MONOTONIC parent/worker phase profiling."""
import argparse,hashlib,json,os,platform,random,statistics as st,subprocess,tempfile,time
from pathlib import Path
from qoo156_cli_abba import CASES

P=["entry","guards_ready","resource_preflight_done","private_tmpdir_ready",
"spool_files_ready","spawn_begin","spawn_returned","admission_sent",
"capture_threads_ready","worker_and_eof_done","descendants_cleaned",
"cgroup_cleanup_done","private_tmpdir_cleaned","capture_join_done","output_published"]
W=["entry","args_parsed","authorized","prepared","engine_begin","engine_end"]
CATS=["parent_setup","worker_boot_admission","native_engine",
"worker_exit_and_pipe_eof","cleanup_and_publish"]
MICRO=["guards","private_tempdir_create","spool_files_create",
"command_configuration","spawn_syscall","worker_clap_authorization",
"capture_threads_spawn","descendants_cleanup","private_tempdir_dispose",
"final_join_and_publish","profiled_parent_total","external_wall",
"unattributed_process_and_probe"]
M=lambda x:x/1e6
median=st.median
def ci(values):
    rng=random.Random(156)
    v=sorted(median(rng.choices(values,k=len(values))) for _ in range(2000))
    return [v[49],v[1949]]
def measure(binary,case,root,trace=None):
    cmd=[str(binary),*[str(root/x) for x in CASES[case]],"--timeout","30","--quiet"]
    if case!="single_h": cmd+=["--method","reduction-rules","--strategy","straightforward"]
    env=os.environ.copy()
    env.pop("QUPRS_CLI_STAGE_PROFILE_FILE",None)
    if trace:env["QUPRS_CLI_STAGE_PROFILE_FILE"]=str(trace)
    start=time.perf_counter_ns()
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     stdin=subprocess.DEVNULL,env=env,timeout=32)
    elapsed=M(time.perf_counter_ns()-start)
    if p.returncode:raise RuntimeError(f"{case} rc={p.returncode}: {p.stderr[-600:]}")
    expect=b"Reduced PathSum State" if case=="single_h" else b"equivalent"
    if expect.lower() not in p.stdout.lower():raise RuntimeError("missing science result")
    digest=hashlib.sha256(p.stdout).hexdigest()
    if trace is None:return elapsed,digest,None
    data={}
    for scope,keys in [("parent",P),("worker",W)]:
        filename=Path(str(trace)+"."+scope)
        if not filename.exists():raise RuntimeError(f"missing profile {filename}")
        pairs=[x.split("\t") for x in filename.read_text().splitlines()]
        obj={k:int(v) for k,v in pairs}
        if len(obj)!=len(pairs) or set(keys)-set(obj):
            raise RuntimeError(f"invalid stages for {scope}: {obj}")
        if any(obj[y]<obj[x] for x,y in zip(keys,keys[1:])):
            raise RuntimeError(f"nonmonotonic {scope}: {obj}")
        data[scope]=obj
        filename.unlink()
    a,b=data["parent"],data["worker"]
    part={
    "parent_setup":a["spawn_begin"]-a["entry"],
    "worker_boot_admission":b["engine_begin"]-a["spawn_begin"],
    "native_engine":b["engine_end"]-b["engine_begin"],
    "worker_exit_and_pipe_eof":a["worker_and_eof_done"]-b["engine_end"],
    "cleanup_and_publish":a["output_published"]-a["worker_and_eof_done"]}
    if any(v<0 for v in part.values()):
        raise RuntimeError(f"invalid cross-process clock partition: {part}")
    if sum(part.values())!=a["output_published"]-a["entry"]:
        raise RuntimeError("phase partition does not sum to parent interval")
    micro={
    "guards":a["guards_ready"]-a["entry"],
    "private_tempdir_create":a["private_tmpdir_ready"]-a["resource_preflight_done"],
    "spool_files_create":a["spool_files_ready"]-a["private_tmpdir_ready"],
    "command_configuration":a["spawn_begin"]-a["spool_files_ready"],
    "spawn_syscall":a["spawn_returned"]-a["spawn_begin"],
    "worker_clap_authorization":b["engine_begin"]-b["entry"],
    "capture_threads_spawn":a["capture_threads_ready"]-a["admission_sent"],
    "descendants_cleanup":a["descendants_cleaned"]-a["worker_and_eof_done"],
    "private_tempdir_dispose":a["private_tmpdir_cleaned"]-a["cgroup_cleanup_done"],
    "final_join_and_publish":a["output_published"]-a["private_tmpdir_cleaned"],
    "profiled_parent_total":a["output_published"]-a["entry"],
    "external_wall":elapsed*1e6,
    "unattributed_process_and_probe":elapsed*1e6-(a["output_published"]-a["entry"])}
    return elapsed,digest,{"partition_ms":{k:M(v) for k,v in part.items()},
         "micro_ms":{k:M(v) for k,v in micro.items()},
         "parent_ns":a,"worker_ns":b}
def summary(raw,category,keys):
    return {key:{"median_ms":median([x[category][key] for x in raw]),
                 "ci95_ms":ci([x[category][key] for x in raw])} for key in keys}
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ["binary","workspace","output"]:
        ap.add_argument("--"+name,type=Path,required=True)
    ap.add_argument("--sha",required=True)
    ap.add_argument("--repetitions",type=int,default=45)
    ap.add_argument("--control-blocks",type=int,default=16)
    o=ap.parse_args()
    if not 15<=o.repetitions<=100 or not 10<=o.control_blocks<=50:
        ap.error("bounded repetitions / control-blocks required")
    if hasattr(os,"sched_getaffinity"):
        allowed=sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0,{allowed[0]})
    result={"schema":"qoo156-source-stage-v1","source_sha":o.sha,
            "probe_research_only":True,"clock":"CLOCK_MONOTONIC Linux",
            "runner":{"name":os.environ.get("RUNNER_NAME"),"platform":platform.platform(),
            "affinity":sorted(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else []},
            "cases":{}}
    with tempfile.TemporaryDirectory(prefix="qoo156-stage-") as tmp:
      store=Path(tmp)
      for case in CASES:
        expect=None
        for n in range(10):
            _,hashvalue,_=measure(o.binary,case,o.workspace,
              store/f"warmup-{case}-{n}" if n%2 else None)
            expect=expect or hashvalue
            if hashvalue!=expect:raise RuntimeError("warmup output mismatch")
        rows=[]
        for n in range(o.repetitions):
            elapsed,hashvalue,phase=measure(o.binary,case,o.workspace,
                                        store/f"stages-{case}-{n}")
            if hashvalue!=expect:raise RuntimeError("profile science output mismatch")
            rows.append({"external_wall_ms":elapsed,**phase})
        diffs=[];blocks=[]
        for n in range(o.control_blocks):
            order=["off","on","on","off"] if n%2==0 else ["on","off","off","on"]
            obs=[]
            for i,mode in enumerate(order):
                elapsed,hashvalue,_=measure(o.binary,case,o.workspace,
                    store/f"control-{case}-{n}-{i}" if mode=="on" else None)
                if hashvalue!=expect:raise RuntimeError("control science output mismatch")
                obs.append({"mode":mode,"wall_ms":elapsed})
            on=[x["wall_ms"] for x in obs if x["mode"]=="on"]
            off=[x["wall_ms"] for x in obs if x["mode"]=="off"]
            diff=st.mean(on)-st.mean(off)
            diffs.append(diff)
            blocks.append({"round":n+1,"order":order,"samples":obs,"delta_ms":diff})
        result["cases"][case]={
            "science_sha256":expect,"raw":rows,
            "partition":summary(rows,"partition_ms",CATS),
            "micro":summary(rows,"micro_ms",MICRO),
            "probe_control":{"blocks":blocks,"median_on_minus_off_ms":median(diffs),
                             "ci95_ms":ci(diffs)}}
        d=result["cases"][case]
        print(case+", partition median ms: "+", ".join(
            f"{k}={d['partition'][k]['median_ms']:.3f}" for k in CATS)
            +f"; observer penalty={median(diffs):+.3f}ms",flush=True)
    o.output.parent.mkdir(parents=True,exist_ok=True)
    o.output.write_text(json.dumps(result,indent=2)+"\n")
    lines=["# QOO-156 research-only parent/worker stage profile",
           "Monotonic cross-process timestamps; I/O profiling instrumentation is not release cost.",
           "| Circuit | "+ " | ".join(CATS)+" | Observer penalty |",
           "|---|"+ "|---:"*(len(CATS)+1)+"|"]
    for case,d in result["cases"].items():
        lines.append("| "+case+" | "+" | ".join(
            f"{d['partition'][k]['median_ms']:.3f}ms" for k in CATS)
            +f" | {d['probe_control']['median_on_minus_off_ms']:+.3f}ms |")
    for case,d in result["cases"].items():
        lines+=["","## "+case,"| Stage | Median ms |","|---|---:|"]
        lines += [f"| {k} | {d['micro'][k]['median_ms']:.4f} |" for k in MICRO]
    lines += ["","Stage group medians cannot be summed as if they were one sample.",
              "Worker writes a trace after engine_end, so exit/EOF includes observer I/O.",
              "The experiment's parent writes a trace after output_published.",
              "Use source-pinned, uninstrumented ABBA for causal release-cost comparisons."]
    o.output.with_suffix(".md").write_text("\n".join(lines)+"\n")
    print("QOO156_STAGE_BREAKDOWN_CAPTURED=TRUE",flush=True)
if __name__=="__main__":
    main()

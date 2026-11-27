"""I3b: matched explicit CPR opt-in vs current main, original frozen cases.
Same request and resource limits. Preserve censored main, no numeric speedup
without completed pairs. No threshold tuning, no repeat-to-pass.
"""
import hashlib,json,os,re,statistics,subprocess,tempfile
from pathlib import Path
from cpr_hh_n5c import entries as heavy_entries
from cpr_c3_matched import entries as easy_entries,emit
from cpr_rr_first import binary_status,repetitions
from cpr_router_acceptance import limit
from conditional_rr_stitch import ROOT
ARMS=("main","cpr")
def entries():
    return [(False,*e) for e in easy_entries()]+[(True,*e) for e in heavy_entries()]
def attempted():
    return sum(2*repetitions(n,v) for _,n,v,*_ in entries())
def native():
    bins={a:Path(os.environ["CPR_BIN_"+a.upper()]).resolve() for a in ARMS}
    for arm,p in bins.items():
        emit("CPR_I3B_BINARY",arm=arm,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    errors=[];blocks=[];drift=[];counts={a:0 for a in ARMS};heavy_counts={a:0 for a in ARMS}
    for heavy,name,variant,n,source,target in entries():
        paths=[]
        for entry in (source,target):
            p=ROOT/entry["path"];data=p.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            paths.append(p)
        reps=repetitions(name,variant)
        rows={a:{} for a in ARMS}
        for rep in range(reps):
            for pos,arm in enumerate(ARMS if rep%2==0 else ARMS[::-1]):
                env={k:v for k,v in os.environ.items() if not k.startswith(("CPR_","CRR_")) and k!="QUPRS_STAGE_LEDGER"}
                env.update(CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]))
                with tempfile.TemporaryDirectory() as tmp:
                    meter=Path(tmp)/"meter"
                    cmd=["/usr/bin/time","-f","%e %M","-o",str(meter),"timeout","--kill-after=2s","35s",str(bins[arm])]
                    if arm=="main":cmd.append("public")
                    r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,preexec_fn=limit)
                    resource=meter.read_text().splitlines()[-1].split() if meter.exists() and meter.read_text().strip() else []
                outer,rss=(float(resource[0]),int(resource[1])) if len(resource)==2 else (None,None)
                calls=[l for l in r.stdout.splitlines() if l.startswith("CPR_PUBLIC ")]
                row=dict(re.findall(r"(\w+)=([^ ]+)",calls[0])) if len(calls)==1 else {}
                verdict=binary_status(row.get("status"))
                if r.returncode in (124,137) or "memory allocation" in r.stderr.lower():status="CENSORED"
                elif r.returncode or outer is None or len(calls)!=1 or "CPR_PUBLIC_ERROR " in r.stdout:status="ERROR"
                elif verdict:status="COMPLETE"
                else:status="INCOMPLETE"
                if status=="COMPLETE":
                    counts[arm]+=1
                    if heavy:heavy_counts[arm]+=1
                    rows[arm][rep]=dict(row,outer_s=outer,rss_kib=rss)
                elif not heavy or arm=="cpr" or status=="ERROR":
                    errors.append([name,variant,rep,arm,status])
                emit("CPR_I3B_TRIAL",case=name,variant=variant,heavy=heavy,arm=arm,repeat=rep,position=pos,status=status,verdict=verdict if status=="COMPLETE" else None,native=row,outer_s=outer,rss_kib=rss,returncode=r.returncode,stdout=r.stdout[-1200:] if status!="COMPLETE" else "",stderr=r.stderr[-1200:] if status!="COMPLETE" else "")
        for arm in ARMS:
            rs=list(rows[arm].values())
            emit("CPR_I3B_SUMMARY",case=name,variant=variant,heavy=heavy,arm=arm,complete=len(rs),attempted=reps,median_total_s=statistics.median(float(r["total_s"]) for r in rs) if rs else None,median_rss_kib=statistics.median(r["rss_kib"] for r in rs) if rs else None)
        both=sorted(set(rows["main"])&set(rows["cpr"]))
        for i in both:
            a,b=rows["main"][i],rows["cpr"][i]
            for key in ("status","solver","rr_approximate","precision_reason"):
                if a.get(key)!=b.get(key) and (not heavy or key=="status"):drift.append([name,variant,i,key,a.get(key),b.get(key)])
        if len(both)!=reps:
            if not heavy:blocks.append([name,variant,"insufficient_pairs"])
            emit("CPR_I3B_PAIR",case=name,variant=variant,matched=len(both),gained=sorted(set(rows["cpr"])-set(rows["main"])),lost=sorted(set(rows["main"])-set(rows["cpr"])),status="INSUFFICIENT_MATCHED_PAIRS")
            continue
        limits={"total_s":(0.05,0.000025),"rss_kib":(0.05,512)}
        if statistics.median(rows["main"][i]["outer_s"] for i in both)>=0.1:limits["outer_s"]=(0.05,0.01)
        for metric,(fraction,floor) in limits.items():
            a=[float(rows["main"][i][metric]) for i in both];b=[float(rows["cpr"][i][metric]) for i in both]
            delta=statistics.median(y-x for x,y in zip(a,b));allowed=max(floor,fraction*statistics.median(a))
            emit("CPR_I3B_PERF",case=name,variant=variant,metric=metric,paired_delta_median=delta,allowed_delta=allowed,status="WITHIN_BUDGET" if delta<=allowed else "BLOCKED")
            if delta>allowed:blocks.append([name,variant,metric,delta,allowed])
    emit("CPR_I3B_NATIVE_GATE",attempted=attempted(),counts=counts,heavy_counts=heavy_counts,errors=errors,drift=drift,perf_blocks=blocks)
    assert attempted()==160 and counts["cpr"]==80 and heavy_counts["cpr"]==20 and not errors and not drift and not blocks
def source_parity():
    from conditional_rr_source_ball import load,controls,dense_overlap,EPS,acb,ctx
    from conditional_rr_tensor_source import tensor_trace,controls as tensor_controls
    controls();tensor_controls();assert ctx.prec==2048
    receipts=[json.loads(l.split(" ",1)[1]) for l in Path(os.environ["CRR_GENERIC_LOG"]).read_text().splitlines() if l.startswith("CPR_I3B_TRIAL ")]
    assert len(receipts)==attempted() and len({(r["case"],r["variant"],r["arm"],r["repeat"]) for r in receipts})==len(receipts)
    completed=[r for r in receipts if r["status"]=="COMPLETE"];errors=[];matched=0
    for heavy,name,variant,n,source,target in entries():
        rows=[r for r in completed if (r["case"],r["variant"])==(name,variant)]
        if not rows:continue
        a,ha=load(source,n);b,hb=load(target,n)
        try:z,meta=tensor_trace(a,b,n);method="tensor_trace"
        except ValueError:
            if n>8:raise
            z=sum((dense_overlap(a,b,k,n) for k in range(1<<n)),acb(0))/(1<<n);meta={};method="dense"
        threshold=(1-EPS*EPS).sqrt()
        expected="Equivalent" if abs(z).lower()>threshold else "NotEquivalent" if abs(z).upper()<threshold else "INCONCLUSIVE"
        for r in rows:
            ok=r["verdict"]==expected
            if not ok:errors.append([name,variant,r["arm"],r["repeat"],expected,r["verdict"]])
            matched+=int(ok)
            emit("CPR_I3B_SOURCE",case=name,variant=variant,arm=r["arm"],repeat=r["repeat"],matched=ok,source_verdict=expected,source_sha256=ha,target_sha256=hb,method=method,**meta)
    emit("CPR_I3B_SOURCE_GATE",matched=matched,completed=len(completed),errors=errors)
    assert matched==len(completed) and not errors and sum(r["arm"]=="cpr" for r in completed)==80
if __name__=="__main__":
    if os.environ.get("CRR_GENERIC_LOG"):source_parity()
    else:native()

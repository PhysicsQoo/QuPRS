"""N5a: public native no-lift control cohort, main vs HH-fixed branch.
Frozen C3a source pairs and RR-first repeat counts, paired order, existing
5%/absolute floors; no adaptive search, no replacement trials, no pooling.
Verdict source oracle is independent. Full public phase/error and CodSpeed
admission remain separate gates.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import tempfile
from cpr_native_i3b import easy_entries as entries, binary_status, repetitions, emit, limit, ROOT

ARMS=("main","fixed")
def expected_trials():
    return sum(2*repetitions(name,variant) for name,variant,*_ in entries())

def native():
    bins={a:Path(os.environ["CPR_BIN_"+a.upper()]).resolve() for a in ARMS}
    for a,p in bins.items():
        assert p.is_file()
        emit("CPR_N5A_BINARY",arm=a,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    blocks=[];errors=[];drift=[];complete=0
    for name,variant,n,source,target in entries():
        paths=[]
        for entry in (source,target):
            p=ROOT/entry["path"];data=p.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            emit("CPR_N5A_SOURCE",case=name,variant=variant,path=entry["path"],sha256=hashlib.sha256(data).hexdigest())
            paths.append(p)
        repeats=repetitions(name,variant)
        rows={a:{} for a in ARMS}
        for rep in range(repeats):
            for pos,arm in enumerate(ARMS if rep%2==0 else ARMS[::-1]):
                env={k:v for k,v in os.environ.items() if not k.startswith(("CPR_","CRR_")) and k!="QUPRS_STAGE_LEDGER"}
                env.update(CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]))
                with tempfile.TemporaryDirectory() as tmp:
                    meter=Path(tmp)/"meter"
                    r=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(meter),"timeout","--kill-after=2s","35s",str(bins[arm]),"public"],cwd=ROOT,env=env,capture_output=True,text=True,preexec_fn=limit)
                    resource=meter.read_text().splitlines()[-1].split() if meter.exists() and meter.read_text().strip() else []
                outer,rss=(float(resource[0]),int(resource[1])) if len(resource)==2 else (None,None)
                lines=[l for l in r.stdout.splitlines() if l.startswith(("CPR_PUBLIC ","CPR_PUBLIC_ERROR "))]
                calls=[l for l in lines if l.startswith("CPR_PUBLIC ")]
                row=dict(re.findall(r"(\w+)=([^ ]+)",calls[0])) if len(calls)==1 else {}
                if len(calls)==1 and " precision_reason=" in calls[0]:
                    row["precision_reason"]=calls[0].split(" precision_reason=",1)[1]
                verdict=binary_status(row.get("status"))
                if r.returncode in (124,137) or "memory allocation" in r.stderr.lower():status="CENSORED"
                elif r.returncode or outer is None or len(calls)!=1 or any(l.startswith("CPR_PUBLIC_ERROR ") for l in lines):status="ERROR"
                elif verdict:status="COMPLETE"
                else:status="INCOMPLETE"
                if status=="COMPLETE":
                    complete+=1
                    rows[arm][rep]=dict(row,outer_s=outer,rss_kib=rss,binary_verdict=verdict)
                else:errors.append([name,variant,rep,arm,status])
                emit("CPR_N5A_TRIAL",case=name,variant=variant,repeat=rep,position=pos,arm=arm,status=status,verdict=verdict if status=="COMPLETE" else None,native=row,outer_s=outer,rss_kib=rss,returncode=r.returncode,stderr=r.stderr[-1000:] if status!="COMPLETE" else "")
        for arm in ARMS:
            rs=list(rows[arm].values())
            emit("CPR_N5A_SUMMARY",case=name,variant=variant,arm=arm,complete=len(rs),attempted=repeats,median_total_s=statistics.median(float(r["total_s"]) for r in rs) if rs else None,median_rss_kib=statistics.median(r["rss_kib"] for r in rs) if rs else None,solver_calls=sum(r.get("solver")=="true" for r in rs))
        both=sorted(set(rows["main"])&set(rows["fixed"]))
        if len(both)!=repeats:
            blocks.append([name,variant,"insufficient_matched_samples",len(both),repeats]);continue
        for rep in both:
            a,b=rows["main"][rep],rows["fixed"][rep]
            for key in ("status","solver","rr_approximate","precision_reason"):
                if a.get(key)!=b.get(key):drift.append([name,variant,rep,key,a.get(key),b.get(key)])
        limits={"total_s":(0.05,0.000025),"rss_kib":(0.05,512)}
        if statistics.median(rows["main"][i]["outer_s"] for i in both)>=0.1:limits["outer_s"]=(0.05,0.01)
        else:emit("CPR_N5A_PERF",case=name,variant=variant,metric="outer_s",status="RESOLUTION_LIMITED")
        for metric,(fraction,floor) in limits.items():
            a=[float(rows["main"][i][metric]) for i in both]
            b=[float(rows["fixed"][i][metric]) for i in both]
            deltas=[y-x for x,y in zip(a,b)]
            delta=statistics.median(deltas);allowed=max(floor,fraction*statistics.median(a))
            passed=delta<=allowed
            emit("CPR_N5A_PERF",case=name,variant=variant,metric=metric,baseline_median=statistics.median(a),candidate_median=statistics.median(b),paired_delta_median=delta,allowed_delta=allowed,paired_deltas=deltas,status="WITHIN_BUDGET" if passed else "BLOCKED")
            if not passed:blocks.append([name,variant,metric,delta,allowed])
    emit("CPR_N5A_NATIVE_GATE",complete=complete,attempted=expected_trials(),errors=errors,public_contract_drift=drift,perf_blocks=blocks)
    assert expected_trials()==120 and complete==expected_trials() and not errors and not drift and not blocks

def source_parity():
    from conditional_rr_source_ball import load, controls, dense_overlap, EPS, acb, ctx
    from conditional_rr_tensor_source import tensor_trace, controls as tensor_controls
    controls();tensor_controls();assert ctx.prec==2048
    receipts=[json.loads(l.split(" ",1)[1]) for l in Path(os.environ["CRR_GENERIC_LOG"]).read_text().splitlines() if l.startswith("CPR_N5A_TRIAL ")]
    assert len(receipts)==expected_trials()
    assert len({(r["case"],r["variant"],r["arm"],r["repeat"]) for r in receipts})==len(receipts)
    completed=[r for r in receipts if r["status"]=="COMPLETE"]
    matched=0;missing=0
    for name,variant,n,source,target in entries():
        rows=[r for r in completed if (r["case"],r["variant"])==(name,variant)]
        if not rows:continue
        try:
            a,ha=load(source,n);b,hb=load(target,n)
            try:z,meta=tensor_trace(a,b,n);method="tensor_trace"
            except ValueError:
                if n>8:raise
                z=sum((dense_overlap(a,b,k,n) for k in range(1<<n)),acb(0))/(1<<n);meta={};method="dense"
        except ValueError as e:
            missing+=len(rows)
            emit("CPR_N5A_SOURCE_ADMISSION",case=name,variant=variant,status="UNVERIFIED",reason=str(e));continue
        threshold=(1-EPS*EPS).sqrt()
        verdict="Equivalent" if abs(z).lower()>threshold else "NotEquivalent" if abs(z).upper()<threshold else "INCONCLUSIVE"
        for r in rows:
            ok=r["verdict"]==verdict;matched+=int(ok)
            emit("CPR_N5A_SOURCE_PARITY",case=name,variant=variant,arm=r["arm"],repeat=r["repeat"],matched=ok,source_verdict=verdict,source_sha256=ha,target_sha256=hb,method=method,**meta)
    emit("CPR_N5A_SOURCE_GATE",matched=matched,completed=len(completed),attempted=len(receipts),unverified=missing)
    assert matched==len(completed)==expected_trials() and missing==0

if __name__=="__main__":
    if os.environ.get("CRR_GENERIC_LOG"):source_parity()
    else:native()

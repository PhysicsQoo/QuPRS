"""N5c: frozen five previously source-confirmed heavy CPR coordinates.
Current main public API, pre-HH-fix CPR and post-fix CPR, same policy.
No adaptive admission, no new cases, no cap increase, no resampling.
Censored main rows are retained and never turned into numeric speedup.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import tempfile
from cpr_rr_first import entries as prior_entries, EXTRA, binary_status, repetitions
from cpr_c3_matched import emit
from cpr_router_acceptance import limit
from conditional_rr_stitch import ROOT

ARMS=("main","pre_fix","fixed")
def entries():
    rows=[e for e in prior_entries() if e[:2] in EXTRA]
    assert len(rows)==len(EXTRA)==5
    return rows

def expected_trials():
    return sum(len(ARMS)*repetitions(n,v) for n,v,*_ in entries())

def native():
    bins={a:Path(os.environ["CPR_BIN_"+a.upper()]).resolve() for a in ARMS}
    for arm,binary in bins.items():
        assert binary.is_file()
        emit("CPR_N5C_BINARY",arm=arm,sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    errors=[];blocks=[];drifts=[];censored=[];gains=[];lost=[];counts=dict.fromkeys(ARMS,0)
    for name,variant,n,source,target in entries():
        paths=[]
        for entry in (source,target):
            p=ROOT/entry["path"];data=p.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            emit("CPR_N5C_SOURCE",case=name,variant=variant,path=entry["path"],sha256=hashlib.sha256(data).hexdigest())
            paths.append(p)
        repeats=repetitions(name,variant)
        rows={a:{} for a in ARMS}
        for rep in range(repeats):
            shift=rep%len(ARMS)
            for pos,arm in enumerate(ARMS[shift:]+ARMS[:shift]):
                env={k:v for k,v in os.environ.items() if not k.startswith(("CPR_","CRR_")) and k!="QUPRS_STAGE_LEDGER"}
                env.update(CRR_CASE=name,CRR_VARIANT=variant,CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]),CRR_POLICY="strict",CRR_SCHEDULE="difference",CRR_GENERIC_ARM="conditional_router",CRR_BRA_RESCUE="1",CRR_LIFT_INDEXED="1")
                if arm!="main":env["CPR_RR_FIRST"]="1"
                mode="public" if arm=="main" else "cpr"
                with tempfile.TemporaryDirectory() as tmp:
                    meter=Path(tmp)/"meter"
                    r=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(meter),"timeout","--kill-after=2s","35s",str(bins[arm]),mode],cwd=ROOT,env=env,capture_output=True,text=True,preexec_fn=limit)
                    resource=meter.read_text().splitlines()[-1].split() if meter.exists() and meter.read_text().strip() else []
                outer,rss=(float(resource[0]),int(resource[1])) if len(resource)==2 else (None,None)
                lines=[l for l in r.stdout.splitlines() if l.startswith(("CPR_PUBLIC ","CPR_PUBLIC_ERROR ","CRR_GENERIC_CALL ","CRR_GENERIC_STOP ","CRR_GENERIC_TRIGGER ","CRR_POLICY_SUMMARY ","CPR_ROUTE ","CPR_A2_DECISION "))]
                for l in lines:print(l+" comparison_arm="+arm+" repeat="+str(rep),flush=True)
                pfx="CPR_PUBLIC " if arm=="main" else "CRR_GENERIC_CALL "
                calls=[dict(re.findall(r"(\w+)=([^ ]+)",l)) for l in lines if l.startswith(pfx)]
                row=calls[0] if len(calls)==1 else {}
                verdict=binary_status(row.get("status") if arm=="main" else row.get("verdict"))
                if r.returncode in (124,137) or "memory allocation" in r.stderr.lower():status="CENSORED"
                elif r.returncode or outer is None or len(calls)>1 or any(l.startswith("CPR_PUBLIC_ERROR ") for l in lines):status="ERROR"
                elif verdict and (arm=="main" or row.get("status")=="complete"):status="COMPLETE"
                elif row or any(l.startswith("CRR_GENERIC_STOP ") for l in lines):status="INCOMPLETE"
                else:status="ERROR"
                if any(l.startswith("CPR_A2_DECISION ") for l in lines):errors.append([name,variant,rep,arm,"adaptive unexpectedly enabled"])
                if status=="ERROR":errors.append([name,variant,rep,arm,"worker"])
                if status=="COMPLETE":
                    counts[arm]+=1
                    rows[arm][rep]=dict(row,outer_s=outer,rss_kib=rss,binary_verdict=verdict)
                else:censored.append([name,variant,rep,arm,status])
                emit("CPR_N5C_TRIAL",case=name,variant=variant,repeat=rep,position=pos,arm=arm,status=status,verdict=verdict if status=="COMPLETE" else None,native=row,outer_s=outer,rss_kib=rss,returncode=r.returncode,stderr=r.stderr[-1000:] if status!="COMPLETE" else "")
        for arm in ARMS:
            rs=list(rows[arm].values())
            emit("CPR_N5C_SUMMARY",case=name,variant=variant,arm=arm,complete=len(rs),attempted=repeats,median_total_s=statistics.median(float(r["total_s"]) for r in rs) if rs else None,median_rss_kib=statistics.median(r["rss_kib"] for r in rs) if rs else None)
        for rep in sorted(set(rows["pre_fix"])&set(rows["fixed"])):
            a,b=rows["pre_fix"][rep],rows["fixed"][rep]
            keys=("vars","clauses","pairs","extracted","twice","proof","solver")
            delta={k:[a.get(k),b.get(k)] for k in keys if a.get(k)!=b.get(k)}
            if delta:
                drifts.append([name,variant,rep,delta])
                emit("CPR_N5C_STRUCTURE_DRIFT",case=name,variant=variant,repeat=rep,delta=delta)
        for before in ("pre_fix","main"):
            after="fixed"
            both=sorted(set(rows[before])&set(rows[after]))
            gained=sorted(set(rows[after])-set(rows[before]))
            missing=sorted(set(rows[before])-set(rows[after]))
            if missing:lost.append([name,variant,before,missing])
            if before=="main" and gained:gains.append([name,variant,gained])
            emit("CPR_N5C_PAIR",case=name,variant=variant,baseline=before,candidate=after,matched=len(both),gained=gained,lost=missing,status="FULL_MATCH" if len(both)==repeats else "INSUFFICIENT_MATCHED_PAIRS")
            if len(both)!=repeats:
                if before=="pre_fix":blocks.append([name,variant,before,"insufficient_pairs"])
                continue
            limits={"total_s":(0.05,0.000025),"rss_kib":(0.05,512)}
            if statistics.median(rows[before][i]["outer_s"] for i in both)>=0.1:limits["outer_s"]=(0.05,0.01)
            else:emit("CPR_N5C_PERF",case=name,variant=variant,baseline=before,metric="outer_s",status="RESOLUTION_LIMITED")
            for metric,(fraction,floor) in limits.items():
                a=[float(rows[before][i][metric]) for i in both]
                b=[float(rows[after][i][metric]) for i in both]
                deltas=[y-x for x,y in zip(a,b)]
                delta=statistics.median(deltas);allowed=max(floor,fraction*statistics.median(a))
                passed=delta<=allowed
                emit("CPR_N5C_PERF",case=name,variant=variant,baseline=before,metric=metric,baseline_median=statistics.median(a),candidate_median=statistics.median(b),paired_delta_median=delta,allowed_delta=allowed,paired_deltas=deltas,status="WITHIN_BUDGET" if passed else "BLOCKED")
                if not passed:blocks.append([name,variant,before,metric,delta,allowed])
    emit("CPR_N5C_NATIVE_GATE",counts=counts,attempted=expected_trials(),errors=errors,perf_blocks=blocks,completion_losses=lost,main_completion_gains=gains,censored=censored,structure_drifts=drifts)
    assert expected_trials()==60 and counts["pre_fix"]==counts["fixed"]==20 and not errors and not blocks and not lost
    # Structural changes are evidence to review, not an automatic PASS or a
    # reason to reject a source-correct legal reduction.

def source_parity():
    from conditional_rr_source_ball import load, controls, dense_overlap, EPS, arb, acb, fmpq, ctx
    from conditional_rr_tensor_source import tensor_trace, controls as tensor_controls
    from fractions import Fraction
    controls();tensor_controls();assert ctx.prec==2048
    receipts=[json.loads(l.split(" ",1)[1]) for l in Path(os.environ["CRR_GENERIC_LOG"]).read_text().splitlines() if l.startswith("CPR_N5C_TRIAL ")]
    assert len(receipts)==expected_trials()
    assert len({(r["case"],r["variant"],r["arm"],r["repeat"]) for r in receipts})==len(receipts)
    completed=[r for r in receipts if r["status"]=="COMPLETE"]
    matched=dict.fromkeys(ARMS,0);counts=dict.fromkeys(ARMS,0);missing=0
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
            emit("CPR_N5C_SOURCE_ADMISSION",case=name,variant=variant,status="UNVERIFIED",reason=str(e));continue
        threshold=(1-EPS*EPS).sqrt()
        verdict="Equivalent" if abs(z).lower()>threshold else "NotEquivalent" if abs(z).upper()<threshold else "INCONCLUSIVE"
        for r in rows:
            ok=r["verdict"]==verdict;delta=None;arm=r["arm"]
            if arm!="main" and r["native"].get("proof")!="rr_exact_projective":
                row=r["native"];k=int(row["twice"])
                def exact(s):
                    q=Fraction(s);return arb(fmpq(q.numerator,q.denominator))
                scale=(arb(2)**(k//2))*(arb(2).sqrt() if k%2 else 1)
                delta=abs(acb(exact(row["real"]),exact(row["imag"]))/scale-z).upper()
                ok=ok and bool(delta<arb("1e-50"))
            counts[arm]+=1;matched[arm]+=int(ok)
            emit("CPR_N5C_SOURCE_PARITY",case=name,variant=variant,arm=arm,repeat=r["repeat"],matched=ok,source_verdict=verdict,count_delta_upper=str(delta) if delta is not None else None,source_sha256=ha,target_sha256=hb,method=method,**meta)
    emit("CPR_N5C_SOURCE_GATE",matched=matched,completed=counts,attempted=len(receipts),unverified=missing)
    assert matched==counts and counts["pre_fix"]==counts["fixed"]==20 and missing==0

if __name__=="__main__":
    if os.environ.get("CRR_GENERIC_LOG"):source_parity()
    else:native()

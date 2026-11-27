"""A1b: fixed first-ket-phase deferral counterfactual, not a runtime policy.
Same RR-first binary, same source/limits and frozen downstream policy.
Two repetitions are exploratory; final admission must re-run full RR-first gate.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import tempfile
from cpr_rr_first import entries, binary_status
from cpr_c3_matched import emit
from cpr_router_acceptance import limit
from conditional_rr_stitch import ROOT

ARMS=("baseline","defer")
KET={("qpeexact_8","random_rotation"),("qwalk-noancilla_5","positive"),
     ("qwalk-noancilla_5","random_rotation"),("grover-noancilla_6","positive")}
def expected_trials():return 44
def native():
    binary=Path(os.environ["CPR_BIN_CPR"]).resolve()
    emit("CPR_A1B_BINARY",sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    complete=0;errors=[];mismatches=[];regressions=[];blocks=[]
    for name,variant,n,source,target in entries():
        paths=[]
        for entry in (source,target):
            p=ROOT/entry["path"];data=p.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            emit("CPR_A1B_SOURCE",case=name,variant=variant,path=entry["path"],sha256=hashlib.sha256(data).hexdigest())
            paths.append(p)
        rows={a:{} for a in ARMS}
        for rep in range(2):
            for arm in (ARMS if rep==0 else ARMS[::-1]):
                env=dict(os.environ,CRR_CASE=name,CRR_VARIANT=variant,CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]),CRR_POLICY="strict",CRR_SCHEDULE="difference",CRR_GENERIC_ARM="conditional_router",CRR_BRA_RESCUE="1",CRR_LIFT_INDEXED="1",CPR_RR_FIRST="1")
                for k in ("CPR_CNF_DIR","CRR_LIFT_CHECKPOINT","CRR_LIFT_POLICY","QUPRS_STAGE_LEDGER","CPR_ADMISSION_PROBE","CPR_MEMORY_DIAGNOSTIC","CPR_A1B_DEFER_FIRST_PHASE"):env.pop(k,None)
                if arm=="defer":env["CPR_A1B_DEFER_FIRST_PHASE"]="1"
                with tempfile.TemporaryDirectory() as tmp:
                    meter=Path(tmp)/"meter"
                    r=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(meter),"timeout","--kill-after=2s","35s",str(binary),"cpr"],cwd=ROOT,env=env,capture_output=True,text=True,preexec_fn=limit)
                    resource=meter.read_text().splitlines()[-1].split() if meter.exists() and meter.read_text().strip() else []
                outer,rss=(float(resource[0]),int(resource[1])) if len(resource)==2 else (None,None)
                lines=[l for l in r.stdout.splitlines() if l.startswith(("CPR_A1B_DEFER ","CPR_A1B_AFTER ","CRR_GENERIC_CALL ","CRR_GENERIC_STOP ","CRR_GENERIC_TRIGGER ","CRR_POLICY_SUMMARY ","CPR_ROUTE "))]
                for l in lines:print(l+" comparison_arm="+arm+" repeat="+str(rep),flush=True)
                calls=[dict(re.findall(r"(\w+)=([^ ]+)",l)) for l in lines if l.startswith("CRR_GENERIC_CALL ")]
                defers=[dict(re.findall(r"(\w+)=([^ ]+)",l)) for l in lines if l.startswith("CPR_A1B_DEFER ")]
                triggers=[dict(re.findall(r"(\w+)=([^ ]+)",l)) for l in lines if l.startswith("CRR_GENERIC_TRIGGER ")]
                row=calls[0] if len(calls)==1 else {}
                verdict=binary_status(row.get("verdict"))
                if r.returncode in (124,137) or "memory allocation" in r.stderr.lower():status="CENSORED"
                elif r.returncode or outer is None or len(calls)>1:status="ERROR"
                elif verdict and row.get("status")=="complete":status="COMPLETE"
                elif row or any(l.startswith("CRR_GENERIC_STOP ") for l in lines):status="INCOMPLETE"
                else:status="ERROR"
                if status=="ERROR":errors.append([name,variant,rep,arm,"worker"])
                if len(defers)!=int(arm=="defer" and (name,variant) in KET):errors.append([name,variant,rep,arm,"defer_coverage"])
                if status=="COMPLETE":
                    complete+=1
                    rows[arm][rep]=dict(row,outer_s=outer,rss_kib=rss,binary_verdict=verdict,deferred=defers,trigger=triggers)
                emit("CPR_A1B_TRIAL",case=name,variant=variant,repeat=rep,arm=arm,status=status,verdict=verdict if status=="COMPLETE" else None,native=row,deferred=defers,trigger=triggers,outer_s=outer,rss_kib=rss,returncode=r.returncode,stderr=r.stderr[-1000:] if status!="COMPLETE" else "")
        if len(rows["baseline"])!=2:errors.append([name,variant,"baseline_incomplete"])
        if len(rows["defer"])!=2:regressions.append([name,variant,"defer_incomplete"])
        for rep in sorted(set(rows["baseline"])&set(rows["defer"])):
            a,b=rows["baseline"][rep],rows["defer"][rep]
            if a["binary_verdict"]!=b["binary_verdict"]:mismatches.append([name,variant,rep])
            if (name,variant) in KET:
                if len(a["trigger"])!=1 or len(b["deferred"])!=1 or a["trigger"][0]["step"]!=b["deferred"][0]["step"]:errors.append([name,variant,rep,"first_trigger_drift"])
                if b["trigger"] and int(b["trigger"][0]["step"])<=int(b["deferred"][0]["step"]):errors.append([name,variant,rep,"nonforward_trigger"])
            else:
                keys=("vars","clauses","pairs","extracted","twice","proof","solver")
                if any(a.get(k)!=b.get(k) for k in keys):errors.append([name,variant,rep,"control_drift"])
            if (name,variant)==("ghz_32","positive") and any(x.get("proof")!="rr_exact_projective" or x.get("solver")!="false" for x in (a,b)):
                errors.append([name,variant,rep,"rr_first_drift"])
        both=sorted(set(rows["baseline"])&set(rows["defer"]))
        if len(both)!=2:continue
        limits={"total_s":(0.05,0.000025),"rss_kib":(0.05,512)}
        if statistics.median(rows["baseline"][i]["outer_s"] for i in both)>=0.1:limits["outer_s"]=(0.05,0.01)
        for metric,(fraction,floor) in limits.items():
            a=[float(rows["baseline"][i][metric]) for i in both]
            b=[float(rows["defer"][i][metric]) for i in both]
            delta=statistics.median(y-x for x,y in zip(a,b));allowed=max(floor,fraction*statistics.median(a))
            passed=delta<=allowed
            emit("CPR_A1B_PERF",case=name,variant=variant,metric=metric,baseline_median=statistics.median(a),defer_median=statistics.median(b),paired_delta_median=delta,allowed_delta=allowed,status="WITHIN_BUDGET" if passed else "BLOCKED")
            if not passed:blocks.append([name,variant,metric,delta,allowed])
    emit("CPR_A1B_NATIVE_GATE",complete=complete,attempted=expected_trials(),errors=errors,mismatches=mismatches,completion_regressions=regressions,perf_blocks=blocks)
    assert complete==expected_trials() and not errors and not mismatches and not regressions and not blocks

def source_parity():
    from conditional_rr_source_ball import load, controls, dense_overlap, EPS, arb, acb, fmpq, ctx
    from conditional_rr_tensor_source import tensor_trace, controls as tensor_controls
    from fractions import Fraction
    controls();tensor_controls();assert ctx.prec==2048
    receipts=[json.loads(l.split(" ",1)[1]) for l in Path(os.environ["CRR_GENERIC_LOG"]).read_text().splitlines() if l.startswith("CPR_A1B_TRIAL ")]
    assert len(receipts)==expected_trials()
    assert len({(r["case"],r["variant"],r["arm"],r["repeat"]) for r in receipts})==len(receipts)
    receipts=[r for r in receipts if r["status"]=="COMPLETE"]
    matched=0; missing=0
    for name,variant,n,source,target in entries():
        rows=[r for r in receipts if r["case"]==name and r["variant"]==variant]
        if not rows:continue
        try:
            a,ha=load(source,n);b,hb=load(target,n)
            try:z,meta=tensor_trace(a,b,n);method="tensor_trace"
            except ValueError:
                if n>8:raise
                z=sum((dense_overlap(a,b,k,n) for k in range(1<<n)),acb(0))/(1<<n);meta={};method="dense"
        except ValueError as e:
            missing+=len(rows)
            emit("CPR_A1B_SOURCE_ADMISSION",case=name,variant=variant,status="UNVERIFIED",reason=str(e))
            continue
        threshold=(1-EPS*EPS).sqrt()
        verdict="Equivalent" if abs(z).lower()>threshold else "NotEquivalent" if abs(z).upper()<threshold else "INCONCLUSIVE"
        for r in rows:
            ok=r["verdict"]==verdict
            delta=None
            if r["arm"]!="main" and r["native"].get("proof")!="rr_exact_projective":
                row=r["native"];k=int(row["twice"])
                def exact(s):
                    q=Fraction(s);return arb(fmpq(q.numerator,q.denominator))
                scale=(arb(2)**(k//2))*(arb(2).sqrt() if k%2 else 1)
                delta=abs(acb(exact(row["real"]),exact(row["imag"]))/scale-z).upper()
                ok=ok and bool(delta<arb("1e-50"))
            matched+=int(ok)
            emit("CPR_A1B_SOURCE_PARITY",case=name,variant=variant,arm=r["arm"],repeat=r["repeat"],matched=ok,source_verdict=verdict,count_delta_upper=str(delta) if delta is not None else None,source_sha256=ha,target_sha256=hb,method=method,**meta)
    emit("CPR_A1B_SOURCE_GATE",matched=matched,completed=len(receipts),unverified=missing)
    assert matched==len(receipts)>0 and missing==0


if __name__=="__main__":
    if os.environ.get("CRR_GENERIC_LOG"):source_parity()
    else:native()

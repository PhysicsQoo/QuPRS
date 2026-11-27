"""A4 fixed holdout, not used in A2/A3 admission design.
No policy edits or tuning. Source oracle limitations and censored rows retained.
Same process bounds and matched non-regression screening as A3.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import tempfile
from cpr_rr_first import binary_status
from cpr_c3_matched import emit
from cpr_router_acceptance import limit
from conditional_rr_stitch import ROOT

ARMS=("main","baseline","adaptive")
# Source-positive blobs from paper corpus; negative blobs locked before trials.
NEGATIVE={
    "qwalk-noancilla_4":"ab5cda304a5ddb76e10a957b87baa343513b1d9e",
    "grover-noancilla_5":"e2f0d392b2e323b6ada4fb211726b186d47a93f1",
    "wstate_8":"04d5e47e1105d13b1198424c6b491e53731b878a",
    "qnn_8":"f7d60e2acea6e550aff6aa3f4dd159fad874760a",
    "qaoa_7":"0479500ecf776aff9b5bc8d4d0434213d1735508",
    "graphstate_16":"efc3ce710b274fd0671e0a36b69296eefe65ac47",
}
def entries():
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    cases={c["id"]:c for c in manifest["cohorts"]["table2_mqt"]["cases"]}
    for name,blob in NEGATIVE.items():
        c=cases[name]
        yield name,"positive",c["qubits"],c["source"],c["transpiled"]
        yield name,"random_rotation",c["qubits"],c["source"],dict(path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,git_blob_sha1=blob)
def arms_for(name,variant):return ARMS
def repetitions(name,variant):return 3
def expected_trials():return 108
def native():
    binaries={a:Path(os.environ["CPR_BIN_MAIN" if a=="main" else "CPR_BIN_CPR"]).resolve() for a in ARMS}
    assert binaries["baseline"]==binaries["adaptive"]
    for arm,binary in binaries.items():
        emit("CPR_A4_BINARY",arm=arm,sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    complete=0;errors=[];mismatches=[];regressions=[];blocks=[];accepted=0;benefits=[];counts={a:0 for a in ARMS};coverage=[];partial_pairs=[];censored=[]
    for name,variant,n,source,target in entries():
        paths=[]
        for entry in (source,target):
            p=ROOT/entry["path"];data=p.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            emit("CPR_A4_SOURCE",case=name,variant=variant,path=entry["path"],sha256=hashlib.sha256(data).hexdigest())
            paths.append(p)
        arms=arms_for(name,variant)
        rows={a:{} for a in arms}
        repeats=repetitions(name,variant)
        for rep in range(repeats):
            shift=rep%len(arms)
            for arm in arms[shift:]+arms[:shift]:
                env=dict(os.environ,CRR_CASE=name,CRR_VARIANT=variant,CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]),CRR_POLICY="strict",CRR_SCHEDULE="difference",CRR_GENERIC_ARM="conditional_router",CRR_BRA_RESCUE="1",CRR_LIFT_INDEXED="1",CPR_RR_FIRST="1")
                for k in ("CPR_CNF_DIR","CRR_LIFT_CHECKPOINT","CRR_LIFT_POLICY","QUPRS_STAGE_LEDGER","CPR_ADMISSION_PROBE","CPR_MEMORY_DIAGNOSTIC","CPR_A2_ADMISSION","CPR_A1B_DEFER_FIRST_PHASE"):env.pop(k,None)
                if arm=="adaptive":env["CPR_A2_ADMISSION"]="1"
                if arm=="main":env.pop("CPR_RR_FIRST",None)
                binary=binaries[arm]
                mode="public" if arm=="main" else "cpr"
                with tempfile.TemporaryDirectory() as tmp:
                    meter=Path(tmp)/"meter"
                    r=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(meter),"timeout","--kill-after=2s","35s",str(binary),mode],cwd=ROOT,env=env,capture_output=True,text=True,preexec_fn=limit)
                    resource=meter.read_text().splitlines()[-1].split() if meter.exists() and meter.read_text().strip() else []
                outer,rss=(float(resource[0]),int(resource[1])) if len(resource)==2 else (None,None)
                lines=[l for l in r.stdout.splitlines() if l.startswith(("CPR_PUBLIC ","CPR_PUBLIC_ERROR ","CPR_A2_DECISION ","CRR_GENERIC_CALL ","CRR_GENERIC_STOP ","CRR_GENERIC_TRIGGER ","CRR_POLICY_SUMMARY ","CPR_ROUTE "))]
                for l in lines:print(l+" comparison_arm="+arm+" repeat="+str(rep),flush=True)
                prefix="CPR_PUBLIC " if arm=="main" else "CRR_GENERIC_CALL "
                calls=[dict(re.findall(r"(\w+)=([^ ]+)",l)) for l in lines if l.startswith(prefix)]
                defers=[dict(re.findall(r"(\w+)=([^ ]+)",l)) for l in lines if l.startswith("CPR_A2_DECISION ")]
                triggers=[dict(re.findall(r"(\w+)=([^ ]+)",l)) for l in lines if l.startswith("CRR_GENERIC_TRIGGER ")]
                row=calls[0] if len(calls)==1 else {}
                verdict=binary_status(row.get("status") if arm=="main" else row.get("verdict"))
                if r.returncode in (124,137) or "memory allocation" in r.stderr.lower():status="CENSORED"
                elif r.returncode or outer is None or len(calls)>1 or any(l.startswith("CPR_PUBLIC_ERROR ") for l in lines):status="ERROR"
                elif verdict and (arm=="main" or row.get("status")=="complete"):status="COMPLETE"
                elif row or any(l.startswith("CRR_GENERIC_STOP ") for l in lines):status="INCOMPLETE"
                else:status="ERROR"
                if status=="ERROR":errors.append([name,variant,rep,arm,"worker"])
                if len(defers)>int(arm=="adaptive"):errors.append([name,variant,rep,arm,"decision_coverage"])
                if status!="COMPLETE":censored.append([name,variant,rep,arm,status])
                for d in defers:
                    if d["decision"]=="defer":
                        accepted+=1
                        if int(d["nodes"])>4096 or int(d["delta"])>0:errors.append([name,variant,rep,arm,"invalid_admission"])
                    elif d["decision"] not in ("growth","work_budget","unsupported"):errors.append([name,variant,rep,arm,"unknown_decision"])
                if status=="COMPLETE":
                    complete+=1;counts[arm]+=1
                    rows[arm][rep]=dict(row,outer_s=outer,rss_kib=rss,binary_verdict=verdict,deferred=defers,trigger=triggers)
                emit("CPR_A4_TRIAL",case=name,variant=variant,repeat=rep,arm=arm,status=status,verdict=verdict if status=="COMPLETE" else None,native=row,deferred=defers,trigger=triggers,outer_s=outer,rss_kib=rss,returncode=r.returncode,stderr=r.stderr[-1000:] if status!="COMPLETE" else "")
        if len({r["binary_verdict"] for arm in arms for r in rows[arm].values()})>1:mismatches.append([name,variant,"cross_arm"])
        if len(rows["adaptive"])!=repeats:coverage.append([name,variant,"adaptive_incomplete"])
        for before,after in [("baseline","adaptive"),("main","adaptive"),("main","baseline")]:
            lost=sorted(set(rows[before])-set(rows[after]))
            if lost:regressions.append([name,variant,before,after,lost])
        for rep in sorted(set(rows["baseline"])&set(rows["adaptive"])):
            a,b=rows["baseline"][rep],rows["adaptive"][rep]
            changed=bool(b["deferred"] and b["deferred"][0]["decision"]=="defer")
            if b["deferred"]:
                if len(a["trigger"])!=1 or a["trigger"][0]["step"]!=b["deferred"][0]["step"]:errors.append([name,variant,rep,"first_trigger_drift"])
                if changed and b["trigger"] and int(b["trigger"][0]["step"])<=int(b["deferred"][0]["step"]):errors.append([name,variant,rep,"nonforward_trigger"])
                if not changed and (not b["trigger"] or a["trigger"][0]["step"]!=b["trigger"][0]["step"]):errors.append([name,variant,rep,"rejected_trigger_drift"])
            if not changed:
                keys=("vars","clauses","pairs","extracted","twice","proof","solver")
                if any(a.get(k)!=b.get(k) for k in keys):errors.append([name,variant,rep,"control_drift"])
                if [x["step"] for x in a["trigger"]]!=[x["step"] for x in b["trigger"]]:errors.append([name,variant,rep,"trigger_drift"])
        for arm in arms:
            rs=rows[arm].values()
            emit("CPR_A4_SUMMARY",case=name,variant=variant,arm=arm,complete=len(rows[arm]),attempted=repeats,median_total_s=statistics.median(float(r["total_s"]) for r in rs) if rs else None,median_rss_kib=statistics.median(r["rss_kib"] for r in rs) if rs else None)
        comparisons=[("baseline","adaptive")]
        if "main" in arms:comparisons.extend([("main","baseline"),("main","adaptive")])
        for before,after in comparisons:
            both=sorted(set(rows[before])&set(rows[after]))
            if len(both)!=repeats:
                partial_pairs.append([name,variant,before,after,len(both)])
                emit("CPR_A4_PAIR",case=name,variant=variant,baseline=before,candidate=after,matched=len(both),status="INSUFFICIENT_MATCHED_PAIRS");continue
            limits={"total_s":(0.05,0.000025),"rss_kib":(0.05,512)}
            if statistics.median(rows[before][i]["outer_s"] for i in both)>=0.1:limits["outer_s"]=(0.05,0.01)
            else:emit("CPR_A4_PERF",case=name,variant=variant,baseline=before,candidate=after,metric="outer_s",status="RESOLUTION_LIMITED")
            for metric,(fraction,floor) in limits.items():
                a=[float(rows[before][i][metric]) for i in both]
                b=[float(rows[after][i][metric]) for i in both]
                deltas=[y-x for x,y in zip(a,b)]
                delta=statistics.median(deltas);allowed=max(floor,fraction*statistics.median(a))
                passed=delta<=allowed
                emit("CPR_A4_PERF",case=name,variant=variant,baseline=before,candidate=after,metric=metric,baseline_median=statistics.median(a),candidate_median=statistics.median(b),paired_delta_median=delta,allowed_delta=allowed,paired_deltas=deltas,status="WITHIN_BUDGET" if passed else "BLOCKED")
                if not passed:blocks.append([name,variant,before,after,metric,delta,allowed])
                # Require actual useful gain on the known admitted coordinates,
                # above the same 5% screening noise margin, not just no regression.
                if before=="baseline" and after=="adaptive" and metric=="total_s" and delta < -allowed and any(r["deferred"] and r["deferred"][0]["decision"]=="defer" for r in rows[after].values()):
                    benefits.append([name,variant,delta,allowed])
    emit("CPR_A4_NATIVE_GATE",complete=complete,attempted=expected_trials(),counts=counts,errors=errors,mismatches=mismatches,completion_regressions=regressions,perf_blocks=blocks,accepted=accepted,benefits=benefits,coverage=coverage,partial_pairs=partial_pairs,censored=censored)
    assert expected_trials()==108 and not errors and not mismatches and not regressions and not blocks and not coverage and accepted>0 and benefits

def source_parity():
    from conditional_rr_source_ball import load, controls, dense_overlap, EPS, arb, acb, fmpq, ctx
    from conditional_rr_tensor_source import tensor_trace, controls as tensor_controls
    from fractions import Fraction
    controls();tensor_controls();assert ctx.prec==2048
    receipts=[json.loads(l.split(" ",1)[1]) for l in Path(os.environ["CRR_GENERIC_LOG"]).read_text().splitlines() if l.startswith("CPR_A4_TRIAL ")]
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
            emit("CPR_A4_SOURCE_ADMISSION",case=name,variant=variant,status="UNVERIFIED",reason=str(e))
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
            emit("CPR_A4_SOURCE_PARITY",case=name,variant=variant,arm=r["arm"],repeat=r["repeat"],matched=ok,source_verdict=verdict,count_delta_upper=str(delta) if delta is not None else None,source_sha256=ha,target_sha256=hb,method=method,**meta)
    emit("CPR_A4_SOURCE_GATE",matched=matched,completed=len(receipts),unverified=missing)
    assert matched==len(receipts)>0 and missing==0


if __name__=="__main__":
    if os.environ.get("CRR_GENERIC_LOG"):source_parity()
    else:native()

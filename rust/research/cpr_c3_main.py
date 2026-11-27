"""C3b: current pinned main vs branch public API vs frozen CPR.
Same host, source bytes, outer limits, strict RR and projective threshold.
Internal timeout allocation and MPFR weight bits intentionally remain native.
No timing claim from censored rows or unsupported source.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import tempfile
from cpr_c3_matched import entries as c3a_entries, emit
from cpr_router_acceptance import limit
from conditional_rr_stitch import ROOT, GENERIC_NEGATIVE

ARMS=["main","branch_public","cpr"]
EXTRA=[("qwalk-noancilla_5","positive"),("qwalk-noancilla_5","random_rotation"),
       ("grover-noancilla_6","positive"),("wstate_16","positive"),("wstate_16","random_rotation")]
def entries():
    yield from c3a_entries()
    cases={c["id"]:c for c in json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())["cohorts"]["table2_mqt"]["cases"]}
    for name,variant in EXTRA:
        c=cases[name]
        target=c["transpiled"] if variant=="positive" else dict(path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,git_blob_sha1=GENERIC_NEGATIVE[name])
        yield name,variant,c["qubits"],c["source"],target
def binary_status(s):
    if s in ("Equivalent","EquivalentUpToGlobalPhase"):return "Equivalent"
    if s=="NotEquivalent":return s
    return None
def native():
    bins={a:Path(os.environ["CPR_BIN_"+a.upper()]).resolve() for a in ARMS}
    for a,p in bins.items():
        assert p.is_file()
        emit("CPR_C3B_BINARY",arm=a,path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    errors=[]; regressions=[]; mismatches=[]; total=0
    for name,variant,n,source,target in entries():
        paths=[]
        for entry in (source,target):
            p=ROOT/entry["path"];data=p.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            emit("CPR_C3B_SOURCE",case=name,variant=variant,path=entry["path"],sha256=hashlib.sha256(data).hexdigest())
            paths.append(p)
        rows={a:{} for a in ARMS}
        for repeat in range(3):
            for pos,arm in enumerate(ARMS[repeat:]+ARMS[:repeat]):
                env=dict(os.environ,CRR_CASE=name,CRR_VARIANT=variant,CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]),CRR_POLICY="strict",CRR_SCHEDULE="difference",CRR_GENERIC_ARM="conditional_router",CRR_BRA_RESCUE="1",CRR_LIFT_INDEXED="1")
                for k in ("CPR_CNF_DIR","CRR_LIFT_CHECKPOINT","CRR_LIFT_POLICY","QUPRS_STAGE_LEDGER"):
                    env.pop(k,None)
                test="conditional_stitch::native_growth_checkpoint" if arm=="cpr" else "cpr_public_hybrid"
                with tempfile.TemporaryDirectory() as tmp:
                    meter=Path(tmp)/"meter"
                    cmd=["/usr/bin/time","-f","%e %M","-o",str(meter),"timeout","--kill-after=2s","35s",str(bins[arm]),test,"--exact","--nocapture"]
                    r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,preexec_fn=limit)
                    resource=meter.read_text().splitlines()[-1].split() if meter.exists() and meter.read_text().strip() else []
                outer,rss=(float(resource[0]),int(resource[1])) if len(resource)==2 else (None,None)
                records=[l for l in r.stdout.splitlines() if l.startswith(("CPR_PUBLIC ","CPR_PUBLIC_ERROR ","CRR_GENERIC_CALL ","CPR_ROUTE ","CRR_GENERIC_STOP ","CRR_POLICY_SUMMARY ","CRR_GENERIC_TRIGGER ","CRR_GENERIC_CONSTRUCT "))]
                for l in records:print(l+" comparison_arm="+arm+" repeat="+str(repeat),flush=True)
                pfx="CRR_GENERIC_CALL " if arm=="cpr" else "CPR_PUBLIC "
                calls=[dict(re.findall(r"(\w+)=([^ ]+)",l)) for l in records if l.startswith(pfx)]
                row=calls[0] if len(calls)==1 else {}
                verdict=binary_status(row.get("verdict") if arm=="cpr" else row.get("status"))
                if r.returncode in (124,137) or "memory allocation" in r.stderr.lower():
                    status="CENSORED"
                elif r.returncode or outer is None or len(calls)>1 or any(l.startswith("CPR_PUBLIC_ERROR ") for l in records):
                    status="ERROR"
                elif verdict and (arm!="cpr" or row.get("status")=="complete"):
                    status="COMPLETE"
                elif row or any(l.startswith("CRR_GENERIC_STOP ") for l in records):
                    status="INCOMPLETE"
                else:status="ERROR"
                if status=="ERROR":errors.append([name,variant,arm,repeat])
                if status=="COMPLETE":
                    rows[arm][repeat]=dict(row,outer_s=outer,rss_kib=rss,binary_verdict=verdict)
                    total+=1
                emit("CPR_C3B_TRIAL",case=name,variant=variant,arm=arm,repeat=repeat,position=pos,status=status,verdict=verdict if status=="COMPLETE" else None,outer_s=outer,rss_kib=rss,native=row,returncode=r.returncode,stderr=r.stderr[-1500:] if status!="COMPLETE" else "")
        all_rows=[r for a in ARMS for r in rows[a].values()]
        if len({r["binary_verdict"] for r in all_rows})>1:mismatches.append([name,variant])
        for a,rs in rows.items():
            emit("CPR_C3B_SUMMARY",case=name,variant=variant,arm=a,complete=len(rs),attempted=3,
                 median_total_s=statistics.median(float(r["total_s"]) for r in rs.values()) if rs else None,
                 median_outer_s=statistics.median(r["outer_s"] for r in rs.values()) if rs else None,
                 median_rss_kib=statistics.median(r["rss_kib"] for r in rs.values()) if rs else None,
                 solver_calls=sum(a=="cpr" or r.get("solver")=="true" for r in rs.values()))
        for a in ("main","branch_public"):
            both=sorted(set(rows[a])&set(rows["cpr"]))
            lost=sorted(set(rows[a])-set(rows["cpr"]))
            gained=sorted(set(rows["cpr"])-set(rows[a]))
            if lost:regressions.append([name,variant,a,lost])
            emit("CPR_C3B_PAIR",case=name,variant=variant,baseline=a,paired=len(both),lost=lost,gained=gained,
                 internal_ratios=[float(rows[a][i]["total_s"])/float(rows["cpr"][i]["total_s"]) for i in both],
                 outer_ratios=[rows[a][i]["outer_s"]/rows["cpr"][i]["outer_s"] if rows["cpr"][i]["outer_s"]>0 else None for i in both])
    emit("CPR_C3B_NATIVE_GATE",complete=total,attempted=len(list(entries()))*9,verdict_mismatches=mismatches,completion_regressions=regressions,errors=errors)
    # Completion loss is a scientific negative result, not an infrastructure failure.
    assert total>0 and not errors and not mismatches

def source_parity():
    from conditional_rr_source_ball import load, controls, dense_overlap, EPS, arb, acb, fmpq, ctx
    from conditional_rr_tensor_source import tensor_trace, controls as tensor_controls
    from fractions import Fraction
    controls();tensor_controls();assert ctx.prec==2048
    receipts=[json.loads(l.split(" ",1)[1]) for l in Path(os.environ["CRR_GENERIC_LOG"]).read_text().splitlines() if l.startswith("CPR_C3B_TRIAL ")]
    assert len(receipts)==len(list(entries()))*9
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
            emit("CPR_C3B_SOURCE_ADMISSION",case=name,variant=variant,status="UNVERIFIED",reason=str(e))
            continue
        threshold=(1-EPS*EPS).sqrt()
        verdict="Equivalent" if abs(z).lower()>threshold else "NotEquivalent" if abs(z).upper()<threshold else "INCONCLUSIVE"
        for r in rows:
            ok=r["verdict"]==verdict
            delta=None
            if r["arm"]=="cpr":
                row=r["native"];k=int(row["twice"])
                def exact(s):
                    q=Fraction(s);return arb(fmpq(q.numerator,q.denominator))
                scale=(arb(2)**(k//2))*(arb(2).sqrt() if k%2 else 1)
                delta=abs(acb(exact(row["real"]),exact(row["imag"]))/scale-z).upper()
                ok=ok and bool(delta<arb("1e-50"))
            matched+=int(ok)
            emit("CPR_C3B_SOURCE_PARITY",case=name,variant=variant,arm=r["arm"],repeat=r["repeat"],matched=ok,source_verdict=verdict,count_delta_upper=str(delta) if delta is not None else None,source_sha256=ha,target_sha256=hb,method=method,**meta)
    emit("CPR_C3B_SOURCE_GATE",matched=matched,completed=len(receipts),unverified=missing)
    assert matched==len(receipts)>0 and missing==0

if __name__=="__main__":
    if os.environ.get("CRR_GENERIC_LOG"):source_parity()
    else:native()

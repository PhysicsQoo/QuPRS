"""C3a frozen C2 native matched cohort: two counterbalanced orders.
This is the bounded research harness, not a production RR-first API or TACAS timing.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import tempfile
from decimal import Decimal, localcontext
from cpr_router_acceptance import norm, limit
from conditional_rr_stitch import ROOT

NEGATIVE = {
    "ghz_32": "157012b31ad13fa7197b5f393f0abd6aef2402f2",
    "qpeexact_8": "01078415cf504c48fa770c5eea3fa9ccdd22fecd",
    "vqe_4": "21776de4a2b0168f208d7dfba62ee198301a8357",
}
SCOPE = [(case, variant) for case in NEGATIVE for variant in ("positive", "random_rotation")]
ARMS = ["original", "conditional_scan", "conditional_raw", "conditional", "conditional_router"]

def entries():
    cases = {c["id"]: c for c in json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())["cohorts"]["table2_mqt"]["cases"]}
    for name, variant in SCOPE:
        c = cases[name]
        target = c["transpiled"] if variant == "positive" else dict(
            path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,
            git_blob_sha1=NEGATIVE[name])
        yield name, variant, c["qubits"], c["source"], target

def emit(tag, **row):
    print(tag+" "+json.dumps(row), flush=True)

def native():
    failures = []
    regressions = []
    mismatches = 0
    count = 0
    for name, variant, n, source, target in entries():
        paths = []
        for entry in (source, target):
            p = ROOT/entry["path"]
            data = p.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest() == entry["git_blob_sha1"]
            emit("CPR_C3_SOURCE", case=name, variant=variant, path=entry["path"], sha256=hashlib.sha256(data).hexdigest(), blob=entry["git_blob_sha1"])
            paths.append(p)
        rows = {a: {} for a in ARMS}
        for repeat, order in enumerate((ARMS, ARMS[::-1])):
            for pos, arm in enumerate(order):
                env = dict(os.environ, CRR_CASE=name, CRR_VARIANT=variant, CRR_SOURCE=str(paths[0]), CRR_TARGET=str(paths[1]), CRR_POLICY="strict", CRR_SCHEDULE="difference", CRR_GENERIC_ARM=arm, CRR_BRA_RESCUE="1")
                for k in ("CRR_LIFT_INDEXED", "CPR_CNF_DIR", "CRR_LIFT_CHECKPOINT", "CRR_LIFT_POLICY"):
                    env.pop(k, None)
                if arm != "conditional_scan":
                    env["CRR_LIFT_INDEXED"] = "1"
                cmd = ["timeout", "--kill-after=2s", "35s", "cargo", "test", "--release", "--locked", "--manifest-path", "rust/Cargo.toml", "-p", "quprs", "--test", "conditional_rr_experiment", "conditional_stitch::native_growth_checkpoint", "--", "--exact", "--nocapture"]
                with tempfile.TemporaryDirectory() as tmp:
                    meter = Path(tmp)/"meter"
                    r = subprocess.run(["/usr/bin/time", "-f", "%e %M", "-o", str(meter), *cmd], cwd=ROOT, env=env, capture_output=True, text=True, preexec_fn=limit)
                    resource = meter.read_text().splitlines()[-1].split() if meter.exists() and meter.read_text().strip() else []
                resource_ok = len(resource)==2
                outer, rss = (float(resource[0]), int(resource[1])) if resource_ok else (None, None)
                records = [l for l in r.stdout.splitlines() if l.startswith(("CRR_GENERIC_CALL ", "CPR_ROUTE ", "CRR_GENERIC_STOP ", "CRR_POLICY_SUMMARY ", "CRR_GENERIC_CONSTRUCT ", "CRR_GENERIC_TRIGGER "))]
                for line in records:
                    print(line+" repeat="+str(repeat), flush=True)
                complete = [dict(re.findall(r"(\w+)=([^ ]+)", l)) for l in records if l.startswith("CRR_GENERIC_CALL ") and "status=complete" in l]
                if r.returncode in (124, 137) or "memory allocation" in r.stderr.lower():
                    status = "CENSORED"
                elif r.returncode or len(complete)>1 or not resource_ok:
                    status = "ERROR"
                    failures.append([name, variant, arm, repeat])
                elif len(complete)==1:
                    status = "COMPLETE"
                    rows[arm][repeat] = dict(complete[0], outer_s=outer, rss_kib=rss)
                    count += 1
                elif any(l.startswith("CRR_GENERIC_STOP ") or "status=incomplete" in l for l in records):
                    status = "INCOMPLETE"
                else:
                    status = "ERROR"
                    failures.append([name, variant, arm, repeat])
                emit("CPR_C3_TRIAL", case=name, variant=variant, arm=arm, repeat=repeat, position=pos, status=status, returncode=r.returncode, outer_s=outer, rss_kib=rss, stderr=r.stderr[-1800:] if status!="COMPLETE" else "")
        all_rows = [r for v in rows.values() for r in v.values()]
        if all_rows:
            with localcontext() as ctx:
                ctx.prec=150
                ref=all_rows[0]
                for row in all_rows[1:]:
                    if sum(abs(norm(ref,k)-norm(row,k)) for k in ("real","imag"))>=Decimal("1e-50") or row["verdict"]!=ref["verdict"]:
                        mismatches += 1
        for arm, data in rows.items():
            summary={k:statistics.median(float(r[k]) for r in data.values()) if data else None for k in ("construct_s","prepare_s","solve_s","total_s","outer_s","rss_kib")}
            emit("CPR_C3_SUMMARY", case=name, variant=variant, arm=arm, complete=len(data), attempted=2, medians=summary)
        for baseline in ARMS[:-1]:
            # Completion and paired time are separate. No censored speedup.
            common=sorted(set(rows[baseline]) & set(rows["conditional_router"]))
            lost=sorted(set(rows[baseline])-set(rows["conditional_router"]))
            if lost:
                regressions.append([name,variant,baseline,lost])
            ratios=[float(rows[baseline][i]["total_s"])/float(rows["conditional_router"][i]["total_s"]) for i in common]
            outer_ratios=[float(rows[baseline][i]["outer_s"])/float(rows["conditional_router"][i]["outer_s"]) for i in common]
            emit("CPR_C3_PAIR", case=name, variant=variant, baseline=baseline, paired=len(common), lost=lost, internal_ratios=ratios, outer_ratios=outer_ratios)
    emit("CPR_C3_NATIVE_GATE", complete=count, attempted=len(SCOPE)*len(ARMS)*2, count_mismatches=mismatches, completion_regressions=regressions, errors=failures)
    assert count>0 and not (mismatches or regressions or failures)

def source_parity():
    from conditional_rr_source_ball import load, controls, dense_overlap, EPS, arb, acb, fmpq, ctx
    from conditional_rr_tensor_source import tensor_trace, controls as tensor_controls
    from fractions import Fraction
    controls()
    tensor_controls()
    assert ctx.prec==2048
    log=Path(os.environ["CRR_GENERIC_LOG"]).read_text().splitlines()
    receipts=[dict(re.findall(r"(\w+)=([^ ]+)",l)) for l in log if l.startswith("CRR_GENERIC_CALL ") and "status=complete" in l]
    matched=0
    missing=0
    for name, variant, n, source, target in entries():
        rows=[r for r in receipts if r["case"]==name and r["variant"]==variant]
        if not rows:
            emit("CPR_C3_SOURCE_ADMISSION",case=name,variant=variant,status="NO_COMPLETED_NATIVE")
            continue
        try:
            a,ha=load(source,n)
            b,hb=load(target,n)
            try:
                z,meta=tensor_trace(a,b,n)
                method="tensor_trace"
            except ValueError:
                if n>8:
                    raise
                z=sum((dense_overlap(a,b,k,n) for k in range(1<<n)),acb(0))/(1<<n)
                meta={}
                method="dense"
        except ValueError as e:
            missing+=len(rows)
            emit("CPR_C3_SOURCE_ADMISSION",case=name,variant=variant,status="UNVERIFIED",reason=str(e))
            continue
        threshold=(1-EPS*EPS).sqrt()
        verdict="Equivalent" if abs(z).lower()>threshold else "NotEquivalent" if abs(z).upper()<threshold else "INCONCLUSIVE"
        def exact(s):
            q=Fraction(s)
            return arb(fmpq(q.numerator,q.denominator))
        for row in rows:
            k=int(row["twice"])
            scale=(arb(2)**(k//2))*(arb(2).sqrt() if k%2 else 1)
            observed=acb(exact(row["real"]),exact(row["imag"]))/scale
            delta=abs(observed-z).upper()
            ok=bool(delta<arb("1e-50") and verdict==row["verdict"])
            matched+=int(ok)
            emit("CPR_C3_SOURCE_PARITY",case=name,variant=variant,arm=row["arm"],repeat=row["repeat"],matched=ok,source_verdict=verdict,delta=str(delta),source_sha256=ha,target_sha256=hb,method=method,**meta)
    emit("CPR_C3_SOURCE_GATE",matched=matched,completed=len(receipts),unverified=missing)
    assert matched==len(receipts)>0 and missing==0

if __name__=="__main__":
    if os.environ.get("CRR_GENERIC_LOG"):
        source_parity()
    else:
        native()

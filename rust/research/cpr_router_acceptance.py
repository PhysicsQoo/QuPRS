"""Frozen C2 router pilot: no case-name decisions in the native policy.
Calibration coordinates and holdout coordinates are reported separately.
One solver call per arm; matched resource limits and independent source oracle.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import statistics
import subprocess
from decimal import Decimal, localcontext
from fractions import Fraction
from conditional_rr_stitch import ROOT, GENERIC_NEGATIVE

SCOPE=[("qwalk-noancilla_5","positive","calibration"),
       ("grover-noancilla_6","positive","calibration"),
       ("wstate_16","positive","holdout"),
       ("wstate_16","random_rotation","holdout"),
       ("qnn_4","positive","no_lift_control")]
ARMS=["conditional_raw","conditional","conditional_router"]
def norm(r,k):
    q=Fraction(r[k])
    with localcontext() as ctx:
        ctx.prec=150
        n=int(r["twice"])
        return Decimal(q.numerator)/Decimal(q.denominator)/(Decimal(2)**(n//2)*(Decimal(2).sqrt() if n%2 else 1))
def limit():
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
def main():
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    cases={c["id"]:c for c in manifest["cohorts"]["table2_mqt"]["cases"]}
    mismatches=0
    regressions=[]
    expected=0
    for name,variant,group in SCOPE:
        c=cases[name]
        target=c["transpiled"] if variant=="positive" else dict(path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,git_blob_sha1=GENERIC_NEGATIVE[name])
        paths=[]
        for entry in (c["source"],target):
            p=ROOT/entry["path"]; data=p.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            print("CPR_ROUTER_SOURCE",name,variant,entry["path"],hashlib.sha256(data).hexdigest(),flush=True)
            paths.append(p)
        rows={a:[] for a in ARMS}
        # Balanced order; new router is the reason to repeat these matched arms.
        for repeat in range(3):
            for arm in ARMS[repeat:]+ARMS[:repeat]:
                env=dict(os.environ,CRR_CASE=name,CRR_VARIANT=variant,CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]),CRR_POLICY="strict",CRR_SCHEDULE="difference",CRR_GENERIC_ARM=arm,CRR_LIFT_INDEXED="1",CRR_BRA_RESCUE="1")
                env.pop("CPR_CNF_DIR",None)
                cmd=["/usr/bin/time","-f","CPR_RESOURCE elapsed_s=%e max_rss_kib=%M","timeout","--kill-after=2s","35s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_stitch::native_growth_checkpoint","--","--exact","--nocapture"]
                r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,preexec_fn=limit)
                print("CPR_RUN",name,variant,group,arm,repeat,r.returncode,flush=True)
                for l in r.stderr.splitlines():
                    if l.startswith("CPR_RESOURCE "):print(l,flush=True)
                for l in r.stdout.splitlines():
                    if l.startswith(("CRR_GENERIC_CALL ","CPR_ROUTE ","CRR_GENERIC_STOP ","CRR_POLICY_SUMMARY ","CRR_GENERIC_CONSTRUCT ")):
                        print(l+" repeat="+str(repeat),flush=True)
                if r.returncode in (124,137) or "memory allocation" in r.stderr.lower():continue
                assert r.returncode==0,r.stderr[-4000:]
                got=[dict(re.findall(r"(\w+)=([^ ]+)",l)) for l in r.stdout.splitlines() if l.startswith("CRR_GENERIC_CALL ") and "status=complete" in l]
                if got:
                    assert len(got)==1
                    rows[arm].append(got[0]);expected+=1
        all_rows=[r for v in rows.values() for r in v]
        if all_rows:
            ref=all_rows[0]
            with localcontext() as ctx:
                ctx.prec=150
                for r in all_rows[1:]:
                    if sum(abs(norm(ref,k)-norm(r,k)) for k in ("real","imag"))>=Decimal("1e-50") or r["verdict"]!=ref["verdict"]:mismatches+=1
        if len(rows["conditional_router"])<max(len(rows[a]) for a in ARMS[:2]):regressions.append([name,variant])
        for arm,v in rows.items():
            ts=[float(r["total_s"]) for r in v]
            print("CPR_ROUTER_SUMMARY "+json.dumps(dict(case=name,variant=variant,group=group,arm=arm,complete=len(v),attempted=3,median_s=statistics.median(ts) if ts else None)),flush=True)
    print("CPR_ROUTER_GATE "+json.dumps(dict(count_mismatches=mismatches,completion_regressions=regressions,completed=expected)),flush=True)
    assert mismatches==0 and not regressions
    assert expected>0
if __name__=="__main__":main()

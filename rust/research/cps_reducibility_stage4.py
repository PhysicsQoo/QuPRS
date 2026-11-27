#!/usr/bin/env python3
"""Stage 4: preserve existing structural fast path and support-index fallback.
No new solver, no new RR, no default CPS changes. Paired regression pilot."""
import hashlib
import json
import os
import pathlib
import sys
from cps_reducibility_pilot import run
from autoq_c3_pilot import CASES

COHORT=("mogrover03","mogrover04","mogrover03-relative","grover04",
        "bv03","ghz3-broken","ghz8","ghz3-plus")
MODES=("raw-factor","hybrid-support","orbit-wmc","orbit-factor")

def main():
    eq,c3,solver,out=map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:5])
    out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,QUPRS_GPMC_PATH=str(solver),AQ_CPS_FUSED="0",AQ_CPS_RR_TRACE="1")
    env.pop("AQ_CPS_ORBIT_BAD",None)
    rows=[];errors=[]
    worker=pathlib.Path(__file__).resolve().with_name("autoq_c3_pilot.py")
    def arm(period,case,mode,bad=False):
        folder=out/f"{period}-{case}-{mode}{'-bad-cert' if bad else ''}"
        e=dict(env,AQ_CPS_ORBIT_BAD="1") if bad else env
        p,row=run([sys.executable,str(worker),"--arm",str(c3),str(solver),case,mode,str(folder)],folder,e)
        row.update(period=period,case=case,mode=mode,bad_certificate=bad)
        if p.returncode in (124,137):row["status"]="TIMEOUT"
        elif p.returncode:row["status"]="ERROR";errors.append(str(folder))
        else:
            try:
                row["native"]=json.loads(p.stdout);row["status"]=row["native"]["verdict"]
                assert row["status"] in ("UNKNOWN",CASES[case])
            except (ValueError,AssertionError,KeyError):
                row["status"]="ERROR";errors.append(str(folder))
        log=folder/"native.log"
        lines=log.read_text().splitlines() if log.exists() else []
        for key,marker in (("stages","AQ_CPS_STAGE "),("steps","AQ_CPS_RR_STEP "),
            ("residual","AQ_CPS_RESIDUAL "),("encoding","AQ_CPS_ENCODING "),
            ("certificates","AQ_CPS_ORBIT_CERT "),("orbit","AQ_CPS_ORBIT_ROUTE ")):
            row[key]=[l.split(marker,1)[1] for l in lines if marker in l]
        if bad and any("admitted=true" in x for x in row["orbit"]):
            errors.append("wrong EQ certificate admitted "+str(folder))
        rows.append(row);print("CPS_STAGE4_ARM "+json.dumps(row),flush=True)
    for period in range(2):
        for case in (COHORT if period==0 else COHORT[::-1]):
            for mode in (MODES if period==0 else MODES[::-1]):
                arm(period,case,mode)
        arm(period,"mogrover03","orbit-wmc",True)
        arm(period,"mogrover03","orbit-factor",True)
    summary=dict(rows=rows,errors=errors,sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (eq,c3,solver)})
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("CPS_STAGE4_SUMMARY "+json.dumps(dict(arms=len(rows),errors=errors)),flush=True)
    # Validate the fallback contract, not just expected verdicts.
    for period in range(2):
        for case in ("ghz8","ghz3-plus"):
            a,b=[next(r for r in rows if r["period"]==period and r["case"]==case and r["mode"]==m and not r["bad_certificate"]) for m in ("raw-factor","orbit-factor")]
            for r in (a,b):
                if r["status"]!=CASES[case] or r.get("native",{}).get("native",{}).get("route")!="symbolic" or r.get("native",{}).get("queries")!=0:
                    errors.append("existing symbolic fast path lost "+str((period,case,r["mode"])))
        for mode in ("orbit-wmc","orbit-factor"):
            r=next(r for r in rows if r["period"]==period and r["case"]=="mogrover03" and r["mode"]==mode and r["bad_certificate"])
            if r["status"]!="PROVED" or not any("admitted=false original=8 representatives=8" in x for x in r["orbit"]):
                errors.append("bad certificate did not retain full fallback "+str((period,mode)))
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("CPS_STAGE4_ACCEPTANCE "+json.dumps(dict(errors=errors)),flush=True)
    assert len(rows)==68 and not errors,errors

if __name__=="__main__":main()

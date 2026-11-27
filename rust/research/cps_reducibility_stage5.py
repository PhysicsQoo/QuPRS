#!/usr/bin/env python3
"""Stage 5: opt-in transactional cost gate for original RR.
Compare against unchanged orbit/raw factor and original hybrid support."""
import hashlib
import json
import os
import pathlib
import sys
from cps_reducibility_pilot import run
from autoq_c3_pilot import CASES

COHORT=("mogrover03","mogrover04","mogrover03-relative","grover04",
        "bv03","ghz3-broken","ghz8","ghz3-plus","ghz5","grover03-relative")
MODES=("raw-factor","hybrid-support","orbit-factor","bounded-orbit-factor")

def main():
    eq,c3,solver,out=map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:5])
    out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,QUPRS_GPMC_PATH=str(solver),AQ_CPS_FUSED="0",AQ_CPS_RR_TRACE="1")
    env.pop("AQ_CPS_ORBIT_BAD",None)
    env.pop("AQ_CPS_RR_POLICY",None)
    rows=[];errors=[]
    worker=pathlib.Path(__file__).resolve().with_name("autoq_c3_pilot.py")
    def arm(period,case,mode,bad=False):
        folder=out/f"{period}-{case}-{mode}{'-bad-cert' if bad else ''}"
        e=dict(env)
        if bad:e["AQ_CPS_ORBIT_BAD"]="1"
        native_mode=mode
        if mode=="bounded-orbit-factor":
            e["AQ_CPS_RR_POLICY"]="bounded"
            native_mode="orbit-factor"
        p,row=run([sys.executable,str(worker),"--arm",str(c3),str(solver),case,native_mode,str(folder)],folder,e)
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
            ("certificates","AQ_CPS_ORBIT_CERT "),("orbit","AQ_CPS_ORBIT_ROUTE "),
            ("policy","AQ_CPS_POLICY "),("policy_steps","AQ_CPS_POLICY_STEP ")):
            row[key]=[l.split(marker,1)[1] for l in lines if marker in l]
        if bad and any("admitted=true" in x for x in row["orbit"]):
            errors.append("wrong EQ certificate admitted "+str(folder))
        rows.append(row);print("CPS_STAGE5_ARM "+json.dumps(row),flush=True)
    for period in range(2):
        for case in (COHORT if period==0 else COHORT[::-1]):
            for mode in (MODES if period==0 else MODES[::-1]):
                arm(period,case,mode)
        arm(period,"mogrover03","bounded-orbit-factor",True)
    summary=dict(rows=rows,errors=errors,sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (eq,c3,solver)})
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("CPS_STAGE5_SUMMARY "+json.dumps(dict(arms=len(rows),errors=errors)),flush=True)
    # Validate the fallback contract, not just expected verdicts.
    for period in range(2):
        for case in ("ghz5","ghz8","ghz3-plus"):
            a,b=[next(r for r in rows if r["period"]==period and r["case"]==case and r["mode"]==m and not r["bad_certificate"]) for m in ("raw-factor","bounded-orbit-factor")]
            for r in (a,b):
                if r["status"]!=CASES[case] or r.get("native",{}).get("native",{}).get("route")!="symbolic" or r.get("native",{}).get("queries")!=0:
                    errors.append("existing symbolic fast path lost "+str((period,case,r["mode"])))
        for mode in ("bounded-orbit-factor",):
            r=next(r for r in rows if r["period"]==period and r["case"]=="mogrover03" and r["mode"]==mode and r["bad_certificate"])
            if r["status"]!="PROVED" or not any("admitted=false original=8 representatives=8" in x for x in r["orbit"]):
                errors.append("bad certificate did not retain full fallback "+str((period,mode)))
    for r in rows:
        if r["mode"]!="bounded-orbit-factor":continue
        if r["status"]!=CASES[r["case"]] or not r["policy"]:
            errors.append("bounded route not definite/diagnosed "+str((r["case"],r["period"],r["bad_certificate"])))
        for line in r["policy_steps"]:
            fields=dict(t.split("=",1) for t in line.split())
            if fields["commit"]=="true" and not (int(fields["h_after"])<int(fields["h_before"]) and int(fields["terms_after"])<=int(fields["terms_before"]) and int(fields["incidence_after"])<=int(fields["incidence_before"])):
                errors.append("growth gate violated "+line)
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("CPS_STAGE5_ACCEPTANCE "+json.dumps(dict(errors=errors)),flush=True)
    assert len(rows)==82 and not errors,errors

if __name__=="__main__":main()

#!/usr/bin/env python3
"""Stage-2 diagnostic: existing sign-factor on raw vs RR residual, not a new solver."""
import hashlib
import json
import os
import pathlib
import sys
from cps_reducibility_pilot import run, CASES_PILOT
from autoq_c3_pilot import CASES

MODES=("wmc","raw-factor","structural-factor")

def main():
    eq,c3,solver,out=map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:5])
    out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,QUPRS_GPMC_PATH=str(solver),AQ_CPS_FUSED="0",AQ_CPS_RR_TRACE="1")
    rows=[];errors=[]
    for size,w in (("03",3),("04",4),("05",5)):
        for j in range(w):
            for variant in (("source","wrong-output") if j==0 else ("source",)):
                folder=out/f"eq-{size}-{j}-{variant}"
                p,row=run([str(eq),"--exact","original_eq_covariance_arm","--ignored","--nocapture"],
                    folder,dict(env,CPS_ORBIT_SIZE=size,CPS_ORBIT_GEN=str(j),
                    CPS_ORBIT_VARIANT=variant,CPS_ORBIT_MODE="rr",CPS_ORBIT_SECONDS="3"))
                lines=[l.split("CPS_ORBIT_RESULT ",1)[1] for l in p.stdout.splitlines() if "CPS_ORBIT_RESULT " in l]
                row.update(kind="eq",size=size,generator=j,variant=variant,result=lines[-1] if lines else None)
                row["status"]="TIMEOUT" if p.returncode in (124,137) else "ERROR" if p.returncode or not lines else lines[-1].split()[0].split("=",1)[1]
                if row["status"]=="ERROR":errors.append(str(folder))
                rows.append(row);print("CPS_STAGE2_ARM "+json.dumps(row),flush=True)
    worker=pathlib.Path(__file__).resolve().with_name("autoq_c3_pilot.py")
    for period in range(2):
        for case in (CASES_PILOT if period==0 else CASES_PILOT[::-1]):
            for mode in (MODES if period==0 else MODES[::-1]):
                folder=out/f"{period}-{case}-{mode}"
                p,row=run([sys.executable,str(worker),"--arm",str(c3),str(solver),case,mode,str(folder)],folder,env)
                row.update(kind="c3",period=period,case=case,mode=mode)
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
                row["stages"]=[l.split("AQ_CPS_STAGE ",1)[1] for l in lines if "AQ_CPS_STAGE " in l]
                row["steps"]=[l.split("AQ_CPS_RR_STEP ",1)[1] for l in lines if "AQ_CPS_RR_STEP " in l]
                row["residual"]=[l.split("AQ_CPS_RESIDUAL ",1)[1] for l in lines if "AQ_CPS_RESIDUAL " in l]
                row["encoding"]=[l.split("AQ_CPS_ENCODING ",1)[1] for l in lines if "AQ_CPS_ENCODING " in l]
                rows.append(row);print("CPS_STAGE2_ARM "+json.dumps(row),flush=True)
    summary=dict(rows=rows,errors=errors,sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (eq,c3,solver)})
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("CPS_STAGE2_SUMMARY "+json.dumps(dict(arms=len(rows),errors=errors)),flush=True)
    assert len(rows)==51 and not errors,errors

if __name__=="__main__":main()

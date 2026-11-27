"""A1: isolated first-trigger cost, no solver and no policy tuning.
Diagnostic worker uses the existing strict Difference prefix. Each arm is
externally bounded (15s/3GiB); intermediate allocation is not proven bounded
by a term counter. Observe post-gate canonical size before RR admission.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile
from cpr_rr_first import entries
from cpr_c3_matched import emit
from cpr_router_acceptance import limit
from conditional_rr_stitch import ROOT

ARMS=("native","lifted","inverse")
# Evidence classes validate the existing trigger behavior only; no runtime
# dispatch by family or known outcome.
TRIGGERED={("qpeexact_8","random_rotation"),("qwalk-noancilla_5","positive"),
           ("qwalk-noancilla_5","random_rotation"),("grover-noancilla_6","positive"),
           ("wstate_16","positive"),("wstate_16","random_rotation")}

def main():
    binary=Path(os.environ["CPR_BIN_CPR"]).resolve()
    emit("CPR_A1_BINARY",sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    errors=[];censored=[];roundtrips=0;unverified=[];no_trigger=0;attempted=0
    for name,variant,n,source,target in entries():
        paths=[]
        for entry in (source,target):
            p=ROOT/entry["path"];data=p.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            emit("CPR_A1_SOURCE",case=name,variant=variant,path=entry["path"],sha256=hashlib.sha256(data).hexdigest())
            paths.append(p)
        # Two repetitions, reverse arm order to expose gross nondeterminism.
        for rep in range(2):
            rows={}
            for arm in (ARMS if rep==0 else ARMS[::-1]):
                attempted+=1
                env=dict(os.environ,CPR_ADMISSION_PROBE=arm,CRR_CASE=name,CRR_VARIANT=variant,CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]),CRR_POLICY="strict",CRR_SCHEDULE="difference",CRR_GENERIC_ARM="conditional_router",CRR_LIFT_INDEXED="1",CRR_BRA_RESCUE="1")
                for key in ("CPR_CNF_DIR","CRR_LIFT_CHECKPOINT","CRR_LIFT_POLICY","QUPRS_STAGE_LEDGER","CPR_RR_FIRST","CPR_MEMORY_DIAGNOSTIC"):
                    env.pop(key,None)
                with tempfile.TemporaryDirectory() as tmp:
                    meter=Path(tmp)/"meter"
                    r=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(meter),"timeout","--kill-after=1s","15s",str(binary),"cpr"],cwd=ROOT,env=env,capture_output=True,text=True,preexec_fn=limit)
                    resource=meter.read_text().splitlines()[-1].split() if meter.exists() and meter.read_text().strip() else []
                rec={}
                for line in r.stdout.splitlines():
                    if line.startswith("CPR_A1_"):
                        key=line.split()[0].removeprefix("CPR_A1_")
                        assert key not in rec,(key,rec)
                        rec[key]=dict(re.findall(r"(\w+)=([^ ]+)",line))
                if r.returncode in (124,137) or "memory allocation" in r.stderr.lower():
                    status="CENSORED";censored.append([name,variant,rep,arm])
                elif r.returncode or len(resource)!=2 or not rec or "CRR_GENERIC_CALL " in r.stdout or "CPR_PUBLIC " in r.stdout:
                    status="ERROR";errors.append([name,variant,rep,arm])
                elif "NO_TRIGGER" in rec:status="NO_TRIGGER"
                elif "STOP" in rec:status="STOP"
                elif (arm=="inverse" and "INVERSE" in rec) or (arm!="inverse" and "RR" in rec):status="COMPLETE"
                else:status="ERROR";errors.append([name,variant,rep,arm])
                rows[arm]=rec
                emit("CPR_A1_TRIAL",case=name,variant=variant,repeat=rep,arm=arm,status=status,returncode=r.returncode,outer_s=float(resource[0]) if len(resource)==2 else None,rss_kib=int(resource[1]) if len(resource)==2 else None,records=rec,stderr=r.stderr[-1000:] if status in ("ERROR","CENSORED") else "")
            key=(name,variant)
            if key not in TRIGGERED:
                if all("NO_TRIGGER" in x for x in rows.values()) and len({x["NO_TRIGGER"]["state_sha"] for x in rows.values()})==1:
                    no_trigger+=1
                else:errors.append([name,variant,rep,"no_trigger_control"])
                continue
            checkpoints=[x["CHECKPOINT"] for x in rows.values() if "CHECKPOINT" in x]
            if len(checkpoints)!=3:
                unverified.append([name,variant,rep,"checkpoint_missing"])
                continue
            invariant=("step","index","kind","q","s","d","work","p_inc","f_inc","bra_bound","terms","phase","incidence","live","state_sha")
            if any(len({x[k] for x in checkpoints})!=1 for k in invariant):
                errors.append([name,variant,rep,"checkpoint_drift"]);continue
            a,b,c=(rows[x] for x in ARMS)
            if "RAW" in b and "RAW" in c and b["RAW"]["state_sha"]!=c["RAW"]["state_sha"]:
                errors.append([name,variant,rep,"lifted_raw_drift"])
            if "RAW" not in a or "RAW" not in b or "INVERSE" not in c:
                unverified.append([name,variant,rep,"roundtrip_missing"]);continue
            raw=a["RAW"];lift=b["RAW"];inverse=c["INVERSE"]
            ok=(inverse["hh"]=="true" and inverse["removed_pair"]=="true" and inverse["state_sha"]==raw["state_sha"]
                and int(lift["live"])==int(raw["live"])+2 and inverse["live"]==raw["live"])
            if ok:roundtrips+=1
            else:errors.append([name,variant,rep,"inverse_roundtrip"])
            emit("CPR_A1_PAIR",case=name,variant=variant,repeat=rep,checkpoint=checkpoints[0],native_raw=raw,lifted_raw=lift,native_rr=a.get("RR"),lifted_rr=b.get("RR"),inverse_ok=ok)
    emit("CPR_A1_GATE",attempted=attempted,expected=66,no_trigger=no_trigger,expected_no_trigger=10,roundtrips=roundtrips,expected_roundtrips=12,censored=censored,unverified=unverified,errors=errors)
    # Missing proof is scientifically inconclusive, not a positive result.
    assert attempted==66 and no_trigger==10 and not errors and not unverified and roundtrips==12

if __name__=="__main__":main()

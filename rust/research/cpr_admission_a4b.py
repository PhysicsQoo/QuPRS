"""A4b census: coverage only, never evaluate A2 acceptance or WMC."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from cpr_c3_matched import emit
from cpr_router_acceptance import limit
from conditional_rr_stitch import ROOT

def main():
    m=json.loads(Path(__file__).with_name("cpr_admission_a4b_manifest.json").read_text())
    assert len(m["entries"])==43 and len(m["excluded"])==6
    binary=Path(os.environ["CPR_BIN_CPR"]).resolve()
    emit("CPR_A4B_BINARY",sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    counts={};errors=[];eligible=[]
    for e in m["excluded"]:emit("CPR_A4B_EXCLUDED",case=e["case"],variant=e["variant"],reason="source_oracle_wire_cap")
    for e in m["entries"]:
        name,variant,n=e["case"],e["variant"],e["n"]
        paths=[]
        for entry in (e["source"],e["target"]):
            path=ROOT/entry["path"];data=path.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            emit("CPR_A4B_SOURCE",case=name,variant=variant,path=entry["path"],sha256=hashlib.sha256(data).hexdigest())
            paths.append(path)
        env=dict(os.environ,CPR_ADMISSION_PROBE="coverage",CRR_CASE=name,CRR_VARIANT=variant,CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]),CRR_POLICY="strict",CRR_SCHEDULE="difference",CRR_GENERIC_ARM="conditional_router",CRR_LIFT_INDEXED="1",CRR_BRA_RESCUE="1")
        for k in ("CPR_CNF_DIR","CRR_LIFT_CHECKPOINT","CRR_LIFT_POLICY","QUPRS_STAGE_LEDGER","CPR_RR_FIRST","CPR_MEMORY_DIAGNOSTIC","CPR_A2_ADMISSION","CPR_A1B_DEFER_FIRST_PHASE"):env.pop(k,None)
        with tempfile.TemporaryDirectory() as tmp:
            meter=Path(tmp)/"meter"
            r=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(meter),"timeout","--kill-after=1s","15s",str(binary),"cpr"],cwd=ROOT,env=env,capture_output=True,text=True,preexec_fn=limit)
            resource=meter.read_text().splitlines()[-1].split() if meter.exists() and meter.read_text().strip() else []
        records=[l for l in r.stdout.splitlines() if l.startswith(("CPR_A4B_TRIGGER ","CPR_A4B_NO_TRIGGER ","CPR_A1_STOP "))]
        row=dict(re.findall(r"(\w+)=([^ ]+)",records[0])) if len(records)==1 else {}
        if "CRR_GENERIC_CALL " in r.stdout or "CPR_PUBLIC " in r.stdout:status="ERROR"
        elif r.returncode in (124,137) or "memory allocation" in r.stderr.lower():status="CENSORED"
        elif r.returncode or len(resource)!=2 or len(records)!=1:status="ERROR"
        elif records[0].startswith("CPR_A4B_TRIGGER "):status="TRIGGER"
        elif records[0].startswith("CPR_A4B_NO_TRIGGER "):status="NO_TRIGGER"
        else:status="PREFIX_STOP"
        if status=="ERROR":errors.append([name,variant])
        counts[status]=counts.get(status,0)+1
        # Static oracle envelope, not a completed independent proof.
        # Include ALL ket-phase triggers in envelope, even budget rejects.
        envelope=bool(row and "source_gates" in row and (n<=8 or n<=32 and int(row["source_gates"])+int(row["target_gates"])<=1000))
        if status=="TRIGGER" and row["kind"]=="ket_phase" and envelope:eligible.append([name,variant])
        emit("CPR_A4B_TRIAL",case=name,variant=variant,n=n,status=status,record=row,oracle_envelope=envelope,outer_s=float(resource[0]) if len(resource)==2 else None,rss_kib=int(resource[1]) if len(resource)==2 else None,returncode=r.returncode,stderr=r.stderr[-800:] if status in ("ERROR","CENSORED") else "")
    emit("CPR_A4B_CENSUS_GATE",attempted=sum(counts.values()),counts=counts,errors=errors,ket_phase_oracle_envelope=eligible)
    assert sum(counts.values())==43 and not errors

if __name__=="__main__":main()

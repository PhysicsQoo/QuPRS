#!/usr/bin/env python3
"""D7e bounded correctness screen; no DAG route or performance admission."""
import json, os, subprocess, sys, time
from pathlib import Path
from eq_dag_d1 import sha, git, markers
DONE={"equivalent","equivalent*","not_equivalent"}

def python_arm(left,right):
    from QuPRS import check_equivalence
    r=check_equivalence(left,right,method="reduction_rules",strategy="Proportional",backend="python",timeout=8)
    print("D7E_PYTHON "+json.dumps({"verdict":r.equivalent}),flush=True)

def main():
    import numpy as np
    import qiskit
    import symengine as se
    from qiskit import qasm2
    from qiskit.quantum_info import Operator
    from QuPRS.pathsum.pattern_match import match_HH
    base,fixed,gpmc,out=map(lambda p:Path(p).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    mpath=Path(__file__).with_name("eq_dag_d7e_manifest.json")
    m=json.loads(mpath.read_text())
    for k in ("original","fix"):
        assert git("rev-parse",m[k]+"^{tree}")==m[k+"_tree"]
    x,y,v=se.symbols("x y v")
    assert match_HH(x*y/2,(y,),(y,),(x,))==(None,None,None,None)
    assert match_HH(y*v/2,(y,),(y,v),(x,))[:2]==(y,v)
    print("D7E_PYTHON_HH_TARGET_CONTROLS_PASS",flush=True)
    (out/"provenance.json").write_text(json.dumps(dict(head=git("rev-parse","HEAD"),manifest_sha=sha(mpath),original_binary_sha=sha(base),fixed_binary_sha=sha(fixed),gpmc_sha=sha(gpmc),qiskit=qiskit.__version__,numpy=np.__version__,symengine=se.__version__),indent=2))
    rows=[];issues=[];gaps=[]
    env=os.environ.copy()
    for k in list(env):
        if k.startswith("QUPRS_RESEARCH_") or k=="QUPRS_KEEP_FAILED_CNF":env.pop(k)
    env["QUPRS_GPMC_PATH"]=str(gpmc)
    def save(row):
        rows.append(row)
        with (out/"rows.jsonl").open("a") as f:f.write(json.dumps(row)+"\n")
        print("D7E_ARM",json.dumps(row),flush=True)
    def arm(c,variant,mode):
        d=out/f"{c['id']}-{variant}-{mode}";d.mkdir()
        a,b=(c[k]["path"] for k in ("left","right"))
        snap=d/"residual.tsv"
        if variant=="python":
            cmd=[sys.executable,str(Path(__file__).resolve()),"--python-arm",a,b]
        else:
            cmd=[str(base if variant=="original" else fixed),a,b,mode,"proportional",str(m["timeout_s"]),str(snap)]
        cmd=["prlimit","--as=4294967296","--","/usr/bin/time","-f","%M","-o",str(d/"rss.txt"),"timeout","--kill-after=2s",str(m["outer_timeout_s"]),*cmd]
        t=time.monotonic()
        p=subprocess.run(cmd,env=env,capture_output=True,text=True,errors="replace")
        wall=time.monotonic()-t
        (d/"stdout.txt").write_text(p.stdout);(d/"stderr.txt").write_text(p.stderr)
        if variant=="python":
            hits=[s[len("D7E_PYTHON "):] for s in p.stdout.splitlines() if s.startswith("D7E_PYTHON ")]
            r=json.loads(hits[0]) if len(hits)==1 else None
            receipt=None;metrics=None
        else:
            r=markers(p.stdout,"D1_RESULT");receipt=markers(p.stdout,"D1_SNAPSHOT");metrics=markers(p.stdout,"D1_METRICS")
        status="OUTER_TIMEOUT" if p.returncode in (124,137) else "ERROR" if p.returncode or not r else r["verdict"]
        snapshot_sha=sha(snap) if snap.exists() else None
        row=dict(case=c["id"],variant=variant,mode=mode,status=status,returncode=p.returncode,wall_s=wall,result=r,metrics=metrics,residual_sha256=snapshot_sha,rss_kib=(d/"rss.txt").read_text().strip() if (d/"rss.txt").exists() else None)
        save(row)
        if status=="ERROR":issues.append([c["id"],variant,mode,"execution error"])
        if variant!="python" and p.returncode==0:
            if not receipt or snapshot_sha!=receipt["sha256"]:issues.append([c["id"],variant,mode,"snapshot receipt"])
            if mode=="rr_only" and r["solver_invoked"]!="false":issues.append([c["id"],variant,mode,"RR solver invocation"])
        if status in DONE and (status=="not_equivalent")!=(c["expected"]=="NEQ"):
            issues.append([c["id"],variant,mode,"wrong decisive verdict"])
        return row
    for c in m["cases"]:
        circuits=[]
        for k in ("left","right"):
            z=c[k];assert git("hash-object",z["path"])==z["git_blob_sha1"]
            if "sha256" in z:assert sha(z["path"])==z["sha256"]
            circuits.append(qasm2.load(z["path"],custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS))
        n=circuits[0].num_qubits
        assert n==circuits[1].num_qubits and 1<=n<=9,(c["id"],n)
        a,b=(Operator(q).data for q in circuits)
        # Direct aligned Frobenius norm avoids cancellation near EQ.
        overlap=np.vdot(a,b)
        phase=overlap/abs(overlap) if abs(overlap)>0 else 1
        distance=float(np.linalg.norm(b-phase*a)/np.sqrt(2**n))
        oracle=dict(case=c["id"],qubits=n,distance=distance,expected=c["expected"],scope="Float64 full operator; not a formal rounding certificate")
        with (out/"oracle.jsonl").open("a") as f:f.write(json.dumps(oracle)+"\n")
        print("D7E_ORACLE",json.dumps(oracle),flush=True)
        if not (distance<=1e-8 if c["expected"]=="EQ" else distance>=1e-6):
            issues.append([c["id"],"oracle expectation not confirmed"]);continue
        for mode in ("rr_only","hybrid"):
            old=None if mode=="hybrid" and c["skip_old_hybrid"] else arm(c,"original",mode)
            new=arm(c,"fixed",mode)
            if old and old["status"] in DONE and new["status"] not in DONE:gaps.append([c["id"],mode,"completion regression"])
            if mode=="hybrid" and new["status"] not in DONE:gaps.append([c["id"],mode,"fixed Hybrid unresolved"])
            if c["skip_old_hybrid"] and (new["status"] not in {"equivalent","equivalent*"} or not new["result"] or new["result"]["solver_invoked"]!="false"):
                issues.append([c["id"],mode,"Feynman must finish via RR"])
            if mode=="rr_only" and c["python_rr"]:
                py=arm(c,"python",mode)
                if py["status"]!=new["status"]:gaps.append([c["id"],"python/native RR result differs",py["status"],new["status"]])
    summary=dict(cases=len(m["cases"]),arms=len(rows),issues=issues,gaps=gaps,scope="bounded correctness and completion screen; single samples not performance admission")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("D7E_SUMMARY",json.dumps(summary),flush=True)
    assert not issues and not gaps,(issues,gaps)
    print("D7E_SCOPED_CORRECTNESS_PASS",flush=True)

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="--python-arm":python_arm(*sys.argv[2:])
    else:main()

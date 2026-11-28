#!/usr/bin/env python3
"""D7c local RR semantics audit. Explicit research switches; no production fix."""
import json,os,subprocess,sys,time
from pathlib import Path
from eq_dag_d1 import sha,git,markers,cnf_info
from eq_dag_e1d_parity import read_snapshot
def main():
    binary,gpmc,src,out=map(lambda x:Path(x).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    m=json.loads(Path(__file__).with_name("eq_dag_d7a_manifest.json").read_text())
    c=next(x for x in m["cases"] if x["id"]=="feynman_grover_5_eq")
    for z in (c["left"],c["right"]):assert git("hash-object",z["path"])==z["git_blob_sha1"]
    for path,blob in m["router_source_blobs"].items():assert git("hash-object",path)==blob
    assert (src/"head.txt").read_text().strip()=="749327480045ee52cfd7eab8f8999e0f2125c011"
    assert (src/"tree.txt").read_text().strip()=="38f1af334c122c404c5781898fe34d098aba4543"
    prov=json.loads((src/"provenance.json").read_text());assert sha(gpmc)==prov["gpmc_sha256"]
    old=next(x for x in map(json.loads,(src/"rows.jsonl").read_text().splitlines()) if x["case"]==c["id"] and x["variant"]=="main")
    wrapper=out/"capture-gpmc.py"
    wrapper.write_text("#!/usr/bin/env python3\nimport os,sys,shutil\nfrom pathlib import Path\np=Path(os.environ['D1_CNF']);assert not p.exists();shutil.copyfile(sys.argv[-1],p)\nreal=os.environ['D1_GPMC'];os.execv(real,[real,*sys.argv[1:]])\n")
    wrapper.chmod(0o700)
    rows=[]
    def arm(label,guard,mode,strategy="proportional"):
        d=out/label;d.mkdir()
        env=os.environ.copy()
        env.pop("QUPRS_RESEARCH_PARITY_E2E",None);env.pop("QUPRS_KEEP_FAILED_CNF",None)
        env.update(QUPRS_RESEARCH_D7C_RR=guard,QUPRS_GPMC_PATH=str(wrapper),D1_GPMC=str(gpmc),D1_CNF=str(d/"actual.cnf"))
        if mode=="hybrid":env["QUPRS_RESEARCH_PARITY_E2E"]="combined"
        cmd=["prlimit","--as=4294967296","--","/usr/bin/time","-f","%M","-o",str(d/"rss.txt"),"timeout","--kill-after=2s","70" if mode=="hybrid" else "25",str(binary),c["left"]["path"],c["right"]["path"],mode,strategy,"60" if mode=="hybrid" else "20",str(d/"residual.tsv")]
        t=time.monotonic();p=subprocess.run(cmd,env=env,capture_output=True,text=True,errors="replace");wall=time.monotonic()-t
        (d/"stdout.txt").write_text(p.stdout);(d/"stderr.txt").write_text(p.stderr)
        snap=d/"residual.tsv";cnf=d/"actual.cnf";r=markers(p.stdout,"D1_RESULT")
        hh=[l for l in p.stderr.splitlines() if l.startswith("D7C_HH ")]
        elim=[l for l in p.stderr.splitlines() if l.startswith("D7C_ELIM ")]
        row=dict(label=label,guard=guard,mode=mode,strategy=strategy,returncode=p.returncode,wall_s=wall,result=r,hh=len(hh),hh_input=sum("input_target=true" in l for l in hh),elim_events=len(elim),elim_removed=sum(int(l.split()[1].split("=")[1]) for l in elim if "blocked=false" in l),residual_sha256=sha(snap) if snap.exists() else None,cnf=cnf_info(cnf) if cnf.exists() else None)
        if snap.exists():
            n,h,phase,f=read_snapshot(snap.read_bytes());row.update(n=n,h=h,terms=len(phase),output_terms=sum(map(len,f.values())))
        rows.append(row);print("D7C_ARM",json.dumps(row),flush=True)
        return row
    a=arm("audit","audit","rr_only")
    assert a["returncode"]==0 and a["residual_sha256"]==old["residual_sha256"],"audit did not reproduce sealed residual"
    assert a["result"]["solver_invoked"]=="false"
    tested=set()
    for guard,needed in (("guard_hh",a["hh_input"]>0),("guard_both",a["elim_removed"]>0)):
        if not needed:continue
        b=arm(guard,guard,"rr_only")
        if b["returncode"]==0 and b["residual_sha256"] and b["residual_sha256"]!=a["residual_sha256"] and b["residual_sha256"] not in tested:
            tested.add(b["residual_sha256"])
            if b["result"]["verdict"]=="unknown":
                arm(guard+"-hybrid",guard,"hybrid")
    # Distinct strategy can change reductions; diagnose only when no risky event occurred
    # or guards fail to produce an equivalent verdict. Bound the symbolic step.
    if not any(x.get("result") and x["result"]["verdict"] in ("equivalent","equivalent*") for x in rows):
        b=arm("difference-audit","audit","rr_only","difference")
        if b["returncode"]==0 and b["residual_sha256"]!=a["residual_sha256"] and b["result"]["verdict"]=="unknown":
            arm("difference-hybrid","audit","hybrid","difference")
    summary=dict(rows=rows,scope="diagnostic only; HH external and Elim guards not proposed production fixes; no admission")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("D7C_SUMMARY",json.dumps(summary),flush=True)
if __name__=="__main__":main()

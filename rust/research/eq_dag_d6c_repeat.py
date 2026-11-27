#!/usr/bin/env python3
"""D6c candidate-only reproducibility; no repeated baseline timeout."""
import json,os,statistics,subprocess,sys,time
from pathlib import Path
from eq_dag_d1 import sha,git,cnf_info,markers
def main():
    binary,gpmc,src,out=map(lambda x:Path(x).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    m=json.loads(Path(__file__).with_name("eq_dag_d6a_manifest.json").read_text())
    for path,blob in m["router_source_blobs"].items():assert git("hash-object",path)==blob
    assert (src/"head.txt").read_text().strip()=="6a5037030103dc77a54f29550cea40327536320e"
    assert (src/"tree.txt").read_text().strip()=="19742687bbab41d338366ba53e87b3a993daaa1a"
    prov=json.loads((src/"provenance.json").read_text())
    assert sha(gpmc)==prov["gpmc_sha256"]
    c=next(c for c in m["cases"] if c["id"]=="wstate_16_neq")
    old=next(x for x in map(json.loads,(src/"rows.jsonl").read_text().splitlines()) if x["case"]==c["id"] and x["variant"]=="combined")
    assert old["status"]=="not_equivalent" and old["route"]=="parity"
    for k in ("left","right"):
        z=c[k];assert sha(Path(z["path"]))==z["sha256"] and git("hash-object",z["path"])==z["git_blob_sha1"]
    wrapper=out/"capture-gpmc.py"
    wrapper.write_text("#!/usr/bin/env python3\nimport os,sys,shutil\nfrom pathlib import Path\np=Path(os.environ['D1_CNF']);assert not p.exists();shutil.copyfile(sys.argv[-1],p)\nreal=os.environ['D1_GPMC'];os.execv(real,[real,*sys.argv[1:]])\n")
    wrapper.chmod(0o700)
    rows=[]
    for i in range(1,8):
        d=out/f"candidate-{i}";d.mkdir()
        env=os.environ.copy();env.pop("QUPRS_KEEP_FAILED_CNF",None)
        env.update(QUPRS_RESEARCH_PARITY_E2E="combined",QUPRS_GPMC_PATH=str(wrapper),D1_GPMC=str(gpmc),D1_CNF=str(d/"actual.cnf"))
        cmd=["prlimit","--as=4294967296","--","/usr/bin/time","-f","%M","-o",str(d/"rss.txt"),"timeout","--kill-after=2s","70",str(binary),c["left"]["path"],c["right"]["path"],"hybrid",c["strategy"],"60",str(d/"residual.tsv")]
        t=time.monotonic();p=subprocess.run(cmd,env=env,capture_output=True,text=True,errors="replace");wall=time.monotonic()-t
        (d/"stdout.txt").write_text(p.stdout);(d/"stderr.txt").write_text(p.stderr)
        rr=markers(p.stdout,"D1_RESULT");ss=markers(p.stdout,"D1_SNAPSHOT")
        cnf=d/"actual.cnf";snap=d/"residual.tsv";rss=d/"rss.txt"
        row=dict(period=i,returncode=p.returncode,result=rr,wall_s=wall,rss_kib=rss.read_text().strip() if rss.exists() else None,cnf=cnf_info(cnf) if cnf.exists() else None,residual_sha256=sha(snap) if snap.exists() else None,route=[x for x in p.stderr.splitlines() if x.startswith("D5B_ROUTE ")])
        rows.append(row)
        print("D6C_ARM",json.dumps(row),flush=True)
        assert p.returncode==0 and rr and ss and rr["verdict"]=="not_equivalent" and rr["solver_invoked"]=="true"
        assert row["residual_sha256"]==ss["sha256"]==old["residual_sha256"]
        assert row["cnf"]["sha256"]==old["cnf"]["sha256"]
        assert len(row["route"])==1 and "route=parity " in row["route"][0]
        assert row["rss_kib"].isdigit()
    summary=dict(case=c["id"],candidate_runs=len(rows),decisive=len(rows),median_wall_s=statistics.median(x["wall_s"] for x in rows),median_rss_kib=statistics.median(int(x["rss_kib"]) for x in rows),baseline_runs=0,solver_sha256=sha(gpmc),binary_sha256=sha(binary),scope="candidate-only completion reproducibility; not matched speedup")
    (out/"summary.json").write_text(json.dumps(dict(summary=summary,rows=rows),indent=2)+"\n")
    print("D6C_SUMMARY",json.dumps(summary),flush=True)
if __name__=="__main__":main()

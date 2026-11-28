#!/usr/bin/env python3
"""D8 corrected-baseline paired screen; frozen router, no threshold tuning."""
import json,os,statistics,subprocess,sys,time
from pathlib import Path
from eq_dag_d1 import sha,git,cnf_info,markers
DONE={"equivalent","equivalent*","not_equivalent"}
def main():
    base,candidate,gpmc,out=map(lambda x:Path(x).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    mp=Path(__file__).with_name("eq_dag_d8_manifest.json")
    m=json.loads(mp.read_text())
    for key in ("baseline","frozen_router"):
        assert git("rev-parse",m[key]+"^{tree}")==m["baseline_tree" if key=="baseline" else "router_tree"]
    for path,blob in m["router_source_blobs"].items():assert git("hash-object",path)==blob
    for c in m["cases"]:
        for k in ("left","right"):
            z=c[k]
            assert git("hash-object",z["path"])==z["git_blob_sha1"]
            if "sha256" in z:assert sha(Path(z["path"]))==z["sha256"]
    wrapper=out/"capture-gpmc.py"
    wrapper.write_text("#!/usr/bin/env python3\nimport os,sys,shutil\nfrom pathlib import Path\np=Path(os.environ['D1_CNF']); assert not p.exists(); shutil.copyfile(sys.argv[-1],p)\nreal=os.environ['D1_GPMC']; os.execv(real,[real,*sys.argv[1:]])\n")
    wrapper.chmod(0o700)
    (out/"provenance.json").write_text(json.dumps(dict(head=git("rev-parse","HEAD"),frozen_router=m["frozen_router"],baseline=m["baseline"],manifest_sha256=sha(mp),gpmc_sha256=sha(gpmc),baseline_binary_sha256=sha(base),candidate_binary_sha256=sha(candidate),timeout_s=m["timeout_s"],address_space_mib=m["address_space_mib"]),indent=2)+"\n")
    rows=[];issues=[]
    def arm(c,i,v):
        d=out/f"{c['id']}-{i}-{v}";d.mkdir()
        env={k:v for k,v in os.environ.items() if not k.startswith("QUPRS_RESEARCH_") and k!="QUPRS_KEEP_FAILED_CNF"}
        if v=="combined":env["QUPRS_RESEARCH_PARITY_E2E"]="combined"
        env.update(QUPRS_GPMC_PATH=str(wrapper),D1_GPMC=str(gpmc),D1_CNF=str(d/"actual.cnf"))
        cmd=["prlimit","--as=4294967296","--","/usr/bin/time","-f","%M","-o",str(d/"rss.txt"),"timeout","--kill-after=2s","70",str(base if v=="main" else candidate),c["left"]["path"],c["right"]["path"],c["mode"],c["strategy"],"60",str(d/"residual.tsv")]
        t=time.monotonic();p=subprocess.run(cmd,env=env,capture_output=True,text=True,errors="replace");wall=time.monotonic()-t
        (d/"stdout.txt").write_text(p.stdout);(d/"stderr.txt").write_text(p.stderr)
        r=markers(p.stdout,"D1_RESULT");s=markers(p.stdout,"D1_SNAPSHOT")
        status="OUTER_TIMEOUT" if p.returncode in (124,137) else "ERROR" if p.returncode or not r else r["verdict"]
        route_logs=[x for x in p.stderr.splitlines() if x.startswith("D5B_ROUTE ")]
        route=route_logs[0].split()[1].split("=")[1] if route_logs else "flat"
        cnf=d/"actual.cnf";snap=d/"residual.tsv";rss=d/"rss.txt"
        x=dict(case=c["id"],family=c["family"],mode=c["mode"],expected=c["expected"],period=i,variant=v,status=status,wall_s=wall,returncode=p.returncode,result=r,route=route,route_log=route_logs,rss_kib=rss.read_text().strip() if rss.exists() else None,residual_sha256=sha(snap) if s and snap.exists() else None,cnf=cnf_info(cnf) if cnf.exists() else None)
        rows.append(x)
        with (out/"rows.jsonl").open("a") as f:f.write(json.dumps(x)+"\n")
        print("D8_ARM",json.dumps(x),flush=True)
        def check(ok,msg):
            if not ok:issues.append([c["id"],i,v,msg])
        if p.returncode==0:
            check(bool(r and s and x["residual_sha256"]==s["sha256"]),"receipt")
        check(status!="ERROR","execution error")
        check(len(route_logs)<=1 and route in {"flat","parity","factored"},"route grammar")
        if v=="main" or c["mode"]=="rr_only":check(not route_logs,"unexpected route")
        if c["mode"]=="rr_only":check(not x["cnf"] and (not r or r["solver_invoked"]=="false"),"RR-only solver")
        if c["id"]=="feynman_grover_5_eq":check(status=="equivalent*" and r and r["solver_invoked"]=="false" and not x["cnf"] and not route_logs,"corrected Feynman must bypass encoder")
        if status in DONE:check((status=="not_equivalent")==(c["expected"]=="NEQ"),"expected verdict")
        return x
    def pair(c,i):
        order=("main","combined") if i%2 else ("combined","main")
        a,b=sorted([arm(c,i,v) for v in order],key=lambda x:x["variant"],reverse=True)
        assert a["variant"]=="main" and b["variant"]=="combined"
        if a["residual_sha256"] and b["residual_sha256"] and a["residual_sha256"]!=b["residual_sha256"]:issues.append([c["id"],i,"residual drift"])
        if a["status"] in DONE and b["status"] in DONE and a["status"]!=b["status"]:issues.append([c["id"],i,"verdict drift"])
        if c["mode"]=="rr_only" and a["status"]!=b["status"]:issues.append([c["id"],i,"RR verdict drift"])
        if b["route"]=="flat" and a["cnf"] and b["cnf"] and a["cnf"]["sha256"]!=b["cnf"]["sha256"]:issues.append([c["id"],i,"Flat CNF drift"])
        if a["status"] in DONE and b["status"] not in DONE:issues.append([c["id"],i,"completion regression"])
        if b["route"]!="flat" and not b["cnf"] and b["status"] in DONE:issues.append([c["id"],i,"missing candidate CNF"])
        return a,b
    stats=[]
    for c in m["cases"]:
        a,b=pair(c,1)
        eligible=all(x["returncode"]==0 and x["wall_s"]<=5 and (x["status"] in DONE or (c["mode"]=="rr_only" and x["status"]=="unknown")) for x in (a,b))
        if eligible:
            for i in range(2,8):pair(c,i)
        aa=[r for r in rows if r["case"]==c["id"]]
        st={}
        for v in ("main","combined"):
            q=[r for r in aa if r["variant"]==v]
            st[v]=dict(statuses=[r["status"] for r in q],routes=[r["route"] for r in q],median_wall_s=statistics.median(r["wall_s"] for r in q),median_rss_kib=statistics.median(int(r["rss_kib"]) for r in q) if all(str(r["rss_kib"]).isdigit() for r in q) else None)
        seven=eligible and len(aa)==14 and all(r["returncode"]==0 and (r["status"] in DONE or c["mode"]=="rr_only" and r["status"]=="unknown") for r in aa)
        x=dict(case=c["id"],family=c["family"],mode=c["mode"],paired_periods=len(aa)//2,seven_complete=seven,stats=st)
        if seven:
            x["wall_ratio"]=st["main"]["median_wall_s"]/st["combined"]["median_wall_s"]
            if st["main"]["median_rss_kib"] and st["combined"]["median_rss_kib"]:x["rss_ratio"]=st["combined"]["median_rss_kib"]/st["main"]["median_rss_kib"]
            x["nonbeneficiary"]=c["mode"]=="rr_only" or all(r["route"]=="flat" for r in aa if r["variant"]=="combined")
            if x["nonbeneficiary"] and (x["wall_ratio"]<1/1.05 or x.get("rss_ratio",float("inf"))>1.05):issues.append([c["id"],"seven-round nonbeneficiary regression"])
        stats.append(x);print("D8_CASE",json.dumps(x),flush=True)
    summary=dict(arms=len(rows),cases=len(stats),seven_complete=sum(x["seven_complete"] for x in stats),issues=issues,stats=stats,scope="corrected baseline existing cohort; changed-CNF replay and final admission pending")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("D8_SUMMARY",json.dumps(summary),flush=True)
    assert not issues,issues
if __name__=="__main__":main()

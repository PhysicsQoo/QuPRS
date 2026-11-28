#!/usr/bin/env python3
"""D7f bounded matched native RR-only nonregression."""
import json,os,statistics,subprocess,sys,time
from pathlib import Path
from eq_dag_d1 import git,sha,markers
def main():
    old,new,out=map(lambda x:Path(x).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    mp=Path(__file__).with_name("eq_dag_d7f_manifest.json")
    m=json.loads(mp.read_text())
    for k in ("original","corrected"):
        assert git("rev-parse",m[k]+"^{tree}")==m[k+"_tree"]
    (out/"provenance.json").write_text(json.dumps(dict(head=git("rev-parse","HEAD"),manifest_sha256=sha(mp),original_binary_sha256=sha(old),corrected_binary_sha256=sha(new)),indent=2))
    env={k:v for k,v in os.environ.items() if not k.startswith("QUPRS_RESEARCH_") and k!="QUPRS_KEEP_FAILED_CNF"}
    issues=[];holds=[];summaries=[]
    for c in m["cases"]:
        for side in ("left","right"):
            z=c[side];assert git("hash-object",z["path"])==z["git_blob_sha1"]
        rows=[]
        for i in range(1,8):
            for v in (("original","corrected") if i%2 else ("corrected","original")):
                d=out/f"{c['id']}-{i}-{v}";d.mkdir()
                snap=d/"residual.tsv";rss=d/"rss.txt"
                cmd=["prlimit","--as=4294967296","--","/usr/bin/time","-f","%M","-o",str(rss),"timeout","--kill-after=2s","12",str(old if v=="original" else new),c["left"]["path"],c["right"]["path"],"rr_only","proportional","8",str(snap)]
                t=time.monotonic();p=subprocess.run(cmd,env=env,capture_output=True,text=True,errors="replace");wall=time.monotonic()-t
                (d/"stdout.txt").write_text(p.stdout);(d/"stderr.txt").write_text(p.stderr)
                r=markers(p.stdout,"D1_RESULT");s=markers(p.stdout,"D1_SNAPSHOT")
                sh=sha(snap) if snap.exists() else None
                status="OUTER_TIMEOUT" if p.returncode in (124,137) else "ERROR" if p.returncode or not r else r["verdict"]
                row=dict(case=c["id"],period=i,variant=v,status=status,returncode=p.returncode,wall_s=wall,rss_kib=int(rss.read_text().strip()) if rss.exists() and rss.read_text().strip().isdigit() else None,result=r,residual_sha256=sh)
                rows.append(row)
                with (out/"rows.jsonl").open("a") as f:f.write(json.dumps(row)+"\n")
                print("D7F_ARM",json.dumps(row),flush=True)
                if status in {"ERROR","not_equivalent"}:issues.append([c["id"],i,v,status])
                if p.returncode==0 and (not r or not s or sh!=s["sha256"] or r["solver_invoked"]!="false"):issues.append([c["id"],i,v,"receipt or solver"])
            pair={r["variant"]:r for r in rows[-2:]}
            a,b=pair["original"],pair["corrected"]
            if c["beneficiary"]:
                if a["status"]!="unknown" or b["status"]!="equivalent*" or not b["result"] or b["result"]["rr_approximate"]!="false":issues.append([c["id"],i,"known correction not reproduced"])
            elif a["returncode"]==b["returncode"]==0 and (a["status"]!=b["status"] or a["residual_sha256"]!=b["residual_sha256"]):issues.append([c["id"],i,"nonbeneficiary residual/verdict drift"])
            if i==1 and not all(r["returncode"]==0 and r["status"] in {"equivalent","equivalent*","unknown"} and r["wall_s"]<=5 and r["rss_kib"] for r in rows):break
        complete=len(rows)==14 and all(r["returncode"]==0 and r["status"] in {"equivalent","equivalent*","unknown"} and r["rss_kib"] for r in rows)
        result=dict(case=c["id"],beneficiary=c["beneficiary"],paired_periods=len(rows)//2,complete=complete)
        if complete:
            stats={}
            for v in ("original","corrected"):
                rs=[r for r in rows if r["variant"]==v]
                if len({(r["status"],r["residual_sha256"]) for r in rs})!=1:issues.append([c["id"],v,"repeat instability"])
                stats[v]=dict(wall=statistics.median(r["wall_s"] for r in rs),rss=statistics.median(r["rss_kib"] for r in rs),pathsum=statistics.median(float(r["result"]["pathsum_s"]) for r in rs))
            a,b=stats["original"],stats["corrected"]
            result.update(stats=stats,wall_ratio=b["wall"]/a["wall"],rss_ratio=b["rss"]/a["rss"])
            if not c["beneficiary"] and (result["wall_ratio"]>1.05 or result["rss_ratio"]>1.05):holds.append([c["id"],"median wall/RSS above 5%"])
        else:holds.append([c["id"],"incomplete/censored"])
        summaries.append(result);print("D7F_CASE",json.dumps(result),flush=True)
    summary=dict(cases=summaries,issues=issues,holds=holds,scope="bounded native RR-only screen, not DAG admission")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("D7F_SUMMARY",json.dumps(summary),flush=True)
    assert not issues and not holds,(issues,holds)
    print("D7F_SCOPED_NONREGRESSION_PASS")
if __name__=="__main__":main()

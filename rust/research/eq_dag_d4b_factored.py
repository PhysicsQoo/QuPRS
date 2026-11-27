#!/usr/bin/env python3
"""D4b actual native EQ, pinned main vs explicit E1b factored. Seven paired periods, no automatic admission."""
import json,os,statistics,subprocess,sys,time
from pathlib import Path
from eq_dag_d1 import sha,git,cnf_info,markers
BASE="b398f07d6845efc23540549ccbfec717c27b1722"
CASES={"grover-noancilla_negative_5":7,"qwalk-noancilla_negative_5":7,"vqe_negative_8":7}
DONE={"equivalent","equivalent*","not_equivalent"}
def main():
    baseline,candidate,gpmc,d1,e1e,out=map(lambda s:Path(s).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    manifest=Path(__file__).with_name("eq_dag_d1d_manifest.json")
    m=json.loads(manifest.read_text());assert m["baseline"]==BASE
    assert git("rev-parse",BASE+"^{tree}")==m["tree"]
    assert json.loads((d1/"provenance.json").read_text())["gpmc_sha256"]==sha(gpmc)
    receipts={r["case"]:r for r in json.loads((e1e/"receipts.json").read_text())["rows"]}
    sources={r["case"]:r for r in map(json.loads,(d1/"rows.jsonl").read_text().splitlines())}
    cases={r["id"]:r for r in m["cases"]}
    wrapper=out/"capture-gpmc.py"
    wrapper.write_text("#!/usr/bin/env python3\nimport os,sys,shutil\nfrom pathlib import Path\np=Path(os.environ['D1_CNF']); assert not p.exists(); shutil.copyfile(sys.argv[-1],p)\nreal=os.environ['D1_GPMC']; os.execv(real,[real,*sys.argv[1:]])\n")
    wrapper.chmod(0o700)
    (out/"provenance.json").write_text(json.dumps(dict(head=git("rev-parse","HEAD"),baseline=BASE,baseline_binary_sha256=sha(baseline),candidate_binary_sha256=sha(candidate),gpmc_sha256=sha(gpmc),manifest_sha256=sha(manifest),timeout_s=60,address_space_mib=4096,scope="forced native E1b factored, not final admission"),indent=2)+"\n")
    rows=[]
    def arm(case,mode,period,variant):
        c=cases[case];d=out/f"{case}-{mode}-{period}-{variant}";d.mkdir()
        for side in ("left","right"):
            z=c[side];assert git("hash-object",z["path"])==z["git_blob_sha1"]
            if "sha256" in z:assert sha(Path(z["path"]))==z["sha256"]
        env=os.environ.copy();env.pop("QUPRS_KEEP_FAILED_CNF",None);env.pop("QUPRS_RESEARCH_PARITY_E2E",None)
        if variant=="factored":env["QUPRS_RESEARCH_PARITY_E2E"]="factored"
        env.update(QUPRS_GPMC_PATH=str(wrapper),D1_GPMC=str(gpmc),D1_CNF=str(d/"actual.cnf"))
        binary=baseline if variant=="main" else candidate
        cmd=["prlimit","--as=4294967296","--","/usr/bin/time","-f","%M","-o",str(d/"rss.txt"),"timeout","--kill-after=2s","70",str(binary),c["left"]["path"],c["right"]["path"],mode,c["strategy"],"60",str(d/"residual.tsv")]
        t=time.monotonic();p=subprocess.run(cmd,env=env,capture_output=True,text=True,errors="replace");wall=time.monotonic()-t
        (d/"stdout.txt").write_text(p.stdout);(d/"stderr.txt").write_text(p.stderr)
        r=markers(p.stdout,"D1_RESULT");s=markers(p.stdout,"D1_SNAPSHOT")
        status="OUTER_TIMEOUT" if p.returncode in (124,137) else "ERROR" if p.returncode else r["verdict"]
        selected="D4_FACTORED_SELECTED " in p.stderr
        cnf=d/"actual.cnf";snap=d/"residual.tsv"
        x=dict(case=case,mode=mode,period=period,variant=variant,status=status,wall_s=wall,returncode=p.returncode,result=r,selected=selected,route_log=[x for x in p.stderr.splitlines() if x.startswith("D4_FACTORED_SELECTED ")],rss_kib=(d/"rss.txt").read_text().strip() if (d/"rss.txt").exists() else None,residual_sha256=sha(snap) if s and snap.exists() else None,cnf=cnf_info(cnf) if cnf.exists() else None)
        if s:assert x["residual_sha256"]==s["sha256"]
        rows.append(x)
        with (out/"rows.jsonl").open("a") as f:f.write(json.dumps(x)+"\n")
        print("D4B_ARM",json.dumps(x),flush=True)
        assert p.returncode==0 and r and s
        if status in DONE:assert (status=="not_equivalent")==(c["expected"]=="NEQ")
        if mode=="hybrid":
            assert x["residual_sha256"]==sources[case]["residual_sha256"] and x["cnf"],case
            assert selected==(variant=="factored")
            expected=receipts[case]["factored_sha256"] if selected else sources[case]["cnf"]["sha256"]
            assert x["cnf"]["sha256"]==expected,(case,variant,"solver input drift")
        else:
            assert not selected and not x["cnf"] and r["solver_invoked"]=="false"
        return x
    for case,periods in CASES.items():
        for i in range(1,periods+1):
            order=("factored","main") if i%2==0 else ("main","factored")
            a,b=[arm(case,"hybrid",i,v) for v in order]
            if a["status"] in DONE and b["status"] in DONE:assert a["status"]==b["status"],case
    stats=[]
    for case,mode in sorted({(r["case"],r["mode"]) for r in rows}):
        s={}
        for v in ("main","factored"):
            a=[r for r in rows if (r["case"],r["mode"],r["variant"])==(case,mode,v)]
            done=[r for r in a if r["status"] in DONE or mode=="rr_only"]
            rss=[int(r["rss_kib"]) for r in done if str(r["rss_kib"]).isdigit()]
            s[v]=dict(statuses=[r["status"] for r in a],median_wall_s=statistics.median(r["wall_s"] for r in done) if len(done)==len(a) else None,median_rss_kib=statistics.median(rss) if len(rss)==len(a) else None)
        x=dict(case=case,mode=mode,stats=s)
        if all(s[v]["median_wall_s"] is not None for v in s):x["wall_ratio"]=s["main"]["median_wall_s"]/s["factored"]["median_wall_s"]
        stats.append(x);print("D4B_CASE",json.dumps(x),flush=True)
    assert len(rows)==42
    assert all(r["status"] in DONE for r in rows),"unexpected incomplete arm; no performance admission"
    summary=dict(arms=len(rows),hybrid=sum(r["mode"]=="hybrid" for r in rows),rr=sum(r["mode"]=="rr_only" for r in rows),complete=sum(r["status"] in DONE for r in rows),stats=stats,scope="forced factored; not final admission")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("D4B_SUMMARY",json.dumps(summary),flush=True)
if __name__=="__main__":main()

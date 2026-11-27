#!/usr/bin/env python3
"""Scoped width admission A/B, no change to lowering or solver, exact count."""
import hashlib,json,os,pathlib,subprocess,sys,time
import autoq_grover_p0 as grover
from hoare_ganak_exact import single_fibre_pack,single_fibre_decode,parse_gpmc_integer

def main():
    binary,solver,out,root,smoke=map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:6])
    out.mkdir(parents=True,exist_ok=False)
    # Verify actual emitted high-ID encoder CNF, including MPZ counts >2^32.
    for h in (32,33,47,48):
        base=(smoke/f"h{h}.cnf").read_text()
        data,radix,bound=single_fibre_pack(base,[-1,-1,-1],h)
        path=out/f"smoke-{h}.cnf";path.write_text(data)
        p=subprocess.run([str(solver),"-mode=1","-natw",str(path)],capture_output=True,text=True,timeout=20,check=True)
        (out/f"smoke-{h}.log").write_text(p.stdout+p.stderr)
        bins=single_fibre_decode(parse_gpmc_integer(p.stdout,"wmc",bound*radix**7),radix,bound,8)
        assert bins==[1<<(h-1)]+[0]*7,(h,bins)
        print("AQ_SHARED_WIDTH_SMOKE "+json.dumps(dict(h=h,bins=bins)),flush=True)
    fixtures,specs=grover.prepare(root,out)
    rows=[]
    for period in range(2):
        for case in (list(grover.CASES) if period==0 else list(reversed(grover.CASES))):
            for wide in (("0","1") if period==0 else ("1","0")):
                folder=out/f"{period}-{case}-{wide}";folder.mkdir()
                env=dict(os.environ,AQ_SHARED_WIDE=wide)
                t=time.monotonic()
                p=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(folder/"resource.txt"),
                    "timeout","--kill-after=1s","4",sys.executable,str(pathlib.Path(grover.__file__).resolve()),
                    "--worker",str(binary),str(solver),str(binary),str(fixtures),case,"wmc",str(folder)],
                    env=env,capture_output=True,text=True)
                elapsed=time.monotonic()-t
                (folder/"worker.stdout").write_text(p.stdout);(folder/"worker.stderr").write_text(p.stderr)
                if p.returncode in (124,137):
                    row=dict(verdict="UNKNOWN",reason="PROCESS_TIMEOUT",queries=None)
                else:
                    assert p.returncode==0,(case,wide,p.stdout,p.stderr)
                    row=json.loads(p.stdout)
                row.update(period=period,case=case,wide=wide,wall_s=elapsed)
                initial=folder/"base.initial.txt"
                row["initial_ir_sha256"]=hashlib.sha256(initial.read_bytes()).hexdigest() if initial.exists() else None
                assert row["initial_ir_sha256"],row
                log=folder/"native.log"
                row["encoding"]=[l.split("AQ_SHARED_WIDTH_ENCODING ",1)[1] for l in log.read_text().splitlines() if "AQ_SHARED_WIDTH_ENCODING " in l] if log.exists() else []
                sol=folder/"solver.jsonl"
                row["solver_records"]=[json.loads(l) for l in sol.read_text().splitlines() if l.strip().endswith("}")] if sol.exists() else []
                resource=(folder/"resource.txt").read_text().split() if (folder/"resource.txt").exists() else []
                row["rss_kib"]=int(resource[-1]) if resource and resource[-1].isdigit() else None
                assert row["verdict"] in ("UNKNOWN",grover.CASES[case]),row
                rows.append(row);print("AQ_SHARED_WIDTH_ARM "+json.dumps(row),flush=True)
    pairs=[]
    for period in range(2):
        for case in grover.CASES:
            a,b=[next(r for r in rows if r["period"]==period and r["case"]==case and r["wide"]==w) for w in ("0","1")]
            assert a["initial_ir_sha256"]==b["initial_ir_sha256"],(a,b)
            aa,bb=a["solver_records"],b["solver_records"]
            if not case.startswith("grover05"):
                assert a["verdict"]==b["verdict"]==grover.CASES[case],(a,b)
                assert len(aa)==len(bb)==1 and aa[0]["status"]==bb[0]["status"]=="EXACT"
                assert aa[0]["bins"]==bb[0]["bins"] and aa[0]["base_sha256"]==bb[0]["base_sha256"],(a,b)
            else:
                assert a["verdict"]=="UNKNOWN" and a.get("native",{}).get("admission")=="encoder-not-admitted",a
            pairs.append(dict(period=period,case=case,base=a["verdict"],wide=b["verdict"],same_initial=True))
    summary=dict(rows=rows,pairs=pairs,source_pin=grover.PIN,
        sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (binary,solver)})
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("AQ_SHARED_WIDTH_SUMMARY "+json.dumps(dict(arms=len(rows),pairs=len(pairs),
        wide05_definite=sum(r["wide"]=="1" and r["case"].startswith("grover05") and r["verdict"]!="UNKNOWN" for r in rows))),flush=True)
    assert len(rows)==40

if __name__=="__main__":main()

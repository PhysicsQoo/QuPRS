#!/usr/bin/env python3
"""D1 discovery only: one fresh process per source pair/mode; timings diagnostic.
Capture exact solver input using exec of pinned GPMC, no fake count or replay.
"""
import argparse, hashlib, json, os, pathlib, subprocess, sys, time

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()

def cnf_info(path):
    header = None
    clauses = literals = 0
    with path.open() as f:
        for line in f:
            parts = line.split()
            if not parts or parts[0] == "c":
                continue
            if parts[:2] == ["p", "cnf"]:
                assert header is None
                header = [int(x) for x in parts[2:]]
                continue
            assert parts[-1] == "0"
            clauses += 1
            literals += len(parts)-1
    assert header and header[1] == clauses
    return dict(variables=header[0], clauses=clauses, literals=literals, sha256=sha(path))

def markers(stdout, key):
    lines = [x for x in stdout.splitlines() if x.startswith(key+"\t")]
    assert len(lines) <= 1
    return dict(x.split("=",1) for x in lines[0].split("\t")[1:]) if lines else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("binary",type=pathlib.Path)
    ap.add_argument("gpmc",type=pathlib.Path)
    ap.add_argument("output",type=pathlib.Path)
    args=ap.parse_args()
    binary, solver, out = (p.resolve() for p in (args.binary,args.gpmc,args.output))
    assert binary.is_file() and solver.is_file()
    out.mkdir(parents=True,exist_ok=False)
    manifest_path=pathlib.Path(__file__).with_name("eq_dag_d1_manifest.json")
    manifest=json.loads(manifest_path.read_text())
    assert git("rev-parse",manifest["baseline"]+"^{tree}")==manifest["tree"]
    (out/"provenance.json").write_text(json.dumps(dict(head=git("rev-parse","HEAD"),tree=git("rev-parse","HEAD^{tree}"),baseline=manifest["baseline"],manifest_sha256=sha(manifest_path),binary_sha256=sha(binary),gpmc_sha256=sha(solver)),indent=2))
    # A unique wrapper destination per arm; use actual CNF bytes, then replace
    # wrapper with original executable so the existing solver supervision stays active.
    wrapper=out/"capture-gpmc.py"
    wrapper.write_text("#!/usr/bin/env python3\nimport os,sys,shutil\nfrom pathlib import Path\np=Path(os.environ['D1_CNF']); assert not p.exists(); tmp=p.with_suffix('.partial'); shutil.copyfile(sys.argv[-1],tmp); os.replace(tmp,p)\nreal=os.environ['D1_GPMC']; os.execv(real,[real,*sys.argv[1:]])\n")
    wrapper.chmod(0o700)
    rows=[]
    for c in manifest["cases"]:
        for side in ("left","right"):
            z=c[side]; assert git("hash-object",z["path"])==z["git_blob_sha1"],z
            if "sha256" in z: assert sha(z["path"])==z["sha256"],z
        for mode in ("hybrid","wmc_only"):
            arm=out/(c["id"]+"-"+mode);arm.mkdir()
            cnf=arm/"actual.cnf";snap=arm/"residual.tsv"
            env=os.environ.copy()
            env.update(QUPRS_GPMC_PATH=str(wrapper), D1_GPMC=str(solver), D1_CNF=str(cnf))
            env.pop("QUPRS_KEEP_FAILED_CNF",None)
            cmd=["/usr/bin/time","-f","%M","-o",str(arm/"rss.txt"),"timeout","--kill-after=2s",str(c["timeout"]+10),str(binary),c["left"]["path"],c["right"]["path"],mode,c["strategy"],str(c["timeout"]),str(snap)]
            t=time.monotonic()
            proc=subprocess.run(cmd,env=env,capture_output=True,text=True,errors="replace")
            elapsed=time.monotonic()-t
            (arm/"stdout.txt").write_text(proc.stdout);(arm/"stderr.txt").write_text(proc.stderr)
            res=markers(proc.stdout,"D1_RESULT"); metrics=markers(proc.stdout,"D1_METRICS"); receipt=markers(proc.stdout,"D1_SNAPSHOT")
            status="OUTER_TIMEOUT" if proc.returncode in (124,137) else "ERROR" if proc.returncode else res["verdict"]
            if proc.returncode==0:
                assert res and metrics and receipt and snap.exists()
                assert sha(snap)==receipt["sha256"]
                # A dispatched solver may time out before the wrapper starts.
                assert not cnf.exists() or res["solver_invoked"]=="true"
                if res["verdict"] in ("equivalent","equivalent*","not_equivalent"):
                    assert (res["solver_invoked"]=="true")==cnf.exists()
            wrong=bool(res and ((c["expected"]=="EQ" and res["verdict"]=="not_equivalent") or (c["expected"]=="NEQ" and res["verdict"] in ("equivalent","equivalent*"))))
            row=dict(case=c["id"],family=c["family"],mode=mode,expected=c["expected"],expectation=c["expectation"],strategy=c["strategy"],left_sha256=sha(c["left"]["path"]),right_sha256=sha(c["right"]["path"]),status=status,returncode=proc.returncode,expected_disagreement=wrong,wall_s=elapsed,result=res,metrics=metrics,residual_sha256=sha(snap) if receipt and snap.exists() else None,cnf=cnf_info(cnf) if cnf.exists() else None,rss_individual_kib=(arm/"rss.txt").read_text().strip() if (arm/"rss.txt").exists() else None)
            rows.append(row)
            with (out/"rows.jsonl").open("a") as f: f.write(json.dumps(row)+"\n")
            print("D1_ARM",json.dumps(row),flush=True)
    summary=dict(arms=len(rows),expected_arms=2*len(manifest["cases"]),residual_receipts=sum(bool(r["residual_sha256"]) for r in rows),actual_cnf=sum(bool(r["cnf"]) for r in rows),hybrid_actual_cnf=sum(r["mode"]=="hybrid" and bool(r["cnf"]) for r in rows),hybrid_paired_residual_cnf=sum(r["mode"]=="hybrid" and bool(r["cnf"]) and bool(r["residual_sha256"]) for r in rows),expected_disagreements=sum(r["expected_disagreement"] for r in rows),status_counts={s:sum(r["status"]==s for r in rows) for s in sorted({r["status"] for r in rows})})
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("D1_SUMMARY",json.dumps(summary),flush=True)
    assert summary["arms"]==summary["expected_arms"]
    # A census is not a correctness or performance gate; retain failures,
    # and require actual production residual+CNF evidence to call it usable.
    assert summary["hybrid_paired_residual_cnf"]>0

if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""SS2 typed synthetic finite StateSet acceptance, not AutoQ source coverage."""
import hashlib,json,os,pathlib,re,subprocess,sys,time
import autoq_c3_pilot as c3

CASES={"ss2-positive":"PROVED","ss2-negative":"REFUTED","ss2-nonclosed-post":"REFUTED",
       "ss2-nonclosed-pre":"PROVED","ss2-duplicate":"PROVED"}

def oracle(case):
    xs=[0,2,3] if case=="ss2-nonclosed-pre" else list(range(4))
    ts=[(0,-1),(1,-1),(0,1),(1,1)]
    if case=="ss2-negative":ts=ts[2:]
    if case=="ss2-nonclosed-post":del ts[1]
    if case=="ss2-duplicate":ts.insert(0,(0,-1))
    # Independent Hadamard action, integer amplitudes / sqrt(2).
    dots={}
    for x in xs:
        v=[0]*4;v[x&1]=1;v[(x&1)|2]=(-1 if x&2 else 1)
        dots[x]=[v[j]+sign*v[j|2] for j,sign in ts]
    assert ("PROVED" if all(any(d*d==4 for d in row) for row in dots.values()) else "REFUTED")==CASES[case]
    return xs,ts,dots

def worker(binary,solver,case,folder):
    c3.CASES.update(CASES)
    os.environ["AQ_C3_NATIVE_TEST"]="exact_property_cnf::hoare_autoq_ss2_arm"
    c3.arm(binary,solver,case,"wmc",folder)

def main():
    binary,solver,out=map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:4])
    out.mkdir(parents=True,exist_ok=False);rows=[]
    for period in range(2):
        def arm(case,route,bad=False):
            folder=out/f"{period}-{case}-{route}{'-bad' if bad else ''}";folder.mkdir()
            env=dict(os.environ,AQ_SHARED_FAMILY=route);env.pop("AQ_CPS_ORBIT_BAD",None)
            if bad:env["AQ_CPS_ORBIT_BAD"]="1"
            t=time.monotonic()
            p=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(folder/"resource.txt"),
                "timeout","--kill-after=1s","4",sys.executable,str(pathlib.Path(__file__).resolve()),
                "--worker",str(binary),str(solver),case,str(folder)],env=env,capture_output=True,text=True)
            elapsed=time.monotonic()-t
            (folder/"worker.stdout").write_text(p.stdout);(folder/"worker.stderr").write_text(p.stderr)
            assert p.returncode==0,(case,route,p.returncode,p.stderr,p.stdout)
            row=json.loads(p.stdout);assert row["verdict"]==CASES[case],row
            lines=(folder/"native.log").read_text().splitlines()
            route_line=next(l for l in lines if "AQ_SS2_ROUTE " in l)
            reps=json.loads(re.search(r"indices=(\[[0-9, ]*\])",route_line)[1])
            xs,ts,dots=oracle(case)
            expected=list(range(len(xs))) if route=="full" or bad or case in ("ss2-nonclosed-pre","ss2-nonclosed-post") else [0,2]
            assert reps==expected,(case,route,reps,expected)
            if case in ("ss2-positive","ss2-duplicate"):assert "ambiguous=true" in route_line
            certs=[l for l in lines if "AQ_SS2_CERT " in l]
            if route=="orbit" and case in ("ss2-positive","ss2-negative","ss2-duplicate"):
                assert any("exact=true" in l for l in certs)==(not bad),certs
                if bad:assert any("status=not_equivalent" in l for l in certs),certs
            pairs=[dict(kv.split("=") for kv in l.split("AQ_SS2_PAIR ",1)[1].split()) for l in lines if "AQ_SS2_PAIR " in l]
            records=[json.loads(l) for l in (folder/"solver.jsonl").read_text().splitlines()]
            assert len(pairs)==len(records)==row["queries"]
            actual=[]
            for pair,rec in zip(pairs,records):
                x,j=int(pair["input"]),int(pair["target"])
                assert rec["status"]=="EXACT" and int(pair["k"])==2
                bins=rec["bins"];assert all(bins[k]==0 for k in (1,2,3,5,6,7))
                assert (bins[0]-bins[4])**2==dots[x][j]**2,(case,pair,rec)
                actual.append((x,j))
            planned=[];witness=None
            for i in reps:
                x=xs[i]
                for j,d in enumerate(dots[x]):
                    planned.append((x,j))
                    if d*d==4:break
                else:
                    witness=x;break
            assert actual==planned,(case,actual,planned)
            assert row["native"]["witness"]==("None" if witness is None else f"Some({witness})")
            rss=(folder/"resource.txt").read_text().split()
            row.update(period=period,route=route,bad=bad,wall_s=elapsed,reps=reps,certs=certs,pairs=pairs,
                initial_ir_sha256=hashlib.sha256((folder/"base.initial.txt").read_bytes()).hexdigest(),
                rss_kib=int(rss[-1]))
            rows.append(row);print("AQ_SS2_ARM "+json.dumps(row),flush=True)
        for case in (list(CASES) if period==0 else list(reversed(CASES))):
            for route in (("full","orbit") if period==0 else ("orbit","full")):arm(case,route)
        arm("ss2-positive","orbit",True)
    for period in range(2):
        for case in CASES:
            a,b=[next(r for r in rows if r["period"]==period and r["case"]==case and r["route"]==route and not r["bad"]) for route in ("full","orbit")]
            assert a["initial_ir_sha256"]==b["initial_ir_sha256"]
    assert len(rows)==22
    (out/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
    print("AQ_SS2_SUMMARY "+json.dumps(dict(arms=len(rows),definite=sum(r["verdict"]!="UNKNOWN" for r in rows))),flush=True)

if __name__=="__main__":
    if sys.argv[1]=="--worker":worker(pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]),sys.argv[4],pathlib.Path(sys.argv[5]))
    else:main()

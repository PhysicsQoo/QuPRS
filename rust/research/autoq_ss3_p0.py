#!/usr/bin/env python3
"""SS3: independent exact cyclotomic overlap oracle; typed synthetic states."""
import hashlib,json,os,pathlib,re,subprocess,sys,time
import autoq_c3_pilot as c3

CASES={"ss3-positive":"PROVED","ss3-relative":"REFUTED","ss3-late-negative":"REFUTED",
       "ss3-nonclosed":"REFUTED","ss3-unknown-recover":"PROVED",
       "ss3-unknown-unresolved":"UNKNOWN","ss3-unknown-late-refute":"REFUTED"}
FAULTS={"ss3-unknown-recover":(0,0),"ss3-unknown-unresolved":(0,2),"ss3-unknown-late-refute":(0,0)}

def power(k):
    v=[0]*4;v[k%4]=1 if k%8<4 else -1;return v

def norm(v):
    a,b,c,d=v
    return a*a+b*b+c*c+d*d,a*b+b*c+c*d-a*d

def oracle(case):
    a=[(0,1),(1,1),(0,0),(1,0)]
    b=[(0,0),(1,0),(0,2),(1,2)]
    if case=="ss3-relative":b[2]=(0,3);b[3]=(1,3)
    if case in ("ss3-late-negative","ss3-unknown-late-refute"):b=b[2:]
    if case=="ss3-nonclosed":del b[3]
    dots={}
    for i,(s,k) in enumerate(a):
        for j,(t,l) in enumerate(b):
            # <b|T|a> directly, without constructing the inverse circuit.
            h=int(k!=0)+int(l!=0)
            v=[0]*4
            if s==t:
                v=power(0)
                if k and l:
                    phase={1:0,2:1,3:7}[l]
                    v=[x+y for x,y in zip(v,power(1-phase))]
            dots[i,j]=(*norm(v),h)
    return a,b,dots

def worker(binary,solver,case,folder):
    c3.CASES.update(CASES)
    os.environ["AQ_C3_NATIVE_TEST"]="exact_property_cnf::hoare_autoq_ss3_arm"
    c3.arm(binary,solver,case,"wmc",folder)

def main():
    binary,solver,out=map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:4])
    out.mkdir(parents=True,exist_ok=False);rows=[]
    for period in range(2):
        def arm(case,route,bad=False):
            folder=out/f"{period}-{case}-{route}{'-bad' if bad else ''}";folder.mkdir()
            env=dict(os.environ,AQ_SHARED_FAMILY=route)
            for k in ("AQ_CPS_ORBIT_BAD","AQ_SS3_FAULT"):env.pop(k,None)
            if bad:env["AQ_CPS_ORBIT_BAD"]="1"
            if case in FAULTS:env["AQ_SS3_FAULT"]=":".join(map(str,FAULTS[case]))
            t=time.monotonic()
            p=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(folder/"resource.txt"),
                "timeout","--kill-after=1s","4",sys.executable,str(pathlib.Path(__file__).resolve()),
                "--worker",str(binary),str(solver),case,str(folder)],env=env,capture_output=True,text=True)
            elapsed=time.monotonic()-t
            (folder/"worker.stdout").write_text(p.stdout);(folder/"worker.stderr").write_text(p.stderr)
            assert p.returncode==0,(case,route,p.returncode,p.stderr,p.stdout)
            row=json.loads(p.stdout);assert row["verdict"]==CASES[case],row
            lines=(folder/"native.log").read_text().splitlines()
            route_line=next(l for l in lines if "AQ_SS3_ROUTE " in l)
            reps=json.loads(re.search(r"indices=(\[[0-9, ]*\])",route_line)[1])
            expected=[0,2] if route=="orbit" and not bad and case!="ss3-nonclosed" else [0,1,2,3]
            assert reps==expected,(case,route,reps)
            certs=[l for l in lines if "AQ_SS3_CERT " in l]
            if route=="orbit" and case!="ss3-nonclosed":
                assert len(certs)==1 and ("exact=true" in certs[0])== (not bad)
                if bad:assert "status=not_equivalent" in certs[0]
            pairs=[dict(kv.split("=") for kv in l.split("AQ_SS3_PAIR ",1)[1].split()) for l in lines if "AQ_SS3_PAIR " in l]
            records=[json.loads(l) for l in (folder/"solver.jsonl").read_text().splitlines()]
            assert len(pairs)==len(records)==row["queries"]
            a,b,dots=oracle(case);actual=[]
            for pair,rec in zip(pairs,records):
                i,j=int(pair["input"]),int(pair["target"])
                assert rec["status"]=="EXACT"
                bins=rec["bins"];v=[bins[k]-bins[k+4] for k in range(4)]
                real,rad=norm(v);e,f,h=dots[i,j];k=int(pair["k"])
                assert real*(1<<h)==e*(1<<k) and rad*(1<<h)==f*(1<<k),(case,pair,rec)
                actual.append((i,j))
            planned=[];witness=None;any_unknown=False
            for i in reps:
                unknown=False;matched=False
                for j in range(len(b)):
                    planned.append((i,j))
                    if FAULTS.get(case)==(i,j):unknown=True;continue
                    e,f,h=dots[i,j]
                    if f==0 and e==1<<h:matched=True;break
                if not matched:
                    if unknown:any_unknown=True
                    else:witness=i;break
            verdict="REFUTED" if witness is not None else "UNKNOWN" if any_unknown else "PROVED"
            assert actual==planned and verdict==row["verdict"],(case,actual,planned)
            assert row["native"]["witness"]==("None" if witness is None else f"Some({witness})")
            injections=[l for l in lines if "AQ_SS3_INJECT " in l]
            assert len(injections)==int(case in FAULTS),injections
            rss=(folder/"resource.txt").read_text().split()
            row.update(period=period,route=route,bad=bad,wall_s=elapsed,reps=reps,certs=certs,pairs=pairs,injections=injections,
                initial_ir_sha256=hashlib.sha256((folder/"base.initial.txt").read_bytes()).hexdigest(),rss_kib=int(rss[-1]))
            rows.append(row);print("AQ_SS3_ARM "+json.dumps(row),flush=True)
        for case in (list(CASES) if period==0 else list(reversed(CASES))):
            for route in (("full","orbit") if period==0 else ("orbit","full")):arm(case,route)
        arm("ss3-positive","orbit",True)
    for period in range(2):
        for case in CASES:
            a,b=[next(r for r in rows if r["period"]==period and r["case"]==case and r["route"]==route and not r["bad"]) for route in ("full","orbit")]
            assert a["initial_ir_sha256"]==b["initial_ir_sha256"]
    assert len(rows)==30
    (out/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
    print("AQ_SS3_SUMMARY "+json.dumps(dict(arms=len(rows),definite=sum(r["verdict"]!="UNKNOWN" for r in rows),expected_unknown=sum(r["verdict"]=="UNKNOWN" for r in rows))),flush=True)

if __name__=="__main__":
    if sys.argv[1]=="--worker":worker(pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]),sys.argv[4],pathlib.Path(sys.argv[5]))
    else:main()

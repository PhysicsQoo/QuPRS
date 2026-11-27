#!/usr/bin/env python3
"""CORE-9b screening: exact same worker, source files and GPMC.
Two reversed periods, all 4 modes per representation, 4s process cap.
Not a general performance acceptance or full-bin equality across representations.
"""
import json
import os
import pathlib
import re
import statistics
import subprocess
import sys
import time
from fractions import Fraction
from autoq_decision_pair import PIN, blob
from cps_core_matched_p0 import CAP, sha, timeout_row

SOURCE_BLOBS={
    "MOGrover/05":("80afcc4cf62924cfc51b30a9acf6f22b21f70853","3ee12b92926da432290b0abd44106ad891e36304","bb7399ca0341c60457a741540fdb595ea022f375"),
    "Grover/04":("3cb06685b906e4a7da6adab65bd6b472370fe800","c5a97b5c984fb0ea92bfaa624ee41fccf875ece6","2493f92a4ae9b335b30b86d5d17aa70902402b13"),
    "MOGrover/04":("2b1c53ee628ef52edeeb09bf0dc70f1d601f968c","5e63ffba67c329e6fcb14693122c35cd0f004728","56e26972835eb604ee7ffd005ae0f10cdd081697"),
}

def main(binary,solver,root,out,case="MOGrover/05"):
    out.mkdir(parents=True,exist_ok=False)
    assert subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()==PIN
    family,width=case.split("/")
    width=int(width)
    source=root/"benchmarks/all"/case
    pre,post,qasm=[(source/f).read_bytes() for f in ("pre.hsl","post.hsl","circuit.qasm")]
    assert tuple(map(blob,(pre,post,qasm)))==SOURCE_BLOBS[case]
    hi,k=map(int,re.search(rb"aH := (\d+) / \(sqrt2 \^ (\d+)\)",post).groups())
    lo,kl=map(int,re.search(rb"aL := -(\d+) / \(sqrt2 \^ (\d+)\)",post).groups())
    assert k==kl and hi*hi+((1<<width)-1)*lo*lo==1<<k
    label=width if family=="MOGrover" else 0
    h=str(hi).encode();l=str(lo).encode()
    assert post.count(b"aH := "+h+b" /")==post.count(b"aL := -"+l+b" /")==1
    relative=post.replace(b"aH := "+h+b" /",b"aH := -"+h+b" /")
    global_=relative.replace(b"aL := -"+l+b" /",b"aL := "+l+b" /")
    assert len({post,relative,global_})==3
    fixtures=(("source",post),("relative",relative),("global",global_))
    modes=("wmc","hybrid","wmc-dag","hybrid-dag")
    routes=("baseline","selector")
    # Adjacent A/B pairs, alternating orientation; reverse the full
    # schedule on period 1. No adaptive stopping on expected outcomes.
    schedule=[(mode,route) for i,mode in enumerate(modes) for route in (routes if i%2==0 else routes[::-1])]
    worker=pathlib.Path(__file__).with_name("cps_core_matched_p0.py").resolve()
    rows=[]
    for period in range(2):
        for variant,target in (fixtures if period==0 else fixtures[::-1]):
            expected="REFUTED" if variant=="relative" else "PROVED"
            mass=Fraction((1<<k)-2*hi**2,1<<k)**2*(1<<label) if variant=="relative" else Fraction(1<<label)
            for mode,route in (schedule if period==0 else schedule[::-1]):
                folder=out/f"{period}-{variant}-{mode}-{route}"
                folder.mkdir()
                for name,data in zip(("pre.hsl","post.hsl","circuit.qasm"),(pre,target,qasm)):
                    (folder/name).write_bytes(data)
                env=dict(os.environ,CPS_CORE_SOURCE_VARIANT=route)
                args=[sys.executable,str(worker),"--worker",str(binary),str(solver),str(folder),mode]
                start=time.monotonic()
                p=subprocess.run(["/usr/bin/time","-f","%M","-o",str(folder/"resource.txt"),"timeout","--kill-after=1s",str(CAP),*args],env=env,capture_output=True,text=True,errors="replace")
                wall=time.monotonic()-start
                (folder/"stdout").write_text(p.stdout);(folder/"stderr").write_text(p.stderr)
                if p.returncode in (124,137):
                    row=timeout_row(folder,mode)
                else:
                    assert p.returncode==0,(variant,mode,route,p.stdout,p.stderr)
                    row=json.loads(p.stdout)
                assert row["reason"] not in ("NATIVE_ERROR","INVALID_COUNT","SOLVER_ERROR","SOLVER_LAUNCH_ERROR"),row
                resource=(folder/"resource.txt").read_text().split()
                row.update(case=case,period=period,variant=variant,mode=mode,route=route,expected=expected,
                           wall_s=wall,returncode=p.returncode,
                           max_individual_rss_kib=int(resource[-1]) if resource and resource[-1].isdigit() else None,
                           inputs_sha256=[sha(folder/f) for f in ("pre.hsl","post.hsl","circuit.qasm")])
                assert row["verdict"] in ("UNKNOWN",expected),row
                if row.get("norm") is not None:assert row["norm"]==[str(mass),"0"],row
                rows.append(row)
                print("CPS_CORE9_AB_ARM",json.dumps(row),flush=True)
    assert len(rows)==48
    for variant,_ in fixtures:
        g=[r for r in rows if r["variant"]==variant]
        assert len({tuple(r["inputs_sha256"]) for r in g})==1
        for route in routes:
            h=[r for r in g if r["route"]==route]
            assert len({r["initial_sha256"] for r in h if "initial_sha256" in r})==1,h
            for period in range(2):
                by={r["mode"]:r for r in h if r["period"]==period}
                for flat,dag in (("wmc","wmc-dag"),("hybrid","hybrid-dag")):
                    a,b=by[flat],by[dag]
                    if a.get("primary",0)>0 and b.get("primary",0)>0:
                        assert all(a.get(x)==b.get(x) for x in ("initial_sha256","n","k","h","steps","primary")),(a,b)
                    if a["verdict"]!="UNKNOWN" and b["verdict"]!="UNKNOWN":
                        assert all(a.get(x)==b.get(x) for x in ("verdict","bins","norm")),(a,b)
        # Across representations compare normalized values, not raw phase
        # bins: the additional unique selector may change the phase bins.
        norms={tuple(r["norm"]) for r in g if r.get("norm") is not None}
        assert len(norms)<=1,g
    summary=[]
    for variant,_ in fixtures:
        for mode in modes:
            for route in routes:
                g=[r for r in rows if (r["variant"],r["mode"],r["route"])==(variant,mode,route)]
                definite=[r for r in g if r["verdict"]!="UNKNOWN"]
                summary.append(dict(case=case,variant=variant,mode=mode,route=route,definite=len(definite),runs=len(g),
                    median_wall_all_s=statistics.median(r["wall_s"] for r in g),
                    median_wall_definite_s=statistics.median(r["wall_s"] for r in definite) if len(definite)==2 else None,
                    median_rss_kib=statistics.median(r["max_individual_rss_kib"] for r in g) if all(r["max_individual_rss_kib"] is not None for r in g) else None,
                    reasons=[r["reason"] for r in g],primary=[r.get("primary") for r in g],
                    clauses=[r.get("clauses") for r in g],encode_ns=[r.get("encode_ns") for r in g],
                    solver_s=[r.get("solver_s") for r in g]))
    # Compare each selector arm to its same-period baseline. Report losses
    # without suppressing the rest of the screening or promoting selector.
    pairs=[]
    for variant,_ in fixtures:
        for mode in modes:
            for period in range(2):
                pair={r["route"]:r for r in rows if (r["variant"],r["mode"],r["period"])==(variant,mode,period)}
                a,b=pair["baseline"],pair["selector"]
                outcome="LOSS" if a["verdict"]!="UNKNOWN" and b["verdict"]=="UNKNOWN" else "GAIN" if a["verdict"]=="UNKNOWN" and b["verdict"]!="UNKNOWN" else "BOTH_DEFINITE" if a["verdict"]!="UNKNOWN" else "BOTH_UNKNOWN"
                pairs.append(dict(case=case,variant=variant,mode=mode,period=period,outcome=outcome,
                    wall_ratio=b["wall_s"]/a["wall_s"] if outcome=="BOTH_DEFINITE" else None))
    (out/"summary.json").write_text(json.dumps(dict(case=case,source_pin=PIN,binary_sha256=sha(binary),solver_sha256=sha(solver),cap_s=CAP,rows=rows,summary=summary,pairs=pairs),indent=2)+"\n")
    for r in summary:print("CPS_CORE9_AB_MEDIAN",json.dumps(r),flush=True)
    print("CPS_CORE9_AB_SUMMARY",json.dumps(dict(arms=len(rows),periods=2,case=case,**{r:sum(x["verdict"]!="UNKNOWN" for x in rows if x["route"]==r) for r in routes})),flush=True)
    print("CPS_CORE9_FAMILY_PAIRS",json.dumps(dict(case=case,**{k:sum(r["outcome"]==k for r in pairs) for k in ("LOSS","GAIN","BOTH_DEFINITE","BOTH_UNKNOWN")})),flush=True)

if __name__=="__main__":
    main(*map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:5]),*sys.argv[5:])

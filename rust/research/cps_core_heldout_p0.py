#!/usr/bin/env python3
"""Source-pinned 04/05 held-out admission and decision pilot.
No new limits, source-family specializations or timed reference enumeration.
One screening pass; not a replicated performance acceptance."""
import collections
import json
import pathlib
import re
import subprocess
import sys
import time
from fractions import Fraction
from autoq_decision_pair import PIN, blob, classify
from cps_core_matched_p0 import MODES, ORDERS, CAP, sha

BLOBS={
 "BV/04":("9c369a362f5e504cd5d4cc64b4b5297a06661b42","2a659d2eaafbfd088cf1b778bc36b960db02286a","91e76da5257e307f92c4ff980ebecc19bc1aef2c"),
 "BV/05":("37090f21884bddadf92603520e847c444eb2b9a6","436231c7a3262f9e2f90efa3d0558eee2e97ffa3","d2358604891fc8b015e0a2a0cf72491e0dac61b1"),
 "Grover/04":("3cb06685b906e4a7da6adab65bd6b472370fe800","c5a97b5c984fb0ea92bfaa624ee41fccf875ece6","2493f92a4ae9b335b30b86d5d17aa70902402b13"),
 "Grover/05":("ee88ac0dfde3f1a971a52493a9231293064fc45f","7323f2705a642f080ae6eeecdb26eb3494fcb21d","a190bac26a13ed2b1f3dbbaec7c3f95ff806ff00"),
 "MOGrover/04":("2b1c53ee628ef52edeeb09bf0dc70f1d601f968c","5e63ffba67c329e6fcb14693122c35cd0f004728","56e26972835eb604ee7ffd005ae0f10cdd081697"),
 "MOGrover/05":("80afcc4cf62924cfc51b30a9acf6f22b21f70853","3ee12b92926da432290b0abd44106ad891e36304","bb7399ca0341c60457a741540fdb595ea022f375"),
}
binary,solver,autoq,root,out=map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:6])
out.mkdir(parents=True,exist_ok=False)
assert subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()==PIN
version=subprocess.run([str(autoq),"-v"],capture_output=True,text=True,check=True)
assert PIN in version.stdout+version.stderr
worker=pathlib.Path(__file__).with_name("cps_core_matched_p0.py").resolve()
records=[]
for ci,(case,hashes) in enumerate(BLOBS.items()):
    family,width=case.split("/")
    width=int(width)
    source=root/"benchmarks"/"all"/case
    pre,post,qasm=[(source/f).read_bytes() for f in ("pre.hsl","post.hsl","circuit.qasm")]
    assert tuple(map(blob,(pre,post,qasm)))==hashes
    q=int(re.search(rb"qreg qubits\[(\d+)\];",qasm).group(1))
    gates=len([line for line in qasm.splitlines() if line.strip() and not line.startswith((b"OPENQASM",b"include",b"qreg",b"//"))])
    h=sum(line.startswith(b"h ") for line in qasm.splitlines())
    assert (q,h)=={"BV":(width+1,2*(width+1)),"Grover":(2*width-1,{4:30,5:47}[width]),"MOGrover":(3*width-1,{4:30,5:47}[width])}[family]
    label=width if family=="MOGrover" else 0
    if family=="BV":
        fixed=re.search(rb"\|([01]+)>",post).group(1)
        flipped=(b"0" if fixed[:1]==b"1" else b"1")+fixed[1:]
        relative=post.replace(b"|"+fixed+b">",b"|"+flipped+b">")
        global_=post.replace(b"c1 := 1\n",b"c1 := -1\n")
        bad_mass=Fraction(0)
        k=0
    else:
        ma=re.search(rb"aH := (\d+) / \(sqrt2 \^ (\d+)\)",post)
        ml=re.search(rb"aL := -(\d+) / \(sqrt2 \^ (\d+)\)",post)
        hi,k=map(int,ma.groups());lo,kl=map(int,ml.groups())
        assert k==kl and hi*hi+((1<<width)-1)*lo*lo==(1<<k)
        relative=post.replace(b"aH := "+str(hi).encode()+b" /",b"aH := -"+str(hi).encode()+b" /")
        global_=relative.replace(b"aL := -"+str(lo).encode()+b" /",b"aL := "+str(lo).encode()+b" /")
        bad_mass=Fraction((1<<k)-2*hi*hi,1<<k)**2*(1<<label)
    assert len({post,relative,global_})==3
    print("CPS_HELDOUT_SOURCE",json.dumps(dict(case=case,qubits=q,gates=gates,hadamard=h,free=label,post_scale=k,blobs=hashes)),flush=True)
    for vi,(variant,target) in enumerate((("source",post),("relative",relative),("global",global_))):
        expected="REFUTED" if variant=="relative" else "PROVED"
        mass=bad_mass if variant=="relative" else Fraction(1<<label)
        group=[]
        for mi in ORDERS[(ci+vi)%len(ORDERS)]:
            mode=MODES[mi]
            folder=out/f"{family.lower()}{width:02d}-{variant}-{mode}";folder.mkdir()
            for name,data in zip(("pre.hsl","post.hsl","circuit.qasm"),(pre,target,qasm)):
                (folder/name).write_bytes(data)
            args=[str(autoq),"ver",str(folder/"pre.hsl"),str(folder/"circuit.qasm"),str(folder/"post.hsl")] if mode=="autoq" else [sys.executable,str(worker),"--worker",str(binary),str(solver),str(folder),mode]
            t=time.monotonic()
            p=subprocess.run(["/usr/bin/time","-f","%M","-o",str(folder/"resource.txt"),"timeout","--kill-after=1s",str(CAP),*args],capture_output=True,text=True,errors="replace")
            wall=time.monotonic()-t
            (folder/"stdout").write_text(p.stdout);(folder/"stderr").write_text(p.stderr)
            if p.returncode in (124,137):
                row=dict(verdict="UNKNOWN",reason="PROCESS_TIMEOUT")
            elif mode=="autoq":
                result=classify(p.stdout,p.stderr,p.returncode,(q,gates))
                row=dict(verdict=result if result in ("PROVED","REFUTED") else "UNKNOWN",reason=result)
            elif p.returncode:
                row=dict(verdict="UNKNOWN",reason="WORKER_ERROR")
            else:
                row=json.loads(p.stdout)
            resource=(folder/"resource.txt").read_text().split()
            row.update(case=case,variant=variant,mode=mode,expected=expected,wall_s=wall,returncode=p.returncode,
                       max_individual_rss_kib=int(resource[-1]) if resource and resource[-1].isdigit() else None,
                       inputs_sha256=[sha(folder/f) for f in ("pre.hsl","post.hsl","circuit.qasm")])
            assert row["verdict"] in ("UNKNOWN",expected),row
            # Analytic mutation mass assumes the original source is valid;
            # AutoQ is an independent verdict comparator. Not a dense oracle.
            if row.get("norm") is not None:assert row["norm"]==[str(mass),"0"],row
            group.append(row);records.append(row)
            print("CPS_HELDOUT_ARM",json.dumps(row),flush=True)
        assert len({tuple(r["inputs_sha256"]) for r in group})==1
        assert len({r["initial_sha256"] for r in group if "initial_sha256" in r})<=1
        by_mode={r["mode"]:r for r in group}
        for flat,dag in (("wmc","wmc-dag"),("hybrid","hybrid-dag")):
            a,b=by_mode[flat],by_mode[dag]
            if a["verdict"]!="UNKNOWN" and b["verdict"]!="UNKNOWN":
                assert a["verdict"]==b["verdict"] and all(a.get(x)==b.get(x) for x in ("n","k","h","steps","primary","bins","norm")), (a,b)
assert len(records)==108
summary={m:dict(definite=sum(r["verdict"]!="UNKNOWN" for r in records if r["mode"]==m),
                unknown=dict(collections.Counter(r.get("stage",r["reason"]) for r in records if r["mode"]==m and r["verdict"]=="UNKNOWN"))) for m in MODES}
(out/"summary.json").write_text(json.dumps(dict(source_pin=PIN,cap_s=CAP,rows=records,summary=summary,
        binary_sha256=sha(binary),solver_sha256=sha(solver),autoq_sha256=sha(autoq)),indent=2)+"\n")
print("CPS_HELDOUT_SUMMARY",json.dumps(dict(arms=len(records),cases=6,obligations=18,**summary)),flush=True)

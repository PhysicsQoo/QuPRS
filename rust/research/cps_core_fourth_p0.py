#!/usr/bin/env python3
"""CORE-10e: larger original GHZall and non-Clifford phase-spread
controls, retaining HXH and rectangular MCToffoli. Same CPS worker.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from autoq_decision_pair import PIN, blob, classify
from cps_core_matched_p0 import CAP, MODES, ORDERS, sha, timeout_row

BLOBS={
 "HXH/04":("83b60a66b5c5b088352cb79f8a55cc065cf2b3ff","c74ba40a77d0835e000e5fd46075ddbad494c1c4","a7aeeb45e48022fe0ede048158bb2676d7a99f6b"),
 "HXH/08":("d96edf2a4c9ab89da44595aa0909d7a72a355d8e","2daacef1a0c69085b7d7e3ab8f62d91c0b98dbda","2879b5bc988622cb692b95c3760b67db992cb8ed"),
 "MCToffoli/04":("86d326ab0789be196096b0a350c2f6a371a6160c","86d326ab0789be196096b0a350c2f6a371a6160c","1a01f82a593b9ab2cda7eb2067edc3ea79071b3a"),
 "GHZall/002":("0e19fc95f7ab5034100479d55239359943b67a06","89275fcde577eba3f0579c5a72c9d80db2f8b1e0","a3651711eaf5a6440c3ee0c2aa049236bcebe838"),
 "GHZall/004":("f735cf6987e054b53d2682edb43abb00463182e9","b47769284fba9e93c8de087848c2b5188a418235","34b355874a3658e45307c44529473a93258e5bd3"),
 "GHZall/008":("a712713768d9605514ff30208785b5bfdbffad06","7a2693425da63470feca65ca62d93e9d19d3a461","f2c88eaf5779c0bd340a501514432290369fdf7f"),
 "GHZall/012":("62415f766e476bf3cd2118270dc41edd7eb3943c","cc32b5ec1b00cbdc8b28f2b70d0589bcd4eef081","2a571c1ca0b5a18e86e6cc1d7eecdb4638e8869b"),
 "GHZall/016":("65b297e71a5df283ebb3ebf7fb1c4b55abe3b706","964c158acda2746f2d3d637c4be0139a3ec32ebe","f182c4d9f0c3c09b60b1576b6d4c5145d30703e6"),
}
def main(binary,solver,autoq,root,out):
    out.mkdir(parents=True,exist_ok=False)
    assert subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()==PIN
    v=subprocess.run([str(autoq),"-v"],capture_output=True,text=True,check=True)
    assert PIN in v.stdout+v.stderr
    worker=pathlib.Path(__file__).with_name("cps_core_matched_p0.py").resolve()
    rows=[]
    for ci,(case,hashes) in enumerate(BLOBS.items()):
        width=int(case.split("/")[1])
        pre,post,qasm=[(root/"benchmarks/all"/case/f).read_bytes() for f in ("pre.hsl","post.hsl","circuit.qasm")]
        assert tuple(map(blob,(pre,post,qasm)))==hashes
        q=int(re.search(rb"qreg qubits\[(\d+)\];",qasm).group(1))
        if case.startswith("HXH"):
            assert q==width
            fixtures=[
                ("source",pre,post,qasm,width,width,1<<width,3*width),
                ("spread",pre,post,qasm.rstrip()+b"\nh qubits[0];\n",width,width,1<<(width-1),3*width+1)]
        elif case.startswith("GHZall"):
            assert q==width
            # H on the first output sends a cat basis ray into an
            # equal superposition of two different cat rays (q>=2).
            fixtures=[
                ("source",pre,post,qasm,width,width,1<<width,width),
                ("spread",pre,post,qasm.rstrip()+b"\nh qubits[0];\n",width,width,1<<(width-1),width+1)]
            if width>=8:
                # T on the first output preserves each two-dimensional
                # cat subspace but mixes the two opposite-sign rays.
                # p+/-=(1 +/- 1/sqrt(2))/2, sum p^2=3/4 exactly.
                fixtures.append(("phase-spread",pre,post,qasm.rstrip()+b"\nt qubits[0];\n",width,width,3*(1<<(width-2)),width+1))
        else:
            assert q==8 and width==4 and pre==post
            assert pre.count(b"|i000j>")==pre.count(b", |j|=1")==1
            fixed=pre.replace(b"|i000j>",b"|i0000>").replace(b", |j|=1",b"")
            # Source-derived controls: target bit fixed at zero vs free.
            # MCToffoli toggles it only for all-one controls.
            fixtures=[
                ("expand",fixed,post,qasm,4,5,16,7),
                ("restrict",pre,fixed,qasm,5,4,16,7),
                ("partial",fixed,fixed,qasm,4,4,15,7)]
        for vi,(variant,src,target,circuit,n,out_n,mass,gates) in enumerate(fixtures):
            expected="PROVED" if mass==1<<n else "REFUTED"
            group=[]
            for mi in ORDERS[(ci+vi)%len(ORDERS)]:
                mode=MODES[mi]
                folder=out/(case.replace("/","-")+"-"+variant+"-"+mode);folder.mkdir()
                for name,data in zip(("pre.hsl","post.hsl","circuit.qasm"),(src,target,circuit)):
                    (folder/name).write_bytes(data)
                args=[str(autoq),"ver",str(folder/"pre.hsl"),str(folder/"circuit.qasm"),str(folder/"post.hsl")] if mode=="autoq" else [sys.executable,str(worker),"--worker",str(binary),str(solver),str(folder),mode]
                start=time.monotonic()
                p=subprocess.run(["/usr/bin/time","-f","%M","-o",str(folder/"resource.txt"),"timeout","--kill-after=1s",str(CAP),*args],
                    env=dict(os.environ,CPS_CORE_SOURCE_VARIANT="basis-fourth"),capture_output=True,text=True,errors="replace")
                wall=time.monotonic()-start
                (folder/"stdout").write_text(p.stdout);(folder/"stderr").write_text(p.stderr)
                if p.returncode in (124,137):row=timeout_row(folder,mode)
                elif mode=="autoq":
                    result=classify(p.stdout,p.stderr,p.returncode,(q,gates))
                    row=dict(verdict=result if result in ("PROVED","REFUTED") else "UNKNOWN",reason=result)
                else:
                    assert p.returncode==0,(case,variant,mode,p.stdout,p.stderr)
                    row=json.loads(p.stdout)
                assert row["verdict"] in ("UNKNOWN",expected),row
                assert row["reason"] not in ("NATIVE_ERROR","INVALID_COUNT","SOLVER_ERROR","SOLVER_LAUNCH_ERROR"),row
                if row.get("norm") is not None:assert row["norm"]==[str(mass),"0"],row
                resource=(folder/"resource.txt").read_text().split()
                row.update(case=case,variant=variant,mode=mode,labels=n,output_labels=out_n,expected=expected,expected_fourth_mass=mass,wall_s=wall,
                    max_individual_rss_kib=int(resource[-1]) if resource and resource[-1].isdigit() else None,
                    returncode=p.returncode,inputs_sha256=[sha(folder/f) for f in ("pre.hsl","post.hsl","circuit.qasm")])
                group.append(row);rows.append(row)
                print("CPS_CORE10_FOURTH_ARM",json.dumps(row),flush=True)
            assert len({tuple(r["inputs_sha256"]) for r in group})==1
            assert len({r["initial_sha256"] for r in group if "initial_sha256" in r})<=1
            by={r["mode"]:r for r in group}
            for flat,dag in (("wmc","wmc-dag"),("hybrid","hybrid-dag")):
                a,b=by[flat],by[dag]
                if a.get("primary",0)>0 and b.get("primary",0)>0:
                    assert all(a.get(x)==b.get(x) for x in ("initial_sha256","n","k","h","steps","primary")),(a,b)
                if a["verdict"]!="UNKNOWN" and b["verdict"]!="UNKNOWN":
                    assert all(a.get(x)==b.get(x) for x in ("verdict","norm","bins")),(a,b)
    assert len(rows)==120
    # Preserve previously definite native results; new cases are a
    # screening cohort, not an assumption that all policies terminate.
    for r in rows:
        if r["case"].startswith("HXH") and r["mode"] in ("hybrid","wmc-dag","hybrid-dag","autoq"):
            assert r["verdict"]==r["expected"],r
        if r["case"]=="MCToffoli/04":
            assert r["verdict"]==r["expected"],r
        # Preserve the observed CORE-10d definite routes (not new phase
        # controls). New widths are measured without assuming completion.
        if r["case"] in ("GHZall/002","GHZall/004","GHZall/008") and r["variant"] in ("source","spread"):
            if r["mode"]!="rr" or r["variant"]=="source":
                assert r["verdict"]==r["expected"],r
            if r["variant"]=="source" and r["mode"] in ("rr","hybrid","hybrid-dag"):
                assert r["h"]==r["k"]==0 and r["steps"]==2 and not r["solver_invoked"],r
    summary={case:{m:sum(r["case"]==case and r["mode"]==m and r["verdict"]!="UNKNOWN" for r in rows) for m in MODES} for case in BLOBS}
    (out/"summary.json").write_text(json.dumps(dict(source_pin=PIN,binary_sha256=sha(binary),solver_sha256=sha(solver),autoq_sha256=sha(autoq),cap_s=CAP,rows=rows,summary=summary),indent=2)+"\n")
    print("CPS_CORE10_FOURTH_SUMMARY",json.dumps(dict(arms=len(rows),cases=8,summary=summary)),flush=True)

if __name__=="__main__":
    main(*map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:6]))

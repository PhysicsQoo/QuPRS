#!/usr/bin/env python3
"""CORE-10b fourth-moment membership: original HXH and appended H control.
No label-fibre assumption. Same CPS worker and norm transport.
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
}
def main(binary,solver,autoq,root,out):
    out.mkdir(parents=True,exist_ok=False)
    assert subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()==PIN
    v=subprocess.run([str(autoq),"-v"],capture_output=True,text=True,check=True)
    assert PIN in v.stdout+v.stderr
    worker=pathlib.Path(__file__).with_name("cps_core_matched_p0.py").resolve()
    rows=[]
    for ci,(case,hashes) in enumerate(BLOBS.items()):
        n=int(case.split("/")[1])
        pre,post,qasm=[(root/"benchmarks/all"/case/f).read_bytes() for f in ("pre.hsl","post.hsl","circuit.qasm")]
        assert tuple(map(blob,(pre,post,qasm)))==hashes
        assert int(re.search(rb"qreg qubits\[(\d+)\];",qasm).group(1))==n
        # Control is full-span-preserving but maps every basis ray to
        # a two-term superposition. Expected fourth mass exactly N/2.
        for vi,(variant,circuit) in enumerate((("source",qasm),("spread",qasm.rstrip()+b"\nh qubits[0];\n"))):
            expected="PROVED" if variant=="source" else "REFUTED"
            mass=1<<(n-(variant=="spread"))
            group=[]
            for mi in ORDERS[(ci+vi)%len(ORDERS)]:
                mode=MODES[mi]
                folder=out/(case.replace("/","-")+"-"+variant+"-"+mode);folder.mkdir()
                for name,data in zip(("pre.hsl","post.hsl","circuit.qasm"),(pre,post,circuit)):
                    (folder/name).write_bytes(data)
                args=[str(autoq),"ver",str(folder/"pre.hsl"),str(folder/"circuit.qasm"),str(folder/"post.hsl")] if mode=="autoq" else [sys.executable,str(worker),"--worker",str(binary),str(solver),str(folder),mode]
                start=time.monotonic()
                p=subprocess.run(["/usr/bin/time","-f","%M","-o",str(folder/"resource.txt"),"timeout","--kill-after=1s",str(CAP),*args],
                    env=dict(os.environ,CPS_CORE_SOURCE_VARIANT="basis-fourth"),capture_output=True,text=True,errors="replace")
                wall=time.monotonic()-start
                (folder/"stdout").write_text(p.stdout);(folder/"stderr").write_text(p.stderr)
                if p.returncode in (124,137):row=timeout_row(folder,mode)
                elif mode=="autoq":
                    result=classify(p.stdout,p.stderr,p.returncode,(n,3*n+(variant=="spread")))
                    row=dict(verdict=result if result in ("PROVED","REFUTED") else "UNKNOWN",reason=result)
                else:
                    assert p.returncode==0,(case,variant,mode,p.stdout,p.stderr)
                    row=json.loads(p.stdout)
                assert row["verdict"] in ("UNKNOWN",expected),row
                assert row["reason"] not in ("NATIVE_ERROR","INVALID_COUNT","SOLVER_ERROR","SOLVER_LAUNCH_ERROR"),row
                if row.get("norm") is not None:assert row["norm"]==[str(mass),"0"],row
                resource=(folder/"resource.txt").read_text().split()
                row.update(case=case,variant=variant,mode=mode,labels=n,expected=expected,expected_fourth_mass=mass,wall_s=wall,
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
    assert len(rows)==24
    summary={case:{m:sum(r["case"]==case and r["mode"]==m and r["verdict"]!="UNKNOWN" for r in rows) for m in MODES} for case in BLOBS}
    (out/"summary.json").write_text(json.dumps(dict(source_pin=PIN,binary_sha256=sha(binary),solver_sha256=sha(solver),autoq_sha256=sha(autoq),cap_s=CAP,rows=rows,summary=summary),indent=2)+"\n")
    print("CPS_CORE10_FOURTH_SUMMARY",json.dumps(dict(arms=len(rows),cases=2,summary=summary)),flush=True)

if __name__=="__main__":
    main(*map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:6]))

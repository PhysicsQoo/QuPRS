#!/usr/bin/env python3
"""CORE-10a source-pinned StateSet inclusion pilot, one screening pass.
Existing matched worker + exact norm, independent AutoQ verdict.
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
 "MCToffoli/04":("86d326ab0789be196096b0a350c2f6a371a6160c","86d326ab0789be196096b0a350c2f6a371a6160c","1a01f82a593b9ab2cda7eb2067edc3ea79071b3a"),
 "MCToffoli/08":("6718339712efc46088280b376b33eea3e61888a9","6718339712efc46088280b376b33eea3e61888a9","fb85adab87e7ee799ea915b8f7acfd0c6f47c7f7"),
 "MOBV_reorder/04":("901a2b6196275d14b38eba0dd99d83fa05533201","2d356d0ddc17477d521c0f0067391cba12dab60f","9287d282a718d1799c46651215c4ff464ee44345"),
 "MOBV_reorder/06":("48b4acd4c93f5371a82c9f5b64180b3bc3a48fc5","f012bd56a7d04b7ce75f6f9aca0bf3e75b6e25a5","a237dee5e3a088a0b8b698a517e6cb2e8cfbda63"),
}
def main(binary,solver,autoq,root,out):
    out.mkdir(parents=True,exist_ok=False)
    assert subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()==PIN
    v=subprocess.run([str(autoq),"-v"],capture_output=True,text=True,check=True)
    assert PIN in v.stdout+v.stderr
    worker=pathlib.Path(__file__).with_name("cps_core_matched_p0.py").resolve()
    rows=[]
    for ci,(case,hashes) in enumerate(BLOBS.items()):
        family,width=case.split("/");width=int(width)
        pre,post,qasm=[(root/"benchmarks/all"/case/f).read_bytes() for f in ("pre.hsl","post.hsl","circuit.qasm")]
        assert tuple(map(blob,(pre,post,qasm)))==hashes
        labels=width+(family=="MCToffoli")
        q=int(re.search(rb"qreg qubits\[(\d+)\];",qasm).group(1))
        gates=len([line for line in qasm.splitlines() if line.strip() and not line.startswith((b"OPENQASM",b"include",b"qreg",b"//"))])
        if family=="MCToffoli":
            anchor=b"|i"+b"0"*(width-1)+b"j>"
            wrong=b"|i1"+b"0"*(width-2)+b"j>"
        else:
            anchor=b"|ii1>";wrong=b"|ii0>"
        assert post.count(anchor)==1 and post.count(b"c1 := 1")==1
        targets=(("source",post),("relative",post.replace(anchor,wrong)),("global",post.replace(b"c1 := 1",b"c1 := -1")))
        for vi,(variant,target) in enumerate(targets):
            expected="REFUTED" if variant=="relative" else "PROVED"
            group=[]
            for mi in ORDERS[(ci+vi)%len(ORDERS)]:
                mode=MODES[mi]
                folder=out/(case.replace("/","-")+"-"+variant+"-"+mode);folder.mkdir()
                for name,data in zip(("pre.hsl","post.hsl","circuit.qasm"),(pre,target,qasm)):
                    (folder/name).write_bytes(data)
                args=[str(autoq),"ver",str(folder/"pre.hsl"),str(folder/"circuit.qasm"),str(folder/"post.hsl")] if mode=="autoq" else [sys.executable,str(worker),"--worker",str(binary),str(solver),str(folder),mode]
                start=time.monotonic()
                p=subprocess.run(["/usr/bin/time","-f","%M","-o",str(folder/"resource.txt"),"timeout","--kill-after=1s",str(CAP),*args],
                    env=dict(os.environ,CPS_CORE_SOURCE_VARIANT="basis-family"),capture_output=True,text=True,errors="replace")
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
                if row.get("norm") is not None:assert row["norm"]==[str(0 if variant=="relative" else 1<<labels),"0"],row
                resource=(folder/"resource.txt").read_text().split()
                row.update(case=case,variant=variant,mode=mode,labels=labels,qubits=q,expected=expected,wall_s=wall,
                    max_individual_rss_kib=int(resource[-1]) if resource and resource[-1].isdigit() else None,
                    returncode=p.returncode,inputs_sha256=[sha(folder/f) for f in ("pre.hsl","post.hsl","circuit.qasm")])
                group.append(row);rows.append(row)
                print("CPS_CORE10_ARM",json.dumps(row),flush=True)
            assert len({tuple(r["inputs_sha256"]) for r in group})==1
            assert len({r["initial_sha256"] for r in group if "initial_sha256" in r})<=1
            by={r["mode"]:r for r in group}
            for flat,dag in (("wmc","wmc-dag"),("hybrid","hybrid-dag")):
                a,b=by[flat],by[dag]
                if a.get("primary",0)>0 and b.get("primary",0)>0:
                    assert all(a.get(x)==b.get(x) for x in ("initial_sha256","n","k","h","steps","primary")),(a,b)
                if a["verdict"]!="UNKNOWN" and b["verdict"]!="UNKNOWN":
                    assert all(a.get(x)==b.get(x) for x in ("verdict","norm","bins")),(a,b)
    assert len(rows)==72
    summary={case:{m:sum(r["case"]==case and r["mode"]==m and r["verdict"]!="UNKNOWN" for r in rows) for m in MODES} for case in BLOBS}
    (out/"summary.json").write_text(json.dumps(dict(source_pin=PIN,binary_sha256=sha(binary),solver_sha256=sha(solver),autoq_sha256=sha(autoq),cap_s=CAP,rows=rows,summary=summary),indent=2)+"\n")
    print("CPS_CORE10_SUMMARY",json.dumps(dict(arms=len(rows),cases=4,summary=summary)),flush=True)

if __name__=="__main__":
    main(*map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:6]))

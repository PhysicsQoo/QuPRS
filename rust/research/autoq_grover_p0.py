#!/usr/bin/env python3
"""Source-bound Grover extension, one-period pilot; not a speedup claim."""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import autoq_c3_pilot as c3
from autoq_decision_pair import PIN, blob, replace_once

SOURCES = {
    "grover04": (7,100,30,16,251,-13,("3cb06685b906e4a7da6adab65bd6b472370fe800","c5a97b5c984fb0ea92bfaa624ee41fccf875ece6","2493f92a4ae9b335b30b86d5d17aa70902402b13")),
    "grover05": (9,172,47,29,23161,-119,("ee88ac0dfde3f1a971a52493a9231293064fc45f","7323f2705a642f080ae6eeecdb26eb3494fcb21d","a190bac26a13ed2b1f3dbbaec7c3f95ff806ff00")),
}
VARIANTS = {"source":"PROVED","global-sign":"PROVED","relative-sign":"REFUTED","remove-cz":"REFUTED"}
CASES = {f"{f}-{v}":e for f in SOURCES for v,e in VARIANTS.items()}
MODES = ("rr","wmc","hybrid","hybrid-pre","autoq")
NAMES = ("pre.hsl","post.hsl","circuit.qasm")

def hashes(data):
    return [hashlib.sha256(d).hexdigest() for d in data]

def read_case(folder):
    return [(folder/name).read_bytes() for name in NAMES]

def oracle(data,n):
    pre,post,src = (d.decode("utf-8") for d in data)
    assert pre.strip() == f"Constants\nc1 := 1\nExtended Dirac\n{{c1 |{'0'*n}>}}"
    m = re.fullmatch(r"Constants\naH := (-?\d+) / \(sqrt2 \^ (\d+)\)\naL := (-?\d+) / \(sqrt2 \^ (\d+)\)\nExtended Dirac\n\{aH \|([01]+)> \+ aL ∑ \|i\|=(\d+), i≠([01]+) \|i([01]+)>\}",post.strip())
    assert m
    hi,k,lo,k2,marked,width,excluded,suffix = m.groups()
    hi,k,lo,k2,width = map(int,(hi,k,lo,k2,width))
    assert k==k2 and marked==excluded+suffix and len(excluded)==width and len(marked)==n
    target=[0]*(1<<n)
    for x in range(1<<width):
        bits=f"{x:0{width}b}"
        target[int((bits+suffix)[::-1],2)]=hi if bits==excluded else lo
    lines=[l.strip() for l in src.splitlines() if l.strip()]
    assert lines[:3]==["OPENQASM 2.0;",'include "qelib1.inc";',f"qreg qubits[{n}];"]
    v=[0]*(1<<n);v[0]=1;h=0
    for line in lines[3:]:
        m=re.fullmatch(r"(h|x|cx|ccx|cz) (qubits\[\d+\](?:,\s*qubits\[\d+\]){0,2});",line)
        assert m,line
        op,args=m.groups();q=list(map(int,re.findall(r"\[(\d+)\]",args)))
        assert len(q)=={"h":1,"x":1,"cx":2,"ccx":3,"cz":2}[op] and len(set(q))==len(q) and all(i<n for i in q)
        a=q[0];w=[0]*len(v)
        for z,c in enumerate(v):
            if not c: continue
            if op=="h":
                w[z&~(1<<a)]+=c;w[z|(1<<a)]+= -c if z>>a&1 else c
            elif op=="x": w[z^(1<<a)]+=c
            elif op=="cx": w[z^((1<<q[1]) if z>>a&1 else 0)]+=c
            elif op=="ccx": w[z^((1<<q[2]) if z>>a&1 and z>>q[1]&1 else 0)]+=c
            elif op=="cz": w[z]+= -c if z>>a&1 and z>>q[1]&1 else c
        h+=op=="h";v=w
    assert sum(c*c for c in v)==1<<h and sum(c*c for c in target)==1<<k
    dot=sum(a*b for a,b in zip(v,target));den=1<<(h+k)
    from fractions import Fraction
    f=Fraction(dot*dot,den)
    i=next(j for j,c in enumerate(target) if c)
    j=next((j for j in range(len(v)) if v[i]*target[j]!=v[j]*target[i]),None)
    assert (j is None)==(f==1)
    witness=None if j is None else dict(i=i,j=j,a_i=v[i],a_j=v[j],b_i=target[i],b_j=target[j],
                                         minor=v[i]*target[j]-v[j]*target[i])
    return dict(verdict="PROVED" if f==1 else "REFUTED",fidelity=str(f),h=h,k=k,
                gates=len(lines)-3,dot=dot,source_support=[i for i,c in enumerate(v) if c],
                target_support=[i for i,c in enumerate(target) if c],reference_minor=witness)

def prepare(root,out):
    assert subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()==PIN
    fixtures=out/"source";fixtures.mkdir();specs={}
    for family,(n,g,h,k,hi,lo,pins) in SOURCES.items():
        raw=read_case(root/"benchmarks"/"all"/"Grover"/family[-2:])
        assert tuple(map(blob,raw))==pins
        for variant,expected in VARIANTS.items():
            pre,post,src=raw
            if variant in ("global-sign","relative-sign"):
                post=replace_once(post,f"aH := {hi} /".encode(),f"aH := {-hi} /".encode())
            if variant=="global-sign":
                post=replace_once(post,f"aL := {lo} /".encode(),f"aL := {-lo} /".encode())
            if variant=="remove-cz":
                lines=src.splitlines(keepends=True)
                j=next(i for i,line in enumerate(lines) if line.strip().startswith(b"cz "))
                del lines[j];src=b"".join(lines)
            data=[pre,post,src];case=f"{family}-{variant}"
            ref=oracle(data,n)
            assert ref["verdict"]==expected and ref["h"]==h and ref["k"]==k
            assert ref["gates"]==g-(variant=="remove-cz")
            assert ref["source_support"]==ref["target_support"]
            expected_fidelity={
                "grover04-relative-sign":"914034289/1073741824","grover05-relative-sign":"71822105252496225/72057594037927936",
                "grover04-remove-cz":"49/64","grover05-remove-cz":"225/256",
            }.get(case,"1")
            assert ref["fidelity"]==expected_fidelity
            folder=fixtures/case;folder.mkdir()
            for name,d in zip(NAMES,data):(folder/name).write_bytes(d)
            specs[case]=dict(shape=[n,ref["gates"]],blobs=pins,sha256=hashes(data),oracle=ref)
    (fixtures/"manifest.json").write_text(json.dumps(specs,indent=2)+"\n")
    print("AQ_GROVER_SOURCE_ORACLE "+json.dumps({c:r["oracle"]["fidelity"] for c,r in specs.items()}),flush=True)
    return fixtures,specs

def worker(binary,solver,autoq,fixtures,case,mode,folder):
    # Isolated process: extend the existing runner's expected-case table only here.
    c3.CASES.update(CASES)
    spec=json.loads((fixtures/"manifest.json").read_text())[case]
    assert hashes(read_case(fixtures/case))==spec["sha256"]
    if mode=="autoq":
        c3.autoq_arm(autoq,fixtures,case,folder)
    else:
        os.environ["AQ_C3_SOURCE_DIR"]=str(fixtures/case)
        c3.arm(binary,solver,case,mode,folder)

def main():
    binary,solver,out,autoq,root=map(lambda x:pathlib.Path(x).resolve(),sys.argv[1:6])
    out.mkdir(parents=True,exist_ok=True)
    assert PIN in subprocess.check_output([str(autoq),"-v"],text=True,stderr=subprocess.STDOUT,timeout=10)
    fixtures,specs=prepare(root,out);rows=[]
    for case,expected in CASES.items():
        for mode in MODES:
            folder=out/f"{case}-{mode}";folder.mkdir()
            t=time.monotonic()
            p=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(folder/"resource.txt"),
                "timeout","--kill-after=1s",str(c3.CAP),sys.executable,str(pathlib.Path(__file__).resolve()),
                "--worker",str(binary),str(solver),str(autoq),str(fixtures),case,mode,str(folder)],
                text=True,capture_output=True)
            elapsed=time.monotonic()-t
            (folder/"worker.stdout").write_text(p.stdout);(folder/"worker.stderr").write_text(p.stderr)
            if p.returncode in (124,137):
                row=dict(case=case,mode=mode,verdict="UNKNOWN",reason="PROCESS_TIMEOUT",queries=None)
            else:
                assert p.returncode==0,(case,mode,p.stderr,p.stdout)
                row=json.loads(p.stdout)
            if elapsed>c3.CAP+0.05:row.update(verdict="UNKNOWN",reason="OUTER_DEADLINE")
            assert row["case"]==case and row["mode"]==mode and row["verdict"] in (expected,"UNKNOWN")
            assert hashes(read_case(fixtures/case))==specs[case]["sha256"]
            res=(folder/"resource.txt").read_text().split() if (folder/"resource.txt").exists() else []
            row.update(expected=expected,budget_s=c3.CAP,process_wall_s=elapsed,
                       source_spec_sha256=specs[case]["sha256"],max_rss_kib=int(res[-1]) if res and res[-1].isdigit() else None)
            rows.append(row);print("AQ_GROVER_ARM "+json.dumps(row),flush=True)
    assert len(rows)==40 and len({(r["case"],r["mode"]) for r in rows})==40
    summary={m:dict(arms=8,definite=sum(r["mode"]==m and r["verdict"]!="UNKNOWN" for r in rows),
                    unknown=sum(r["mode"]==m and r["verdict"]=="UNKNOWN" for r in rows)) for m in MODES}
    (out/"summary.json").write_text(json.dumps(dict(rows=rows,summary=summary,source_pin=PIN,
        binary_sha256=hashes([binary.read_bytes(),solver.read_bytes(),autoq.read_bytes()]),scope="single-period reference pilot; not certified or performance claim"),indent=2)+"\n")
    print("AQ_GROVER_SUMMARY "+json.dumps(summary),flush=True)

if __name__=="__main__":
    if sys.argv[1]=="--worker":
        a,b,c,d=map(pathlib.Path,sys.argv[2:6])
        worker(a,b,c,d,sys.argv[6],sys.argv[7],pathlib.Path(sys.argv[8]))
    else: main()

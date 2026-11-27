#!/usr/bin/env python3
"""Reuse the shared WMC arm and original EQ orbit certificate, pinned sources."""
import hashlib,json,os,pathlib,re,subprocess,sys,time
from collections import defaultdict
import autoq_c3_pilot as c3
from autoq_decision_pair import PIN,blob,replace_once

PINS={
"03":("286d24f8d0e43e07535658526682566d4897823d","413ee90158043d0e17dc9285261b05de694793d1","4a5cc0a405f2c67172de5a7fe2ca16fcfac77bdc"),
"04":("2b1c53ee628ef52edeeb09bf0dc70f1d601f968c","5e63ffba67c329e6fcb14693122c35cd0f004728","56e26972835eb604ee7ffd005ae0f10cdd081697"),
"05":("80afcc4cf62924cfc51b30a9acf6f22b21f70853","3ee12b92926da432290b0abd44106ad891e36304","bb7399ca0341c60457a741540fdb595ea022f375")}
NAMES=("pre.hsl","post.hsl","circuit.qasm")
CASES={"mo03-source":"PROVED","mo04-source":"PROVED","mo05-source":"PROVED",
       "mo05-global":"PROVED","mo05-relative":"REFUTED"}

def reference(data):
    pre,post,src=[d.decode().strip() for d in data]
    m=re.fullmatch(r"Constants\nc1 := 1\nExtended Dirac\n\{c1 \|s(0+)> : \|s\|=(\d+)\}",pre);assert m
    w=int(m[2]);n=w+len(m[1]);N=1<<w
    m=re.fullmatch(r"Constants\naH := (-?\d+) / \(sqrt2 \^ (\d+)\)\naL := (-?\d+) / \(sqrt2 \^ (\d+)\)\nExtended Dirac\n\{aH \|ss([01]+)> \+ aL ∑ \|i\|=(\d+), i≠s \|si\5> : \|s\|=(\d+)\}",post)
    assert m and int(m[6])==int(m[7])==w and m[2]==m[4] and n==2*w+len(m[5])
    aH,k,aL=map(int,m.group(1,2,3));tail=int(m[5][::-1],2)
    assert aH*aH+(N-1)*aL*aL==1<<k
    lines=[l.strip() for l in src.splitlines() if l.strip()]
    assert lines[:3]==["OPENQASM 2.0;",'include "qelib1.inc";',f"qreg qubits[{n}];"]
    ops=[]
    for l in lines[3:]:
        m=re.fullmatch(r"(h|x|z|cx|cz|ccx) (qubits\[\d+\](?:,\s*qubits\[\d+\]){0,2});",l)
        assert m,l
        op=m[1];q=list(map(int,re.findall(r"\[(\d+)\]",m[2])))
        assert len(q)=={"h":1,"x":1,"z":1,"cx":2,"cz":2,"ccx":3}[op] and len(set(q))==len(q) and all(0<=i<n for i in q)
        ops.append((op,q))
    h=sum(op=="h" for op,q in ops);den=1<<(h+k)
    dots=[];members=[]
    for x in range(N):
        v={x:1}
        for op,q in ops:
            a=q[0];u=defaultdict(int)
            for z,c in v.items():
                if op=="h":
                    u[z&~(1<<a)]+=c;u[z|(1<<a)]+= -c if z>>a&1 else c
                elif op=="x":u[z^(1<<a)]+=c
                elif op=="z":u[z]+= -c if z>>a&1 else c
                elif op=="cx":u[z^((1<<q[1]) if z>>a&1 else 0)]+=c
                elif op=="ccx":u[z^((1<<q[2]) if z>>a&1 and z>>q[1]&1 else 0)]+=c
                elif op=="cz":u[z]+= -c if z>>a&1 and z>>q[1]&1 else c
            v={z:c for z,c in u.items() if c}
        assert sum(c*c for c in v.values())==1<<h
        # Independently compute every target overlap, not assume label pairing.
        d=[sum(v.get(j|(i<<w)|(tail<<(2*w)),0)*(aH if i==j else aL)
                for i in range(N)) for j in range(N)]
        assert all(z==0 for j,z in enumerate(d) if j!=x)
        dots.append(d[x]);members.append(any(z*z==den for z in d))
    return dict(n=n,h=h,k=k,labels=N,dots=dots,verdict="PROVED" if all(members) else "REFUTED")

def prepare(root,out):
    assert subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()==PIN
    fixtures=out/"source";fixtures.mkdir();specs={}
    for case,expected in CASES.items():
        size=case[2:4]
        raw=[(root/"benchmarks"/"all"/"MOGrover"/size/name).read_bytes() for name in NAMES]
        assert tuple(map(blob,raw))==PINS[size]
        if case.endswith(("global","relative")):raw[1]=replace_once(raw[1],b"aH := 23161 /",b"aH := -23161 /")
        if case.endswith("global"):raw[1]=replace_once(raw[1],b"aL := -119 /",b"aL := 119 /")
        ref=reference(raw);assert ref["verdict"]==expected
        folder=fixtures/case;folder.mkdir()
        for name,data in zip(NAMES,raw):(folder/name).write_bytes(data)
        specs[case]=dict(ref=ref,sha256=[hashlib.sha256(d).hexdigest() for d in raw])
    (out/"manifest.json").write_text(json.dumps(specs,indent=2)+"\n")
    return fixtures,specs

def worker(binary,solver,fixtures,case,folder):
    c3.CASES.update(CASES)
    os.environ["AQ_C3_SOURCE_DIR"]=str(fixtures/case)
    os.environ["AQ_C3_NATIVE_TEST"]="exact_property_cnf::hoare_autoq_shared_fixed_basis_arm"
    c3.arm(binary,solver,case,"wmc",folder)

def main():
    binary,solver,out,root=map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:5])
    out.mkdir(parents=True,exist_ok=False);fixtures,specs=prepare(root,out);rows=[]
    for period in range(2):
        def arm(case,route,bad=False):
            folder=out/f"{period}-{case}-{route}{'-bad' if bad else ''}";folder.mkdir()
            env=dict(os.environ,AQ_SHARED_WIDE="1",AQ_SHARED_FAMILY=route)
            env.pop("AQ_CPS_ORBIT_BAD",None)
            if bad:env["AQ_CPS_ORBIT_BAD"]="1"
            t=time.monotonic()
            p=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(folder/"resource.txt"),"timeout","--kill-after=1s","4",
                sys.executable,str(pathlib.Path(__file__).resolve()),"--worker",str(binary),str(solver),str(fixtures),case,str(folder)],
                env=env,capture_output=True,text=True)
            elapsed=time.monotonic()-t
            (folder/"worker.stdout").write_text(p.stdout);(folder/"worker.stderr").write_text(p.stderr)
            if p.returncode in (124,137):row=dict(verdict="UNKNOWN",reason="PROCESS_TIMEOUT",queries=None)
            else:
                assert p.returncode==0,(case,route,p.stderr,p.stdout)
                row=json.loads(p.stdout)
            row.update(period=period,case=case,route=route,bad=bad,wall_s=elapsed)
            log=folder/"native.log"
            lines=log.read_text().splitlines() if log.exists() else []
            for key,marker in (("family","AQ_SHARED_FAMILY_ROUTE "),("certificates","AQ_CPS_ORBIT_CERT "),("encodings","AQ_SHARED_FAMILY_QUERY ")):
                row[key]=[l.split(marker,1)[1] for l in lines if marker in l]
            sol=folder/"solver.jsonl"
            row["solver_records"]=[json.loads(l) for l in sol.read_text().splitlines() if l.strip().endswith("}")] if sol.exists() else []
            ref=specs[case]["ref"];initial=folder/"base.initial.txt"
            row["initial_ir_sha256"]=hashlib.sha256(initial.read_bytes()).hexdigest() if initial.exists() else None
            assert row["initial_ir_sha256"] and row["family"],row
            assert row["verdict"] in ("UNKNOWN",CASES[case]),row
            for rec,enc in zip(row["solver_records"],row["encodings"]):
                if rec["status"]!="EXACT":continue
                e=dict(kv.split("=") for kv in enc.split())
                bins=rec["bins"];assert all(bins[j]==0 for j in (1,2,3,5,6,7))
                # Common phase may differ by sign: compare squared overlap exactly.
                assert int(e["input"])==int(e["target"])
                assert (bins[0]-bins[4])**2==ref["dots"][int(e["input"])]**2,(case,enc,rec)
            if bad:
                assert f"admitted=false original={ref['labels']} representatives={ref['labels']}" in row["family"][0],row
                if case=="mo03-source":assert row["verdict"]=="PROVED" and row["queries"]==8,row
            if route=="orbit" and not bad:
                assert f"admitted=true original={ref['labels']} representatives=1" in row["family"][0],row
                assert len(row["certificates"])==ref["labels"].bit_length()-1 and all("exact=true" in c for c in row["certificates"])
                assert row["verdict"]==CASES[case] and row["queries"]==1,row
            resource=(folder/"resource.txt").read_text().split() if (folder/"resource.txt").exists() else []
            row["rss_kib"]=int(resource[-1]) if resource and resource[-1].isdigit() else None
            assert [hashlib.sha256((fixtures/case/name).read_bytes()).hexdigest() for name in NAMES]==specs[case]["sha256"]
            rows.append(row);print("AQ_SHARED_FAMILY_ARM "+json.dumps(row),flush=True)
        for case in (list(CASES) if period==0 else list(reversed(CASES))):
            for route in (("full","orbit") if period==0 else ("orbit","full")):arm(case,route)
        arm("mo03-source","orbit",True)
        arm("mo05-source","orbit",True)
    for period in range(2):
        for case in CASES:
            a,b=[next(r for r in rows if r["period"]==period and r["case"]==case and r["route"]==route and not r["bad"]) for route in ("full","orbit")]
            assert a["initial_ir_sha256"]==b["initial_ir_sha256"]
            if a["verdict"]!="UNKNOWN":assert a["verdict"]==b["verdict"]
    (out/"summary.json").write_text(json.dumps(dict(rows=rows,specs=specs,source_pin=PIN,sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (binary,solver)}),indent=2)+"\n")
    assert len(rows)==24
    print("AQ_SHARED_FAMILY_SUMMARY "+json.dumps(dict(arms=len(rows),orbit_definite=sum(r["route"]=="orbit" and not r["bad"] and r["verdict"]!="UNKNOWN" for r in rows))),flush=True)

if __name__=="__main__":
    if sys.argv[1]=="--worker":worker(pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]),pathlib.Path(sys.argv[4]),sys.argv[5],pathlib.Path(sys.argv[6]))
    else:main()

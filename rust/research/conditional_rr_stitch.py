"""Bounded independent exact verification of stitched PathSum branch identities.

No solver, Rust reduction, or native polynomial substitution is used here.
Compare canonical arithmetic phase coefficients (Fraction, modulo 1 turns
and exact radian/pi part), Boolean ANF outputs and guard, branch by branch.
This verifies the exported residual rewrite, not the source parser or RR prefix.
"""
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
CAP=16384
ZERO=(F(0),F(0))
ONE={():1}
def mon(m):
    return tuple(sorted(set(m)))
def add(p,m,c):
    m=mon(m)
    v=p.get(m,0)+c
    if v:p[m]=v
    else:p.pop(m,None)
    if len(p)>CAP:raise ValueError("oracle polynomial cap")
def times(a,b):
    p={}
    for m,c in a.items():
        for n,d in b.items():add(p,m+n,c*d)
    return p
def anf(rows):
    p=set()
    for m in rows:p.symmetric_difference_update({mon(m)})
    return p
def lift(rows):
    p={}
    for m in sorted(rows):
        old=p.copy()
        add(p,m,1)
        for n,c in old.items():add(p,m+n,-2*c)
    return p
def phaseadd(p,m,a,b):
    m=mon(m);x,y=p.get(m,ZERO)
    c=((x+a)%1,y+b)
    if c!=ZERO:p[m]=c
    else:p.pop(m,None)
    if len(p)>CAP:raise ValueError("oracle phase cap")
def substitute_phase(p,v,r):
    out={}
    for m,(a,b) in p.items():
        if v not in m:phaseadd(out,m,a,b)
        else:
            rest=tuple(i for i in m if i!=v)
            for n,c in r.items():phaseadd(out,rest+n,a*c,b*c)
    return out
def substitute_anf(p,v,r):
    out=set()
    for m in p:
        if v not in m:out.symmetric_difference_update({m})
        else:
            for n in r:out.symmetric_difference_update({mon(tuple(i for i in m if i!=v)+n)})
    return out
def decode(ir):
    p={}
    for m,a,b in ir["phase"]:phaseadd(p,m,F(a),F(b))
    return p,[anf(f) for f in ir["outputs"]],None if ir["guard"] is None else anf(ir["guard"])
def restrict(ir,gs,vals):
    p,fs,g=decode(ir)
    for v,val in zip(gs,vals):
        r={()} if val else set()
        p=substitute_phase(p,v,lift(r))
        fs=[substitute_anf(f,v,r) for f in fs]
        if g is not None:g=substitute_anf(g,v,r)
    return p,fs,g
def verify(row):
    assert row["status"]=="candidate"
    original,after=row["before"],row["after"]
    y,gs=row["y"],row["guards"]
    assert original["n"]==after["n"] and len(set(gs))==2 and y not in gs
    assert y>=original["n"] and y in original["live"]
    assert set(after["live"])==set(original["live"])-{y}
    assert set(gs)<=set(after["live"])
    assert row["hidden_before"]==row["hidden_after"]+1
    assert sorted(tuple(b["values"]) for b in row["branches"])==[(False,False),(False,True),(True,False),(True,True)]
    assert set(b["rule"] for b in row["branches"])=={1,2}
    for b in row["branches"]:
        vals=b["values"]
        p,fs,g=restrict(original,gs,vals)
        assert all(y not in m for f in fs for m in f)
        assert g is None or all(y not in m for m in g)
        dep={m:c for m,c in p.items() if y in m}
        p={m:c for m,c in p.items() if y not in m}
        if b["rule"]==2:
            v=b["pivot"]
            assert v is not None and v not in gs and v!=y and v>=original["n"] and v in after["live"]
            assert dep and all(c==(F(1,2),F(0)) for c in dep.values())
            phi=anf(tuple(i for i in m if i!=y) for m in dep)
            assert (v,) in phi and all(v not in m or m==(v,) for m in phi)
            phi.remove((v,))
            assert phi==anf(b["rhs"])
            p=substitute_phase(p,v,lift(phi))
            fs=[substitute_anf(f,v,phi) for f in fs]
            if g is not None:g=substitute_anf(g,v,phi)
            assert all(v not in m for m in p) and all(v not in m for f in fs for m in f)
            assert g is None or all(v not in m for m in g)
            phaseadd(p,(v,),F(1,4),F(0))
            phaseadd(p,(),F(-1,8),F(0))
        else:
            assert b["pivot"] is None and not b["rhs"]
            c=dep.pop((y,))
            assert c in ((F(1,4),F(0)),(F(3,4),F(0)))
            assert all(v==(F(1,2),F(0)) for v in dep.values())
            phi=anf(tuple(i for i in m if i!=y) for m in dep)
            q=F(3,4) if c[0]==F(1,4) else F(1,4)
            phaseadd(p,(),F(1,8) if c[0]==F(1,4) else F(-1,8),F(0))
            for m,k in lift(phi).items():phaseadd(p,m,k*q,F(0))
        want=(p,fs,g)
        actual=restrict(after,gs,vals)
        assert actual==want, (row["case"],vals,"exact phase/output/guard mismatch")
    return len(row["branches"])
def main():
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    case=next(c for c in manifest["cohorts"]["table2_mqt"]["cases"] if c["id"]=="grover-noancilla_4")
    expected=["f64bc99e09b5ac3aebd569505c38bae27beee38c2de5f89b96ecc91e4af7c9d9",
              "6bdbc083e4b92c4de9f2a007f8695af739bb7aabf9f11c5bb7cbcd530055d537"]
    env=dict(os.environ)
    for side,key,sha in zip(("source","transpiled"),("CRR_SOURCE","CRR_TARGET"),expected):
        e=case[side];path=ROOT/e["path"];data=path.read_bytes()
        assert hashlib.sha1(f"blob {len(data)}\\0".encode().replace(b"\\0",b"\x00")+data).hexdigest()==e["git_blob_sha1"]
        assert hashlib.sha256(data).hexdigest()==sha
        env[key]=str(path)
        print("CRR_STITCH_SOURCE",side,sha,flush=True)
    cmd=["timeout","--kill-after=3s","120s","cargo","test","--locked","--manifest-path","rust/Cargo.toml","-p","quprs",
         "--test","conditional_rr_experiment","conditional_stitch::native_mixed_stitch_pilot","--","--exact","--nocapture"]
    r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
    print(r.stdout,flush=True); print(r.stderr[-10000:],file=sys.stderr,flush=True)
    assert r.returncode==0, ("native exit",r.returncode)
    rows=[json.loads(l.removeprefix("CRR_STITCH ")) for l in r.stdout.splitlines() if l.startswith("CRR_STITCH ")]
    assert [x["case"] for x in rows]==["synthetic_original","synthetic_guarded","grover-noancilla_4"]
    assert "CRR_STITCH_NEGATIVE guard_integrator=reject guard_target=reject" in r.stdout
    import copy
    checks=0;negative=0
    for row in rows:
        if row["status"]=="rejected":
            assert row["case"]=="grover-noancilla_4",row
            print("CRR_STITCH_ORACLE",row["case"],"NOT_ADMITTED",row["reason"],flush=True)
            continue
        count=verify(row);checks+=count
        print("CRR_STITCH_ORACLE",row["case"],"EXACT_BRANCH_MATCH",count,flush=True)
        # A changed scalar or missing branch must not be accepted.
        bad=copy.deepcopy(row);bad["after"]["phase"].append([[],"1/8","0"])
        for mutation in (bad,dict(row,branches=row["branches"][:-1])):
            try:verify(mutation)
            except AssertionError:negative+=1
            else:raise AssertionError("mutation accepted")
        if row["before"]["guard"] is not None:
            bad=copy.deepcopy(row);bad["after"]["guard"]=row["before"]["guard"]
            try:verify(bad)
            except AssertionError:negative+=1
            else:raise AssertionError("untransported guard accepted")
    print("CRR_STITCH_SUMMARY",json.dumps(dict(branches=checks,mutations_rejected=negative,
          grover=rows[-1]["status"],source_semantics_certified=False,production=False)),flush=True)
if __name__=="__main__":main()

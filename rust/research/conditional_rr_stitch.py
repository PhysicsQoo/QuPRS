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
            sign=-1 if row.get("direct") else 1
            phaseadd(p,(v,),F(sign,4),F(0))
            phaseadd(p,(),F(-sign,8),F(0))
        else:
            assert b["pivot"] is None and not b["rhs"]
            c=dep.pop((y,))
            assert c in ((F(1,4),F(0)),(F(3,4),F(0)))
            assert all(v==(F(1,2),F(0)) for v in dep.values())
            phi=anf(tuple(i for i in m if i!=y) for m in dep)
            q=F(3,4) if c[0]==F(1,4) else F(1,4)
            phaseadd(p,(),F(1,8) if c[0]==F(1,4) else F(-1,8),F(0))
            for m,k in lift(phi).items():phaseadd(p,m,k*q,F(0))
            if row.get("direct"):
                v=row["direct_pivot"];shift=anf(row["direct_shift"])
                assert v in after["live"] and v>=original["n"] and v not in gs
                assert all(v not in m and y not in m and set(m)<=set(original["live"]) for m in shift)
                for coord,val in zip(gs,vals):
                    shift=substitute_anf(shift,coord,{()} if val else set())
                shift.symmetric_difference_update({(v,)})
                p=substitute_phase(p,v,lift(shift))
                fs=[substitute_anf(f,v,shift) for f in fs]
                if g is not None:g=substitute_anf(g,v,shift)
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
    direct_mode=bool(os.environ.get("CRR_DIRECT_MIXED"))
    test="conditional_stitch::native_direct_mixed_pilot" if direct_mode else "conditional_stitch::native_mixed_stitch_pilot"
    cmd=["timeout","--kill-after=3s","120s","cargo","test",*(["--release"] if direct_mode else []),"--locked","--manifest-path","rust/Cargo.toml","-p","quprs",
         "--test","conditional_rr_experiment",test,"--","--exact","--nocapture"]
    r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
    print(r.stdout,flush=True); print(r.stderr[-10000:],file=sys.stderr,flush=True)
    assert r.returncode==0, ("native exit",r.returncode)
    prefix="CRR_DIRECT " if direct_mode else "CRR_STITCH "
    rows=[json.loads(l.removeprefix(prefix)) for l in r.stdout.splitlines() if l.startswith(prefix)]
    assert [x["case"] for x in rows]==(["synthetic_original","grover-noancilla_4"] if direct_mode else ["synthetic_original","synthetic_guarded","grover-noancilla_4"])
    assert ("CRR_DIRECT_NEGATIVE output_dependency=reject wrong_quarter=reject" if direct_mode else "CRR_STITCH_NEGATIVE guard_integrator=reject guard_target=reject") in r.stdout
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
          grover=rows[-1]["status"],source_semantics_certified=False,production=False,direct=direct_mode)),flush=True)
    if direct_mode:
        import statistics
        def records(prefix):
            return [json.loads(l.removeprefix(prefix)) for l in r.stdout.splitlines() if l.startswith(prefix)]
        timing=records("CRR_DIRECT_TIMING ");wmc=records("CRR_DIRECT_WMC ");parity=records("CRR_DIRECT_PARITY ")
        assert len(timing)==12 and len(wmc)==4 and len(parity)==2
        assert all(x["status"]=="candidate" for x in rows)
        print("CRR_DIRECT_SUMMARY",json.dumps(dict(
            rewrite_median={arm:statistics.median(x["rewrite_s"] for x in timing if x["arm"]==arm) for arm in ("stitch","direct")},
            rr_total_median={arm:statistics.median(x["rewrite_s"]+x["post_rr_s"] for x in timing if x["arm"]==arm) for arm in ("stitch","direct")},
            matched_pairs=sum(x["status"]=="matched" for x in parity),
            completed_solver_calls=sum(x["status"]=="complete" for x in wmc))),flush=True)

def check_remainder(row):
    p,fs,g=decode(row["before"])
    q,gs,g2=decode(row["after"])
    y=row["y"]
    assert g is None and g2 is None
    assert row["before"]["live"]==row["after"]["live"]
    dep={m:c for m,c in p.items() if y in m}
    assert dep and dep=={m:c for m,c in q.items() if y in m}
    assert all(c==(F(1,2),F(0)) for c in dep.values())
    assert all(y not in m for f in fs+gs for m in f)
    phi=anf(tuple(v for v in m if v!=y) for m in dep)
    scope=sorted(set(v for m in phi for v in m))
    assert 2<=len(scope)<=6
    import itertools
    tested=0
    for bits in itertools.product((0,1),repeat=len(scope)):
        a=dict(zip(scope,bits))
        if sum(all(a[v] for v in m) for m in phi)%2:continue
        # Independently restrict entire phase and all output ANFs,
        # leaving nonlocal variables symbolic.
        pp,qq=p.copy(),q.copy();ff,gg=fs.copy(),gs.copy()
        for v,b in a.items():
            r={()} if b else set()
            pp=substitute_phase(pp,v,lift(r));qq=substitute_phase(qq,v,lift(r))
            ff=[substitute_anf(f,v,r) for f in ff];gg=[substitute_anf(f,v,r) for f in gg]
        assert (pp,ff)==(qq,gg),(row["case"],y,bits)
        tested+=1
    assert tested
    return tested

def cohort():
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    cases={c["id"]:c for c in manifest["cohorts"]["table2_mqt"]["cases"]}
    ids=("grover-noancilla_4","qwalk-noancilla_3","qwalk-noancilla_4","qpeexact_8","wstate_4","qnn_4","vqe_4","ghz_32")
    totals=[];direct_checks=rem_checks=0
    for name in ids:
        env=dict(os.environ,CRR_CASE=name)
        for side,key in (("source","CRR_SOURCE"),("transpiled","CRR_TARGET")):
            entry=cases[name][side];path=ROOT/entry["path"];data=path.read_bytes()
            assert hashlib.sha1(("blob %d"%len(data)).encode()+b"\x00"+data).hexdigest()==entry["git_blob_sha1"]
            env[key]=str(path)
            print("CRR_COHORT_SOURCE",name,side,hashlib.sha256(data).hexdigest(),flush=True)
        cmd=["timeout","--kill-after=3s","40s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_stitch::native_original_rr_cohort","--","--exact","--nocapture"]
        r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
        print(r.stdout,flush=True)
        assert r.returncode==0,(name,r.returncode,r.stderr[-4000:])
        rec=lambda prefix:[json.loads(l.removeprefix(prefix)) for l in r.stdout.splitlines() if l.startswith(prefix)]
        summary=rec("CRR_COHORT ");assert len(summary)==1
        for row in rec("CRR_DIRECT "):direct_checks+=verify(row)
        for row in rec("CRR_REMAINDER "):rem_checks+=check_remainder(row)
        totals.extend(summary)
    assert len(totals)==8
    print("CRR_COHORT_SUMMARY",json.dumps(dict(cases=totals,direct_exact_branches=direct_checks,remainder_exact_fibers=rem_checks,source_semantics_certified=False,production=False)),flush=True)


def verify_ket(row):
    a,b=row["before"],row["after"]
    assert a["live"]==b["live"] and a["n"]==b["n"]
    v=row["pivot"];rhs=anf(row["rhs"])
    assert v>=a["n"] and v in a["live"] and (v,) in rhs
    assert all(v not in m or m==(v,) for m in rhs)
    p,fs,g=decode(a);q,gs,g2=decode(b)
    assert g is None and g2 is None and fs[row["output"]]==rhs
    assert substitute_phase(p,v,lift(rhs))==q
    assert [substitute_anf(f,v,rhs) for f in fs]==gs
    assert gs[row["output"]]=={(v,)}
    return 1

def ket_cohort():
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    cases={c["id"]:c for c in manifest["cohorts"]["table2_mqt"]["cases"]}
    ids=("grover-noancilla_4","qwalk-noancilla_3","qwalk-noancilla_4","qpeexact_8","wstate_4","qnn_4","vqe_4","ghz_32")
    rows=[];checked=0
    for name in ids:
        env=dict(os.environ,CRR_CASE=name)
        for side,key in (("source","CRR_SOURCE"),("transpiled","CRR_TARGET")):
            e=cases[name][side];p=ROOT/e["path"];data=p.read_bytes()
            assert hashlib.sha1(("blob %d"%len(data)).encode()+b"\x00"+data).hexdigest()==e["git_blob_sha1"]
            env[key]=str(p)
            print("CRR_KET_SOURCE",name,side,hashlib.sha256(data).hexdigest(),flush=True)
        cmd=["timeout","--kill-after=3s","40s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_stitch::native_output_coordinate_cohort","--","--exact","--nocapture"]
        r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
        print(r.stdout,flush=True)
        assert r.returncode==0,(name,r.returncode,r.stderr[-4000:])
        rec=lambda prefix:[json.loads(l.removeprefix(prefix)) for l in r.stdout.splitlines() if l.startswith(prefix)]
        row=rec("CRR_KET ");assert len(row)==1;rows.extend(row)
        for z in rec("CRR_KET_REWRITE "):checked+=verify_ket(z)
    assert len(rows)==8
    print("CRR_KET_SUMMARY",json.dumps(dict(cases=rows,exact_reparameterizations=checked,source_semantics_certified=False,production=False)),flush=True)


def default_rr_cohort():
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    cases={c["id"]:c for c in manifest["cohorts"]["table2_mqt"]["cases"]}
    ids=("grover-noancilla_4","qwalk-noancilla_3","qwalk-noancilla_4","qpeexact_8","wstate_4","qnn_4","vqe_4","ghz_32")
    rows=[]
    for name in ids:
        env=dict(os.environ,CRR_CASE=name)
        for side,key in (("source","CRR_SOURCE"),("transpiled","CRR_TARGET")):
            e=cases[name][side];p=ROOT/e["path"];data=p.read_bytes()
            assert hashlib.sha1(("blob %d"%len(data)).encode()+b"\x00"+data).hexdigest()==e["git_blob_sha1"]
            env[key]=str(p)
            print("CRR_DEFAULT_SOURCE",name,side,hashlib.sha256(data).hexdigest(),flush=True)
        cmd=["timeout","--kill-after=3s","40s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_stitch::native_default_rr_baseline","--","--exact","--nocapture"]
        r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
        print(r.stdout,flush=True);assert r.returncode==0,(name,r.returncode,r.stderr[-4000:])
        rec=[json.loads(l.removeprefix("CRR_DEFAULT_RR ")) for l in r.stdout.splitlines() if l.startswith("CRR_DEFAULT_RR ")]
        assert len(rec)==1 and rec[0]["case"]==name and rec[0]["tolerance"]==1e-10
        rows.append({k:v for k,v in rec[0].items() if k!="ir"})
    print("CRR_DEFAULT_SUMMARY",json.dumps(dict(cases=rows,source_semantics_certified=False,production_change=False)),flush=True)

if __name__=="__main__":
    if os.environ.get("CRR_DEFAULT_RR"):default_rr_cohort()
    elif os.environ.get("CRR_KET_COHORT"):ket_cohort()
    elif os.environ.get("CRR_ORIGINAL_COHORT"):cohort()
    else:main()

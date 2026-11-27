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


def verify_walsh_hh(row):
    a,b,c=(row[k] for k in ("before","transformed","after"))
    y,v=row["y"],row["pivot"]
    assert (y,v)==(103,110) and row["shift"]==[91,93,111]
    assert a["n"]==b["n"]==c["n"]==4
    assert a["live"]==b["live"]
    assert set(c["live"])==set(a["live"])-{y,v}
    assert all(i>=a["n"] and i in a["live"] for i in [y,v,*row["shift"]])
    p,fs,g=decode(a);q,gs,g2=decode(b);r,hs,g3=decode(c)
    assert g is g2 is g3 is None
    assert all(i not in m for f in fs for m in f for i in [y,v,*row["shift"]])
    for i in row["shift"]:
        rhs={(i,),(y,)}
        p=substitute_phase(p,i,lift(rhs))
        fs=[substitute_anf(f,i,rhs) for f in fs]
    assert (p,fs)==(q,gs),"reparameterization"
    dep={m:k for m,k in q.items() if y in m}
    assert dep and all(k==(F(1,2),F(0)) for k in dep.values())
    phi=anf(tuple(i for i in m if i!=y) for m in dep)
    assert (v,) in phi and all(v not in m or m==(v,) for m in phi)
    phi.remove((v,))
    assert phi==anf(row["rhs"])
    assert row["scale_exponent_delta"]==-2
    assert row["inherited_rr_approximate"]==row["after_rr_approximate"]
    if row["policy"]=="strict":assert not row["inherited_rr_approximate"]
    q={m:k for m,k in q.items() if y not in m}
    assert substitute_phase(q,v,lift(phi))==r,"HH phase"
    assert [substitute_anf(f,v,phi) for f in gs]==hs,"HH outputs"
    assert all(set(m)<=set(c["live"]) for m in r)
    assert all(set(m)<=set(c["live"]) for f in hs for m in f)
    return 1

def walsh_hh_pilot():
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    case=next(c for c in manifest["cohorts"]["table2_mqt"]["cases"] if c["id"]=="grover-noancilla_4")
    expected=["f64bc99e09b5ac3aebd569505c38bae27beee38c2de5f89b96ecc91e4af7c9d9",
              "6bdbc083e4b92c4de9f2a007f8695af739bb7aabf9f11c5bb7cbcd530055d537"]
    env=dict(os.environ)
    for side,key,sha in zip(("source","transpiled"),("CRR_SOURCE","CRR_TARGET"),expected):
        e=case[side];path=ROOT/e["path"];data=path.read_bytes()
        assert hashlib.sha1(("blob %d"%len(data)).encode()+b"\x00"+data).hexdigest()==e["git_blob_sha1"]
        assert hashlib.sha256(data).hexdigest()==sha
        env[key]=str(path)
        print("CRR_WALSH_SOURCE",side,sha,flush=True)
    cmd=["timeout","--kill-after=3s","60s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_stitch::native_walsh_hh_pilot","--","--exact","--nocapture"]
    run=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
    print(run.stdout,flush=True);assert run.returncode==0,(run.returncode,run.stderr[-4000:])
    rec=lambda p:[json.loads(l.removeprefix(p)) for l in run.stdout.splitlines() if l.startswith(p)]
    rows=rec("CRR_WALSH_HH ");results=rec("CRR_WALSH_RESULT ")
    assert [r["policy"] for r in rows]==[r["policy"] for r in results]==["strict","default"]
    import copy
    checks=negative=0
    for row in rows:
        checks+=verify_walsh_hh(row)
        for field in ("scale","phase","domain","transform"):
            bad=copy.deepcopy(row)
            if field=="scale":bad["scale_exponent_delta"]=0
            elif field=="phase":bad["after"]["phase"].append([[],"1/8","0"])
            elif field=="domain":bad["after"]["live"].append(row["pivot"])
            else:bad["shift"]=bad["shift"][:-1]
            try:verify_walsh_hh(bad)
            except AssertionError:negative+=1
            else:raise AssertionError("mutation accepted")
    print("CRR_WALSH_SUMMARY",json.dumps(dict(exact_reparam_hh=checks,mutations_rejected=negative,results=[{k:v for k,v in r.items() if k!="post"} for r in results],source_semantics_certified=False,post_rr_independent_oracle=False,production=False)),flush=True)


def rotation_pilot():
    import statistics
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    cases={c["id"]:c for c in manifest["cohorts"]["table2_mqt"]["cases"]}
    negatives={"qnn_4":"fed46a5b63719525b28be193aa0a43ab9d10c6d7","vqe_4":"21776de4a2b0168f208d7dfba62ee198301a8357"}
    summary=[]
    for name in negatives:
        c=cases[name]
        for variant in ("positive","random_rotation"):
            env=dict(os.environ,CRR_CASE=name,CRR_VARIANT=variant)
            target=c["transpiled"] if variant=="positive" else dict(path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,git_blob_sha1=negatives[name])
            for entry,key in ((c["source"],"CRR_SOURCE"),(target,"CRR_TARGET")):
                path=ROOT/entry["path"];data=path.read_bytes()
                assert hashlib.sha1(("blob %d"%len(data)).encode()+b"\x00"+data).hexdigest()==entry["git_blob_sha1"]
                env[key]=str(path);print("CRR_ROTATION_SOURCE",name,variant,key,hashlib.sha256(data).hexdigest(),flush=True)
            cmd=["timeout","--kill-after=3s","90s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_stitch::native_early_rotation_pilot","--","--exact","--nocapture"]
            r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
            print(r.stdout,flush=True);assert r.returncode==0,(r.returncode,r.stderr[-4000:])
            rows=[json.loads(l.removeprefix("CRR_ROTATION ")) for l in r.stdout.splitlines() if l.startswith("CRR_ROTATION ")]
            assert len(rows)==24
            for policy in ("strict","default"):
                for arm in (False,True):
                    z=[x for x in rows if x["policy"]==policy and x["lower"]==arm]
                    assert len(z)==6 and len({(x["native"],x["hidden"],x["incidence"],x["residual_rr_approximate"]) for x in z})==1
                    summary.append(dict(case=name,variant=variant,policy=policy,lower=arm,native=z[0]["native"],hidden=z[0]["hidden"],incidence=z[0]["incidence"],residual_rr_approximate=z[0]["residual_rr_approximate"],median_total_s=statistics.median(x["total_s"] for x in z),median_verify_s=statistics.median(x["verify_s"] for x in z)))
    print("CRR_ROTATION_SUMMARY",json.dumps(dict(arms=summary,source_truth_certified=False,production=False)),flush=True)


def verify_pivot_step(row):
    a,b,c=(row[k] for k in ("before","after","native_after"))
    y,v,w=row["y"],row["pivot"],row["native_pivot"]
    assert v!=w and v<w and y!=v and y!=w
    assert a["n"]==b["n"]==c["n"]
    assert all(i>=a["n"] and i in a["live"] for i in (y,v,w))
    p,fs,g=decode(a)
    assert g is None and all(y not in m for f in fs for m in f)
    dep={m:k for m,k in p.items() if y in m}
    assert dep and all(k==(F(1,2),F(0)) for k in dep.values())
    phi=anf(tuple(i for i in m if i!=y) for m in dep)
    pivots=[m[0] for m in phi if len(m)==1 and all(m[0] not in k or k==m for k in phi)]
    assert w==max(pivots) and v in pivots
    assert row["scale_exponent_delta"]==-2
    p={m:k for m,k in p.items() if y not in m}
    for i,out in ((v,b),(w,c)):
        rhs=phi-{(i,)}
        if i==v:assert rhs==anf(row["rhs"])
        assert set(out["live"])==set(a["live"])-{y,i}
        q,gs,g2=decode(out)
        assert g2 is None
        assert substitute_phase(p,i,lift(rhs))==q
        assert [substitute_anf(f,i,rhs) for f in fs]==gs
        assert all(set(m)<=set(out["live"]) for m in q)
        assert all(set(m)<=set(out["live"]) for f in gs for m in f)
    assert row["candidate_incidence"]<row["native_incidence"]
    return 1

def pivot_pilot():
    import copy,statistics
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    cases={c["id"]:c for c in manifest["cohorts"]["table2_mqt"]["cases"]}
    ids=("grover-noancilla_4","qnn_4","vqe_4","qwalk-noancilla_3","ghz_32","qpeexact_24","qwalk-noancilla_5")
    neg={"qnn_4":"fed46a5b63719525b28be193aa0a43ab9d10c6d7","vqe_4":"21776de4a2b0168f208d7dfba62ee198301a8357"}
    summary=[];checks=mutations=0
    for name in ids:
        c=cases[name]
        for variant in (("positive","random_rotation") if name in neg else ("positive",)):
            env=dict(os.environ,CRR_CASE=name,CRR_VARIANT=variant)
            target=c["transpiled"] if variant=="positive" else dict(path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,git_blob_sha1=neg[name])
            for entry,key in ((c["source"],"CRR_SOURCE"),(target,"CRR_TARGET")):
                path=ROOT/entry["path"];data=path.read_bytes()
                assert hashlib.sha1(("blob %d"%len(data)).encode()+b"\x00"+data).hexdigest()==entry["git_blob_sha1"]
                env[key]=str(path);print("CRR_PIVOT_SOURCE",name,variant,key,hashlib.sha256(data).hexdigest(),flush=True)
            cmd=["timeout","--kill-after=3s","45s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_stitch::native_cost_aware_pivot_pilot","--","--exact","--nocapture"]
            r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
            print(r.stdout,flush=True)
            if r.returncode in (124,137):
                summary.append(dict(case=name,variant=variant,status="censored_timeout_or_kill"))
                continue
            assert r.returncode==0,(name,variant,r.returncode,r.stderr[-4000:])
            rec=lambda p:[json.loads(l.removeprefix(p)) for l in r.stdout.splitlines() if l.startswith(p)]
            rows=rec("CRR_PIVOT_CASE ");steps=rec("CRR_PIVOT_STEP ");timing=rec("CRR_PIVOT_TIME ")
            assert len(rows)==1 and len(timing)==6 and len(steps)==rows[0]["accepted"]
            for row in steps:
                checks+=verify_pivot_step(row)
                for field in ("phase","scale","domain"):
                    bad=copy.deepcopy(row)
                    if field=="phase":bad["after"]["phase"].append([[],"1/8","0"])
                    elif field=="scale":bad["scale_exponent_delta"]=0
                    else:bad["after"]["live"].append(row["pivot"])
                    try:verify_pivot_step(bad)
                    except AssertionError:mutations+=1
                    else:raise AssertionError("mutation accepted")
            row={k:v for k,v in rows[0].items() if k not in ("baseline","candidate")}
            row["status"]="complete"
            row["median_replay_s"]={str(arm).lower():statistics.median(x["elapsed_s"] for x in timing if x["adaptive"]==arm) for arm in (False,True)}
            summary.append(row)
    print("CRR_PIVOT_SUMMARY",json.dumps(dict(cases=summary,exact_local_checks=checks,mutations_rejected=mutations,source_truth_certified=False,production=False)),flush=True)


def frontier_pilot():
    import resource
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    cases={c["id"]:c for c in manifest["cohorts"]["table2_mqt"]["cases"]}
    negative={"qwalk-noancilla_4":"ab5cda304a5ddb76e10a957b87baa343513b1d9e","qwalk-noancilla_5":"d927ecd21bf3676069d90a3ad3bc4e7ee434a0de"}
    scope=("qwalk-noancilla_4","qwalk-noancilla_5","qpeexact_24","qft_24")
    summary=[]
    def limit():
        resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    for name in scope:
        c=cases[name]
        for variant in (("positive","random_rotation") if name in negative else ("positive",)):
            target=c["transpiled"] if variant=="positive" else dict(path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,git_blob_sha1=negative[name])
            env=dict(os.environ,CRR_CASE=name,CRR_VARIANT=variant)
            for entry,key in ((c["source"],"CRR_SOURCE"),(target,"CRR_TARGET")):
                p=ROOT/entry["path"];data=p.read_bytes()
                assert hashlib.sha1(("blob %d"%len(data)).encode()+b"\x00"+data).hexdigest()==entry["git_blob_sha1"]
                env[key]=str(p);print("CRR_FRONTIER_SOURCE",name,variant,key,hashlib.sha256(data).hexdigest(),flush=True)
            # Independent processes keep timeout/memory censoring per arm.
            plans=[(p,"rr",a) for p in ("default","strict") for a in ("original","lower","frontier")]
            if name in ("qwalk-noancilla_5","qpeexact_24"):
                plans += [("default","hybrid",a) for a in ("original","lower","frontier")]
            for policy,mode,arm in plans:
                cmd=["timeout","--kill-after=2s","20s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_stitch::native_frontier_pilot","--","--exact","--nocapture"]
                run=subprocess.run(cmd,cwd=ROOT,env=dict(env,CRR_POLICY=policy,CRR_MODE=mode,CRR_ARM=arm),capture_output=True,text=True,preexec_fn=limit)
                print(run.stdout,flush=True)
                prep=[json.loads(l.removeprefix("CRR_FRONTIER_PREP ")) for l in run.stdout.splitlines() if l.startswith("CRR_FRONTIER_PREP ")]
                rows=[json.loads(l.removeprefix("CRR_FRONTIER_RESULT ")) for l in run.stdout.splitlines() if l.startswith("CRR_FRONTIER_RESULT ")]
                identity=dict(case=name,variant=variant,policy=policy,mode=mode,arm=arm)
                if run.returncode in (124,137) or (run.returncode!=0 and "memory allocation of" in run.stderr and "failed" in run.stderr):
                    summary.append(dict(**identity,status="censored_timeout_or_memory",returncode=run.returncode,prep=prep,stderr=run.stderr[-1000:]))
                    continue
                assert run.returncode==0,(identity,run.returncode,run.stderr[-4000:])
                assert len(prep)==len(rows)==1
                assert all(rows[0][k]==v for k,v in identity.items())
                summary.append(dict(**rows[0],status="returned",prep=prep[0]))
    print("CRR_FRONTIER_SUMMARY",json.dumps(dict(cases=summary,source_truth_certified=False,production=False,single_observation=True)),flush=True)

def qpe24_reuse():
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    c=next(x for x in manifest["cohorts"]["table2_mqt"]["cases"] if x["id"]=="qpeexact_24")
    env=dict(os.environ,CRR_CASE=c["id"],CRR_REPEAT="0",CRR_SOLVER_SECS="12")
    for entry,key in ((c["source"],"CRR_SOURCE"),(c["transpiled"],"CRR_TARGET")):
        p=ROOT/entry["path"];data=p.read_bytes()
        assert hashlib.sha1(("blob %d"%len(data)).encode()+b"\x00"+data).hexdigest()==entry["git_blob_sha1"]
        env[key]=str(p);print("CRR_QPE24_SOURCE",key,hashlib.sha256(data).hexdigest(),flush=True)
    cmd=["timeout","--kill-after=3s","90s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_trace::native_full_pipeline_paired","--","--exact","--nocapture"]
    r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
    print(r.stdout,flush=True)
    if r.returncode in (124,137):print("CRR_QPE24_REUSE_CENSORED",r.returncode,flush=True)
    else:
        assert r.returncode==0,(r.returncode,r.stderr[-4000:])
        assert len([l for l in r.stdout.splitlines() if l.startswith("CRR_FULL_CALL ")])==2
        assert len([l for l in r.stdout.splitlines() if l.startswith("CRR_FULL_COMPARE ")])==1


def historical_closeout():
    from conditional_rr_reference import run_case,locked
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    cases={c["id"]:c for c in manifest["cohorts"]["table2_mqt"]["cases"]}
    neg={"qwalk-noancilla_4":"ab5cda304a5ddb76e10a957b87baa343513b1d9e","qwalk-noancilla_5":"d927ecd21bf3676069d90a3ad3bc4e7ee434a0de","qpeexact_24":"a3d3099816e51d98783176a1df64b077b92ab0b7"}
    def inputs(name,variant):
        c=cases[name]
        target=c["transpiled"] if variant=="positive" else dict(path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,git_blob_sha1=neg[name])
        paths=[]
        for entry in (c["source"],target):
            path=ROOT/entry["path"];data=path.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            print("CRR_CLOSEOUT_SOURCE",name,variant,entry["path"],hashlib.sha256(data).hexdigest(),flush=True);paths.append(path)
        return paths
    # Reuse the independent reference, verify QPE24 positive and historical
    # random-rotation negative; same native RR/normalization, not source proof.
    for variant in ("positive","random_rotation"):
        a,b=inputs("qpeexact_24",variant)
        r=run_case("qpeexact_24:"+variant,a,b,None)
        print("CRR_QPE24_REFERENCE "+json.dumps(r),flush=True)
        assert r["status"]!="ERROR"
    # Locate native explosion without another unbounded complete miter.
    for name in ("qwalk-noancilla_4","qwalk-noancilla_5"):
        for variant in ("positive","random_rotation"):
            a,b=inputs(name,variant)
            for policy in ("strict","default"):
                for schedule in ("difference","naive"):
                    env=dict(os.environ,CRR_CASE=name,CRR_VARIANT=variant,CRR_SOURCE=str(a),CRR_TARGET=str(b),CRR_POLICY=policy,CRR_SCHEDULE=schedule)
                    cmd=["timeout","--kill-after=2s","15s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_stitch::native_growth_checkpoint","--","--exact","--nocapture"]
                    r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
                    print("CRR_GROWTH_RUN",name,variant,policy,schedule,r.returncode,flush=True);print(r.stdout,flush=True)
                    if r.returncode in (124,137):print("CRR_GROWTH_CENSORED",flush=True);continue
                    assert r.returncode==0,(name,variant,policy,schedule,r.stderr[-4000:])
                    assert sum(l.startswith(("CRR_GROWTH_STOP ","CRR_GROWTH_COMPLETE ")) for l in r.stdout.splitlines())==1


def conditional_lift_checkpoint():
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    c=next(c for c in manifest["cohorts"]["table2_mqt"]["cases"] if c["id"]=="qwalk-noancilla_5")
    for variant in ("positive","random_rotation"):
        target=c["transpiled"] if variant=="positive" else dict(path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,git_blob_sha1="d927ecd21bf3676069d90a3ad3bc4e7ee434a0de")
        paths=[]
        for entry in (c["source"],target):
            p=ROOT/entry["path"];data=p.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            print("CRR_LIFT_SOURCE",variant,entry["path"],hashlib.sha256(data).hexdigest(),flush=True);paths.append(p)
        env=dict(os.environ,CRR_CASE=c["id"],CRR_VARIANT=variant,CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]),CRR_POLICY="strict",CRR_SCHEDULE="difference",CRR_LIFT_CHECKPOINT="1")
        cmd=["timeout","--kill-after=2s","30s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_stitch::native_growth_checkpoint","--","--exact","--nocapture"]
        r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
        print(r.stdout,flush=True)
        if r.returncode in (124,137):
            print("CRR_LIFT_CENSORED",variant,r.returncode,flush=True);continue
        assert r.returncode==0,(variant,r.stderr[-4000:])
        assert sum(l.startswith("CRR_LIFT_LOCAL ") for l in r.stdout.splitlines())==1
        assert sum(l.startswith("CRR_LIFT_HORIZON ") for l in r.stdout.splitlines())==1


def lift_policy_comparison():
    import resource
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    c=next(c for c in manifest["cohorts"]["table2_mqt"]["cases"] if c["id"]=="qwalk-noancilla_5")
    def limit():
        resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    for variant in ("positive","random_rotation"):
        target=c["transpiled"] if variant=="positive" else dict(path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,git_blob_sha1="d927ecd21bf3676069d90a3ad3bc4e7ee434a0de")
        paths=[]
        for entry in (c["source"],target):
            p=ROOT/entry["path"];data=p.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            print("CRR_POLICY_SOURCE",variant,entry["path"],hashlib.sha256(data).hexdigest(),flush=True);paths.append(p)
        for arm in (("static","adaptive") if variant=="positive" else ("adaptive","static")):
            env=dict(os.environ,CRR_CASE=c["id"],CRR_VARIANT=variant,CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]),CRR_POLICY="strict",CRR_SCHEDULE="difference",CRR_LIFT_CHECKPOINT="1",CRR_LIFT_POLICY=arm)
            cmd=["timeout","--kill-after=2s","25s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_stitch::native_growth_checkpoint","--","--exact","--nocapture"]
            r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,preexec_fn=limit)
            print(r.stdout,flush=True)
            if r.returncode in (124,137) or "memory allocation" in r.stderr.lower():
                print("CRR_POLICY_CENSORED",variant,arm,r.returncode,r.stderr[-1000:],flush=True);continue
            assert r.returncode==0,(variant,arm,r.stderr[-4000:])
            assert sum(l.startswith("CRR_POLICY_SUMMARY ") for l in r.stdout.splitlines())==1

def lift_handoff():
    import resource
    manifest=json.loads((ROOT/"docs/development/paper-corpus-manifest.json").read_text())
    c=next(c for c in manifest["cohorts"]["table2_mqt"]["cases"] if c["id"]=="qwalk-noancilla_5")
    target=dict(path="benchmarks/MQTBench/Random_Rotation/"+Path(c["source"]["path"]).name,git_blob_sha1="d927ecd21bf3676069d90a3ad3bc4e7ee434a0de")
    paths=[]
    for entry in (c["source"],target):
        p=ROOT/entry["path"];data=p.read_bytes()
        assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
        print("CRR_HANDOFF_SOURCE",entry["path"],hashlib.sha256(data).hexdigest(),flush=True);paths.append(p)
    env=dict(os.environ,CRR_CASE=c["id"],CRR_VARIANT="random_rotation",CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]),CRR_POLICY="strict",CRR_SCHEDULE="difference",CRR_LIFT_CHECKPOINT="1",CRR_LIFT_POLICY="adaptive",CRR_LIFT_HANDOFF="1")
    def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    cmd=["timeout","--kill-after=2s","65s","cargo","test","--release","--locked","--manifest-path","rust/Cargo.toml","-p","quprs","--test","conditional_rr_experiment","conditional_stitch::native_growth_checkpoint","--","--exact","--nocapture"]
    r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,preexec_fn=limit)
    print(r.stdout,flush=True)
    if r.returncode in (124,137) or "memory allocation" in r.stderr.lower():
        print("CRR_HANDOFF_CENSORED",r.returncode,r.stderr[-1000:],flush=True);return
    assert r.returncode==0,(r.returncode,r.stderr[-4000:])
    assert sum(l.startswith("CRR_POLICY_SUMMARY ") for l in r.stdout.splitlines())==1
    if "CRR_POLICY_COMPLETE " in r.stdout:
        assert sum(l.startswith("CRR_HANDOFF_CALL ") for l in r.stdout.splitlines())==3
if __name__=="__main__":
    if os.environ.get("CRR_LIFT_HANDOFF"):lift_handoff()
    elif os.environ.get("CRR_LIFT_POLICY_COMPARISON"):lift_policy_comparison()
    elif os.environ.get("CRR_CONDITIONAL_LIFT"):conditional_lift_checkpoint()
    elif os.environ.get("CRR_HISTORICAL_CLOSEOUT"):historical_closeout()
    elif os.environ.get("CRR_FRONTIER"):frontier_pilot()
    elif os.environ.get("CRR_QPE24_REUSE"):qpe24_reuse()
    elif os.environ.get("CRR_PIVOT"):pivot_pilot()
    elif os.environ.get("CRR_ROTATION"):rotation_pilot()
    elif os.environ.get("CRR_WALSH_HH"):walsh_hh_pilot()
    elif os.environ.get("CRR_DEFAULT_RR"):default_rr_cohort()
    elif os.environ.get("CRR_KET_COHORT"):ket_cohort()
    elif os.environ.get("CRR_ORIGINAL_COHORT"):cohort()
    else:main()

"""I2b: one native routed solve per frozen heavy coordinate.
Independent 2048-bit source comparison; native dynamic precision is not
the historical fixed-256-bit experiment. Count delta threshold is an
observational test (1e-25), not a certified solver arithmetic bound.
"""
import hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
from fractions import Fraction
from cpr_hh_n5c import entries
from cpr_router_acceptance import limit
from cpr_c3_matched import emit
from conditional_rr_stitch import ROOT
EXPECTED={
 ("qwalk-noancilla_5","positive"):(7,387,7,3341,13965),
 ("qwalk-noancilla_5","random_rotation"):(7,399,7,3396,14100),
 ("grover-noancilla_6","positive"):(1,259,0,1410,4976),
 ("wstate_16","positive"):(1,84,1,2827,16644),
 ("wstate_16","random_rotation"):(1,87,1,2836,16658),
}
def run():
    binary=Path(os.environ["CPR_I2B_BIN"]).resolve()
    emit("CPR_I2B_BINARY",sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    errors=[]
    for name,variant,n,a,b in entries():
        paths=[]
        for entry in (a,b):
            p=ROOT/entry["path"];data=p.read_bytes()
            assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==entry["git_blob_sha1"]
            paths.append(p)
        env=dict(os.environ,CRR_SOURCE=str(paths[0]),CRR_TARGET=str(paths[1]))
        with tempfile.TemporaryDirectory() as tmp:
            meter=Path(tmp)/"time"
            p=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(meter),"timeout","--kill-after=2s","35s",str(binary),"cpr_native_router_tests::i2b_locked_source_worker","--exact","--nocapture"],env=env,cwd=ROOT,text=True,capture_output=True,preexec_fn=limit)
            resource=meter.read_text().strip().splitlines() if meter.exists() else []
        print(p.stdout,flush=True);print(p.stderr,flush=True)
        def row(prefix):
            found=[l.split(prefix,1)[1] for l in p.stdout.splitlines() if prefix in l]
            return dict(re.findall(r"(\w+)=([^ ]+)",found[0])) if len(found)==1 else {}
        build=row("CPR_I2B_BUILD ");route=row("CPR_I2B_ROUTE ");count=row("CPR_I2B_COUNT ");result=row("CPR_I2B_RESULT ")
        pairs,twice,removed,v,c=EXPECTED[name,variant]
        header=f"header=p cnf {v} {c}"
        ok=p.returncode==0 and build.get("pairs")==str(pairs) and build.get("twice")==str(twice) and count.get("removed")==str(removed) and count.get("twice")==str(twice-2*removed) and header in p.stdout and result.get("status") in ("Equivalent","EquivalentUpToGlobalPhase","NotEquivalent")
        if not ok:errors.append([name,variant,p.returncode])
        emit("CPR_I2B_RECEIPT",case=name,variant=variant,ok=ok,build=build,route=route,count=count,result=result,resource=resource)
    emit("CPR_I2B_NATIVE_GATE",errors=errors,checked=5)
    assert not errors
def source():
    from conditional_rr_source_ball import load,controls,dense_overlap,EPS,arb,acb,fmpq,ctx
    from conditional_rr_tensor_source import tensor_trace,controls as tensor_controls
    controls();tensor_controls();assert ctx.prec==2048
    receipts=[json.loads(l.split("CPR_I2B_RECEIPT ",1)[1]) for l in Path(os.environ["CRR_GENERIC_LOG"]).read_text().splitlines() if l.startswith("CPR_I2B_RECEIPT ")]
    assert len(receipts)==5 and len({(r["case"],r["variant"]) for r in receipts})==5
    checked=0;errors=[]
    for name,variant,n,source,target in entries():
        r=next(r for r in receipts if (r["case"],r["variant"])==(name,variant))
        if not r["count"]:errors.append([name,variant,"missing count"]);continue
        a,ha=load(source,n);b,hb=load(target,n)
        try:z,meta=tensor_trace(a,b,n);method="tensor_trace"
        except ValueError:
            if n>8:raise
            z=sum((dense_overlap(a,b,k,n) for k in range(1<<n)),acb(0))/(1<<n);meta={};method="dense"
        count=r["count"];k=int(count["twice"])
        def exact(s):
            q=Fraction(s);return arb(fmpq(q.numerator,q.denominator))
        normalized=acb(exact(count["real"]),exact(count["imag"]))/(arb(2)**(k//2)*(arb(2).sqrt() if k%2 else 1))
        delta=abs(normalized-z).upper()
        threshold=(1-EPS*EPS).sqrt()
        expected="Equivalent" if abs(z).lower()>threshold else "NotEquivalent" if abs(z).upper()<threshold else "INCONCLUSIVE"
        actual=r["result"].get("status")
        binary="Equivalent" if actual in ("Equivalent","EquivalentUpToGlobalPhase") else actual
        ok=bool(delta<arb("1e-25")) and binary==expected and r["ok"]
        if not ok:errors.append([name,variant,str(delta),actual,expected])
        checked+=1
        emit("CPR_I2B_SOURCE",case=name,variant=variant,matched=ok,source_verdict=expected,native_verdict=actual,count_delta_upper=str(delta),method=method,source_sha256=ha,target_sha256=hb,**meta)
    emit("CPR_I2B_SOURCE_GATE",checked=checked,errors=errors,observational_count_threshold="1e-25")
    assert checked==5 and not errors
if __name__=="__main__":
    if os.environ.get("CRR_GENERIC_LOG"):source()
    else:run()

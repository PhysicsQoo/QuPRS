#!/usr/bin/env python3
"""Matched original source E2E encoder A/B. Six balanced periods, 4s per complete
process tree. Release builds; no timed dense oracle. GNU time max RSS is
maximum individual process RSS, not sum of concurrent process-tree RSS."""
import hashlib
import json
import os
import pathlib
import statistics
import subprocess
import sys
import time
from fractions import Fraction
from autoq_decision_pair import PIN, BLOBS, SHAPES, blob, mutant, classify
from hoare_ganak_exact import single_fibre_pack, single_fibre_decode, parse_gpmc_integer

CAP=4
MODES=("rr","wmc","hybrid","autoq","wmc-dag","hybrid-dag")
# Williams design: balance both positions and first-order carryover.
ORDERS=tuple(tuple((i+p)%6 for i in (0,1,5,2,4,3)) for p in range(6))
PERIODS=len(ORDERS)
assert all(sorted(order)==list(range(len(MODES))) for order in ORDERS)
assert len({(a,b) for order in ORDERS for a,b in zip(order,order[1:])})==30
VARIANTS=("source","relative-mutant","global-sign")
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic_receipt(folder,name,data):
    tmp=folder/(name+".tmp")
    tmp.write_text(json.dumps(data)+"\n")
    tmp.replace(folder/name)
def timeout_row(folder,mode):
    row=dict(verdict="UNKNOWN",reason="PROCESS_TIMEOUT")
    receipt=folder/"query-ready.json"
    if mode=="autoq" or not receipt.is_file():return row
    ready=json.loads(receipt.read_text())
    assert ready["verdict"]=="UNKNOWN" and ready["reason"]=="QUERY_PREPARED",ready
    assert ready["cnf_sha256"]==sha(folder/"base.cnf")
    assert ready["packed_sha256"]==sha(folder/"packed.cnf")
    assert ready["initial_sha256"]==sha(folder/"initial.txt")
    row.update(ready)
    row.update(verdict="UNKNOWN",reason="PROCESS_TIMEOUT",query_prepared=True,solver_invoked=None,timeout_boundary="prepared-no-launch-receipt")
    launch=folder/"solver-launch.json"
    done=folder/"solver-exit.json"
    if launch.is_file():
        started=json.loads(launch.read_text())
        assert started["packed_sha256"]==ready["packed_sha256"] and started["pid"]>0,started
        row.update(solver_invoked=True,timeout_boundary="launched-no-exit-receipt")
    if done.is_file():
        assert launch.is_file()
        exited=json.loads(done.read_text())
        assert exited["packed_sha256"]==ready["packed_sha256"] and exited["pid"]==started["pid"],exited
        row.update(solver_invoked=True,timeout_boundary="exit-observed-before-worker-result",
                   solver_s=exited["solver_s"],solver_returncode=exited["returncode"])
    return row
def sign(a,b):
    if a==0:return (b>0)-(b<0)
    if b==0 or (a>0)==(b>0):return (a>0)-(a<0)
    c=(a*a>2*b*b)-(a*a<2*b*b)
    return c if a>0 else -c
def worker(binary,solver,folder,mode):
    env=dict(os.environ,CPS_CORE_MATCHED_DIR=str(folder),CPS_CORE_MATCHED_MODE=mode)
    p=subprocess.run([str(binary),"--exact","exact_property_cnf::hoare_cps_core_matched_worker","--nocapture"],env=env,capture_output=True,text=True)
    (folder/"native.stdout").write_text(p.stdout);(folder/"native.stderr").write_text(p.stderr)
    if p.returncode!=0:
        print(json.dumps(dict(verdict="UNKNOWN",reason="NATIVE_ERROR",returncode=p.returncode)));return
    markers=[l.split()[1:] for l in p.stdout.splitlines() if l.startswith("CPS_MATCHED_NATIVE ")]
    assert len(markers)==1,markers
    m=markers[0]
    if m[0]=="UNSUPPORTED":
        detail=[l.removeprefix("CPS_COMPOSITION_DETAIL ") for l in p.stdout.splitlines() if l.startswith("CPS_COMPOSITION_DETAIL ")]
        row=dict(verdict="UNKNOWN",reason="UNSUPPORTED",stage=m[1] if len(m)>1 else "unspecified")
        if detail:
            assert len(detail)==1 and row["stage"] in ("native-gate-composition","composition","adjoint"),detail
            row["composition_detail"]=detail[0]
        enc=[l.removeprefix("CPS_SPARSE_ENCODER_DETAIL ") for l in p.stdout.splitlines() if l.startswith("CPS_SPARSE_ENCODER_DETAIL ")]
        if enc:
            assert len(enc)==1 and row["stage"] in ("flat-encoder","dag-encoder"),enc
            row["encoder_detail"]=enc[0]
        sparse=[l.removeprefix("CPS_SPARSE_MATCHED ") for l in p.stdout.splitlines() if l.startswith("CPS_SPARSE_MATCHED ")]
        if sparse:
            assert len(sparse)==1,sparse
            row.update(storage="sparse",sparse_detail=sparse[0])
            if (folder/"initial.txt").is_file():row["initial_sha256"]=sha(folder/"initial.txt")
            if (folder/"sparse-rr.txt").is_file():
                assert not mode.startswith("wmc"),mode
                row["sparse_rr_sha256"]=sha(folder/"sparse-rr.txt")
            if row["stage"]=="flat-encoder":assert enc,row
        print(json.dumps(row));return
    status=m[0]
    n,k,h,ih,steps,primary,vars,clauses=map(int,m[1:9])
    phase=m[9];build_ns,rr_ns,encode_ns=map(int,m[10:])
    row=dict(verdict=status if status!="READY" else "UNKNOWN",reason="algebraic" if status in ("PROVED","REFUTED") else "residual",
             n=n,k=k,h=h,initial_h=ih,steps=steps,primary=primary,vars=vars,clauses=clauses,build_ns=build_ns,rr_ns=rr_ns,encode_ns=encode_ns,
             initial_sha256=sha(folder/"initial.txt"),solver_invoked=False)
    affine=[l.removeprefix("CPS_AFFINE_INTERFACE ") for l in p.stdout.splitlines() if l.startswith("CPS_AFFINE_INTERFACE ")]
    if affine:
        assert len(affine)==1,affine
        row["affine_interface"]=affine[0]
    pre_rr=[l.removeprefix("CPS_PRECOMPOSE_RR ") for l in p.stdout.splitlines() if l.startswith("CPS_PRECOMPOSE_RR ")]
    if pre_rr:
        assert len(pre_rr)==1 and not mode.startswith("wmc"),pre_rr
        row["precompose_rr"]=pre_rr[0]
    prefix=[l.removeprefix("CPS_PREFIX_INTERFACE ") for l in p.stdout.splitlines() if l.startswith("CPS_PREFIX_INTERFACE ")]
    if prefix:
        assert len(prefix)==1 and not mode.startswith("wmc"),prefix
        row.update(prefix_rr=prefix[0],prefix_receipt_sha256=sha(folder/"prefix-rr.txt"))
    sparse=[l.removeprefix("CPS_SPARSE_MATCHED ") for l in p.stdout.splitlines() if l.startswith("CPS_SPARSE_MATCHED ")]
    if sparse:
        assert len(sparse)==1,sparse
        row["storage"]="sparse"
        row["sparse_detail"]=sparse[0]
        if (folder/"sparse-rr.txt").is_file():
            assert not mode.startswith("wmc"),mode
            row["sparse_rr_sha256"]=sha(folder/"sparse-rr.txt")
    if status=="READY":
        base=(folder/"base.cnf").read_text()
        packed,radix,bound=single_fibre_pack(base,list(map(int,phase.split(","))),primary)
        query=folder/"packed.cnf";query.write_text(packed)
        row.update(cnf_sha256=sha(folder/"base.cnf"),packed_sha256=sha(query))
        # Distinguish prepared query, successful process launch and observed exit.
        # A missing receipt cannot prove that the process did not run.
        atomic_receipt(folder,"query-ready.json",dict(row,verdict="UNKNOWN",reason="QUERY_PREPARED",solver_invoked=None))
        start=time.monotonic()
        try:
            p=subprocess.Popen([str(solver),"-mode=1","-natw",str(query)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        except OSError as exc:
            row.update(reason="SOLVER_LAUNCH_ERROR",launch_error=str(exc))
            print(json.dumps(row));return
        with p:
            row["solver_invoked"]=True
            launch=dict(packed_sha256=row["packed_sha256"],pid=p.pid)
            atomic_receipt(folder,"solver-launch.json",launch)
            stdout,stderr=p.communicate()
            row["solver_s"]=time.monotonic()-start
            atomic_receipt(folder,"solver-exit.json",dict(launch,solver_s=row["solver_s"],returncode=p.returncode))
        (folder/"solver.stdout").write_text(stdout);(folder/"solver.stderr").write_text(stderr)
        if p.returncode!=0:row.update(reason="SOLVER_ERROR",returncode=p.returncode)
        else:
            try:bins=single_fibre_decode(parse_gpmc_integer(stdout,"wmc",bound*radix**7),radix,bound,8)
            except (ValueError,OverflowError):row.update(reason="INVALID_COUNT")
            else:
                assert all(bins[i]==bins[-i%8] for i in range(8)),bins
                a,b=Fraction(bins[0]-bins[4])*Fraction(2)**(-k),Fraction(bins[1]-bins[3])*Fraction(2)**(-k)
                d=sign(a-(1<<n),b);assert sign(a,b)>=0 and d<=0,(a,b,n)
                row.update(verdict="PROVED" if d==0 else "REFUTED",reason="EXACT",norm=[str(a),str(b)],bins=bins)
    print(json.dumps(row))
def main(binary,solver,autoq,root,out):
    out.mkdir(parents=True,exist_ok=False)
    assert subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()==PIN
    version=subprocess.run([str(autoq),"-v"],capture_output=True,text=True,check=True)
    assert PIN in version.stdout+version.stderr
    fixtures={}
    for case,hashes in BLOBS.items():
        family={"bv03":"BV","grover03":"Grover","mogrover03":"MOGrover"}[case]
        source=root/"benchmarks"/"all"/family/"03"
        pre,post,qasm=[(source/f).read_bytes() for f in ("pre.hsl","post.hsl","circuit.qasm")]
        assert tuple(map(blob,(pre,post,qasm)))==hashes
        for variant in VARIANTS:
            fixtures[case,variant]=(pre,mutant(case,post,variant),qasm)
    rows=[]
    for period,order in enumerate(ORDERS):
        keys=list(fixtures)
        if period%2:keys.reverse()
        for case,variant in keys:
            expected="REFUTED" if variant=="relative-mutant" else "PROVED"
            for i in order:
                mode=MODES[i]
                folder=out/f"{period}-{case}-{variant}-{mode}";folder.mkdir()
                for name,data in zip(("pre.hsl","post.hsl","circuit.qasm"),fixtures[case,variant]):
                    (folder/name).write_bytes(data)
                args=[str(autoq),"ver",str(folder/"pre.hsl"),str(folder/"circuit.qasm"),str(folder/"post.hsl")] if mode=="autoq" else [sys.executable,str(pathlib.Path(__file__).resolve()),"--worker",str(binary),str(solver),str(folder),mode]
                t=time.monotonic()
                p=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(folder/"resource.txt"),"timeout","--kill-after=1s",str(CAP),*args],capture_output=True,text=True,errors="replace")
                wall=time.monotonic()-t
                (folder/"stdout").write_text(p.stdout);(folder/"stderr").write_text(p.stderr)
                if p.returncode in (124,137):row=timeout_row(folder,mode)
                elif mode=="autoq":
                    result=classify(p.stdout,p.stderr,p.returncode,SHAPES[case])
                    row=dict(verdict=result if result in ("PROVED","REFUTED") else "UNKNOWN",reason=result)
                else:
                    assert p.returncode==0,(case,variant,mode,p.stdout,p.stderr)
                    row=json.loads(p.stdout)
                resource=(folder/"resource.txt").read_text().split()
                rss=int(resource[-1]) if resource and resource[-1].isdigit() else None
                row.update(case=case,variant=variant,mode=mode,period=period,expected=expected,wall_s=wall,max_individual_rss_kib=rss,
                           returncode=p.returncode,inputs_sha256=[sha(folder/f) for f in ("pre.hsl","post.hsl","circuit.qasm")])
                assert row["verdict"] in ("UNKNOWN",expected),row
                if row.get("norm") is not None:
                    want=Fraction(0) if case=="bv03" and variant=="relative-mutant" else Fraction(3249,4096)*(8 if case=="mogrover03" else 1) if variant=="relative-mutant" else Fraction(8 if case=="mogrover03" else 1)
                    assert row["norm"]==[str(want),"0"],row
                rows.append(row);print("CPS_MATCHED_ARM",json.dumps(row),flush=True)
    assert len(rows)==len(fixtures)*len(MODES)*PERIODS==324
    for period in range(PERIODS):
        for case,variant in fixtures:
            group=[r for r in rows if (r["period"],r["case"],r["variant"])==(period,case,variant)]
            assert len(group)==len(MODES) and len({tuple(r["inputs_sha256"]) for r in group})==1
            hashes={r["initial_sha256"] for r in group if "initial_sha256" in r}
            assert len(hashes)==1,(case,variant,hashes)
            by_mode={r["mode"]:r for r in group}
            for flat,dag in (("wmc","wmc-dag"),("hybrid","hybrid-dag")):
                a,b=by_mode[flat],by_mode[dag]
                assert a["verdict"]==a["expected"],a
                if b["verdict"]!="UNKNOWN":
                    assert a["verdict"]==b["verdict"]
                    assert all(a.get(x)==b.get(x) for x in ("initial_sha256","n","h","k","steps","primary","solver_invoked","bins","norm")),(a,b)
            assert by_mode["autoq"]["verdict"]==by_mode["autoq"]["expected"]
            if case=="bv03":
                assert by_mode["rr"]["verdict"]==by_mode["rr"]["expected"]
    summary=[]
    for case,variant in fixtures:
        for mode in MODES:
            group=[r for r in rows if (r["case"],r["variant"],r["mode"])==(case,variant,mode)]
            definite=[r for r in group if r["verdict"]!="UNKNOWN"]
            summary.append(dict(case=case,variant=variant,mode=mode,definite=len(definite),runs=PERIODS,
                median_wall_s=statistics.median(r["wall_s"] for r in definite) if len(definite)==PERIODS else None,
                median_rss_kib=statistics.median(r["max_individual_rss_kib"] for r in definite) if len(definite)==PERIODS and all(r["max_individual_rss_kib"] is not None for r in definite) else None,
                median_solver_s=statistics.median(r.get("solver_s",0) for r in definite) if len(definite)==PERIODS else None,
                median_encode_ns=statistics.median(r.get("encode_ns",0) for r in definite) if len(definite)==PERIODS and mode!="autoq" else None))
    (out/"summary.json").write_text(json.dumps(dict(rows=rows,summary=summary,source_pin=PIN,
        binary_sha256=sha(binary),solver_sha256=sha(solver),autoq_sha256=sha(autoq),cap_s=CAP),indent=2)+"\n")
    for r in summary:print("CPS_MATCHED_MEDIAN",json.dumps(r),flush=True)
    print("CPS_MATCHED_SUMMARY",json.dumps(dict(arms=len(rows),periods=PERIODS,**{m:sum(r["mode"]==m and r["verdict"]!="UNKNOWN" for r in rows) for m in MODES})),flush=True)
if __name__=="__main__":
    if sys.argv[1]=="--worker":
        worker(pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]),pathlib.Path(sys.argv[4]),sys.argv[5])
    else:main(*map(lambda p:pathlib.Path(p).resolve(),sys.argv[1:6]))

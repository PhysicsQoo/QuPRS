#!/usr/bin/env python3
"""E1f: serialized-weight error certificate and bounded same-host solver pilot.
No production change. Retain all incomplete arms. Auto admission is separate.
"""
import ast,ctypes,functools,itertools,json,math,statistics,subprocess,sys
from fractions import Fraction as F
from pathlib import Path
from decimal import Decimal,localcontext,ROUND_CEILING
from eq_dag_e1d_parity import HEAD,TREE,read_snapshot,invert,replay
from eq_dag_e1e_encode import build as parity_build
from eq_dag_e1b_encode import build as flat_build
from eq_dag_d3_ab import sha,git,run as gpmc_run,compare,DELTA
from eq_dag_d3c_raw import run as raw_run,parity as count_parity,RAW

E1B="2addb665bd8015791c5ee7527a8ce0de5bf8e3a1"
E1E="7cf9e67d16e416b8bdd9f242afe668245f6421c4"
CASES=("wstate_16","wstate_8","vqe_16")
MODES=("archived","e1b","parity")
def upper(x):
    with localcontext() as c:
        c.prec=10;c.rounding=ROUND_CEILING
        return str(Decimal(x.numerator)/Decimal(x.denominator))
def trace_rank(n,domain,outputs):
    nonlinear={v for f in outputs.values() for m in f if len(m)>1 for v in m}
    cols={v:i for i,v in enumerate(v for v in domain if v not in nonlinear)}
    piv={}
    for i in range(n):
        x=0
        for m in outputs[i]+[(i,)]:
            if len(m)==1 and m[0] in cols:x^=1<<cols[m[0]]
        while x:
            k=x.bit_length()-1
            if k not in piv:piv[k]=x;break
            x^=piv[k]
    return len(piv)
def error_fn(lib):
    fn=ctypes.CDLL(str(lib)).phase_error
    fn.argtypes=[ctypes.c_char_p]*4;fn.restype=ctypes.c_double
    @functools.lru_cache(maxsize=131072)
    def err(c,r,a,b):
        x=fn(*(str(v).encode() for v in (c,r,a,b)))
        assert math.isfinite(x) and x>=0
        return F.from_float(x)
    # Negative controls: wrong sign and a visibly perturbed real weight.
    assert err(F(1,4),F(0),"0","-1")>=2
    assert err(F(0),F(0),"1.125","0")>=F(1,8)
    assert err(F(0),F(0),"1","0")==0
    return err
def audit_weights(path,build,err):
    text=path.read_text()
    weights=[]
    for line in text.splitlines():
        if line.startswith("c p weight "):
            a=line.split()
            if int(a[3])>0:weights.append((int(a[3]),a[4],a[5]))
    assert len({z for z,_,_ in weights})==len(weights)
    w=iter(sorted(weights));errors=[]
    def callback(c,bits):
        _,a,b=next(w)
        errors.append(err(c[0],c[1],a,b))
        return a,b
    e=build(callback)
    assert next(w,None) is None and e.render()==text
    return sum(errors,F(0)),len(errors)
def main():
    d,e1b,e1e,lib,gpmc,reader,rawdir,raw,out=map(lambda s:Path(s).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    for p,h,t in ((d,HEAD,TREE),(e1b,E1B,"f3c63a58c6a7ab651e0117e2a847ffa52b1c0f47"),(e1e,E1E,"8f3dc8351bf35185dfb6dc4eaa0cf0a1c90774bd")):
        assert (p/"head.txt").read_text().strip()==h and (p/"tree.txt").read_text().strip()==t
    assert subprocess.check_output(["git","-C",str(rawdir),"rev-parse","HEAD"],text=True).strip()==RAW
    assert json.loads((d/"provenance.json").read_text())["gpmc_sha256"]==sha(gpmc)
    err=error_fn(lib)
    src={r["case"]:r for r in map(json.loads,(d/"rows.jsonl").read_text().splitlines())}
    b={r["case"]:r for r in json.loads((e1b/"receipts.json").read_text())["rows"]}
    e={r["case"]:r for r in json.loads((e1e/"receipts.json").read_text())["rows"]}
    assert len(b)==len(e)==12 and set(b)==set(e)
    bounds=[]
    for case,r in e.items():
        a=b[case];s=src[case];arm=d/(case+"-hybrid");snap=arm/"residual.tsv"
        flat=e1b/(case+"-flat.cnf");candidate=e1e/(case+"-parity.cnf")
        assert sha(snap)==r["residual_sha256"]==a["source_residual_sha256"]==s["residual_sha256"]
        assert sha(arm/"actual.cnf")==r["original_cnf_sha256"]==a["original_cnf_sha256"]==s["cnf"]["sha256"]
        assert sha(flat)==a["flat_sha256"] and sha(e1b/(case+"-factored.cnf"))==r["e1b_sha256"]==a["factored_sha256"]
        assert sha(candidate)==r["cnf_sha256"] and a["weight_bits"]==r["weight_bits"]
        n,h,p,f=read_snapshot(snap.read_bytes())
        domain=ast.literal_eval(next(l.split("\t")[1] for l in snap.read_text().splitlines() if l.startswith("vars\t")))
        q,work=invert({m:c[1] for m,c in p.items() if c[1]})
        assert q is not None and work==r["subset_work"] and replay(q)=={m:c[1] for m,c in p.items() if c[1]}
        x,nx=audit_weights(flat,lambda cb:flat_build(domain,n,p,f,[],cb,a["weight_bits"]),err)
        y,ny=audit_weights(candidate,lambda cb:parity_build(domain,n,p,f,q,cb,a["weight_bits"])[0],err)
        assert nx==a["flat_weighted"] and ny==r["factors"]
        # Each weight is within e_i of ideal unit-modulus phase. Telescoping
        # through ideal products, any mixed product <= 1/(1-sum e_i).
        # Exact phase replay equates the two ideal products per assignment.
        total=x+y;assert total<1
        rank=trace_rank(n,domain,f)
        bound=total/(1-total)*F(2)**((h+1)//2-rank)
        row=dict(case=case,flat_error_sum=upper(x),parity_error_sum=upper(y),rank=rank,h=h,normalized_bound=upper(bound),passes_1e20=bound<=DELTA,passes_1e8=bound<=F(1,10**8),exact_fraction_bound=True)
        bounds.append(row);print("E1F_BOUND",json.dumps(row),flush=True)
    (out/"bounds.json").write_text(json.dumps(bounds,indent=2)+"\n")
    (out/"provenance.json").write_text(json.dumps(dict(head=git("rev-parse","HEAD"),d1=HEAD,e1b=E1B,e1e=E1E,raw_source=RAW,gpmc_sha256=sha(gpmc),reader_sha256=sha(reader),raw_sha256=sha(raw),interval_library_sha256=sha(lib),digits=30,raw_bits=100,cap=60,address_space_mib=4096,scope="one matched period per case; second parity and separate Auto admission for Wstate16; no E2E"),indent=2)+"\n")
    rows=[]
    for case in CASES:
        arm=d/(case+"-hybrid");n,h,_,_=read_snapshot((arm/"residual.tsv").read_bytes());k=2*n+h
        files=dict(archived=arm/"actual.cnf",e1b=e1b/(case+"-factored.cnf"),parity=e1e/(case+"-parity.cnf"))
        samples=[]
        def run(solver,mode,period,auto=False):
            folder=out/f"{case}-{period}-{solver}-{mode}"
            if solver=="gpmc":
                x=gpmc_run(gpmc,reader,files[mode],folder,k)
                if x["returncode"]==137:x.update(status="KILLED_137",rss_individual_kib=None)
                elif x["returncode"]==124:x["status"]="OUTER_TIMEOUT"
                if x["status"]=="COMPLETE" and set(x["reported_precision"])!={"30"}:x["status"]="PRECISION_MISMATCH"
            else:
                x=raw_run(raw,files[mode],folder,case=="wstate_16" and not auto)
            row=dict(solver=solver,mode=mode,period=period,auto_admission=auto,**x)
            assert row["cnf_sha256"]==sha(files[mode])
            samples.append(row);print("E1F_ARM",json.dumps(dict(case=case,**row)),flush=True)
        # Run new parity first for hard Wstate16; one full matched baseline
        # period only (avoid repeated known 60s timeouts).
        for solver in ("gpmc","rawmocs"):
            for mode in (tuple(reversed(MODES)) if case=="wstate_16" else MODES):
                run(solver,mode,1)
        if case=="wstate_16":
            run("rawmocs","parity",2);run("gpmc","parity",2)
            run("rawmocs","parity",3,True);run("rawmocs","parity",4,True)
        bad=[];comparisons=[]
        for x in samples:
            if x["status"] not in ("COMPLETE","TIMEOUT","OUTER_TIMEOUT","KILLED_137","RESOURCE_LIMIT","ROUTE_REJECTED"):
                bad.append([x["solver"],x["mode"],x["period"],x["status"]])
            if x["status"]=="COMPLETE" and x["solver"]=="gpmc":
                expected=src[case]["expected"]
                if x["verdict"] not in (("equivalent","equivalent*") if expected=="EQ" else ("not_equivalent",)):
                    bad.append(["expected",x["mode"],x["verdict"]])
        for a,b in itertools.combinations(samples,2):
            status=compare(a,b,k)["status"] if a["solver"]==b["solver"]=="gpmc" else count_parity(a,b,k)
            comparisons.append(status)
        row=dict(case=case,expected=src[case]["expected"],normalization_twice_log2=k,samples=samples,comparisons=dict((s,comparisons.count(s)) for s in set(comparisons)),unexpected=bad)
        rows.append(row);print("E1F_CASE",json.dumps({k:v for k,v in row.items() if k!="samples"}),flush=True)
        (out/"results.json").write_text(json.dumps(rows,indent=2)+"\n")
    summary=dict(arms=sum(len(r["samples"]) for r in rows),complete=sum(x["status"]=="COMPLETE" for r in rows for x in r["samples"]),disagreements=sum(r["comparisons"].get("DISAGREEMENT",0) for r in rows),paired_pass=sum(r["comparisons"].get("PASS",0) for r in rows),unexpected=sum(len(r["unexpected"]) for r in rows))
    print("E1F_SUMMARY",json.dumps(summary),flush=True)
    assert summary["arms"]==22 and summary["disagreements"]==summary["unexpected"]==0 and summary["paired_pass"]>0
if __name__=="__main__":
    main()

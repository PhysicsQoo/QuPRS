#!/usr/bin/env python3
"""RaWMoCS v0.2.2 independent same-CNF topology pilot, not cross-host ranking."""
import itertools,json,re,statistics,subprocess,sys,time
from fractions import Fraction
from pathlib import Path
from eq_dag_d2a_rewrite import replay
from eq_dag_phase_screen import read_snapshot
from eq_dag_d3_ab import sha,git,compare,DELTA
RAW="7ff6b1fdb772f16367fd1e094761a368d54f2ea7"
CASES=("wstate_16","grover-noancilla_negative_5","qwalk-noancilla_negative_5","vqe_16","qnn_12")
MODES=("flat","deep","balanced")
def run(binary,cnf,out,large):
    out.mkdir()
    args=["--digits","30","--solver","general" if large else "auto","--timeout-ms","60000"]
    if large: args+=["--large-general"]
    cmd=["prlimit","--as=4294967296","--","/usr/bin/time","-f","%M","-o",str(out/"rss.txt"),"timeout","--kill-after=2s","62",str(binary),*args,str(cnf)]
    start=time.monotonic()
    with (out/"stdout.txt").open("wb") as o,(out/"stderr.txt").open("wb") as e:
        p=subprocess.run(cmd,stdout=o,stderr=e)
    elapsed=time.monotonic()-start
    stdout=(out/"stdout.txt").read_text(errors="replace")
    stderr=(out/"stderr.txt").read_text(errors="replace")
    status={2:"INVALID_INPUT",3:"UNSUPPORTED_INPUT",4:"TIMEOUT",5:"RESOURCE_LIMIT",6:"ROUTE_REJECTED",7:"INTERNAL_ERROR",124:"OUTER_TIMEOUT",137:"KILLED_137"}.get(p.returncode,"PROCESS_ERROR")
    rss=(out/"rss.txt").read_text().strip().splitlines() if (out/"rss.txt").exists() else []
    x=dict(status=status,returncode=p.returncode,wall_s=elapsed,rss_individual_kib=int(rss[-1]) if rss and rss[-1].isdigit() and p.returncode!=137 else None,cnf_sha256=sha(cnf),args=args)
    x["route_diagnostics"]=[s for s in stderr.splitlines() if s.startswith(("RAWMOCS_","PREJOIN_"))]
    if p.returncode:
        if stdout.strip(): x["status"]="INVALID_PARTIAL_OUTPUT"
        return x
    ls=stdout.splitlines()
    assert len(ls)==2 and ls[0] in ("s SATISFIABLE","s UNSATISFIABLE")
    a=ls[1].split()
    assert a[:3]==["c","r","mpfr"] and len(a)==5
    re_,im=map(Fraction,a[3:])
    m=re.search(r"^RAWMOCS_COMPLETE route=(\S+) digits=30 bits=100 solve_ns=(\d+)$",stderr,re.M)
    assert m,stderr
    x.update(status="COMPLETE",real=str(re_),imag=str(im),sat=ls[0],route=m[1],solve_ns=int(m[2]))
    return x

def parity(a,b,k):
    if a["status"]!="COMPLETE" or b["status"]!="COMPLETE": return "INCOMPLETE"
    d=(Fraction(a["real"])-Fraction(b["real"]))**2+(Fraction(a["imag"])-Fraction(b["imag"]))**2
    return "PASS" if d<=Fraction(2)**k*DELTA**2 and ("sat" not in a or "sat" not in b or a["sat"]==b["sat"]) else "DISAGREEMENT"

def main():
    d1,d2,d3,d3b,rawdir,binary,out=map(lambda s:Path(s).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    assert subprocess.check_output(["git","-C",str(rawdir),"rev-parse","HEAD"],text=True).strip()==RAW
    for p,h in ((d1,"8811544a462338569bc5a375e3df41fdd18ea3b8"),(d2,"9c62004793c91f99213f782f3518f84267efb385"),(d3,"5fb621c803000c6d4ffc7e819c48fad0f4097536"),(d3b,"9e9b91e82bb7f7f29542e439e802dda955a6e8fb")):
        assert (p/"head.txt").read_text().strip()==h
    recs={r["case"]:r for r in json.loads((d2/"rewrite_receipts.json").read_text())["rows"]}
    old={r["case"]:r for r in map(json.loads,(d3/"cases.jsonl").read_text().splitlines())}
    bal={r["case"]:r for r in map(json.loads,(d3b/"cases.jsonl").read_text().splitlines())}
    (out/"provenance.json").write_text(json.dumps(dict(head=git("rev-parse","HEAD"),raw_commit=RAW,raw_binary_sha256=sha(binary),precision_digits=30,precision_bits=100,internal_timeout_ms=60000,outer_timeout_s=62,address_space_mib=4096,normalized_count_delta=str(DELTA),scope="within-RaWMoCS topology pilot; GPMC archived counts only, not cross-host speed ranking"),indent=2)+"\n")
    reports=[]
    for case in CASES:
        r=recs[case];arm=d1/(case+"-hybrid")
        flat=arm/"actual.cnf";deep=d2/(case+".cnf")
        assert sha(flat)==r["flat_sha256"] and sha(deep)==r["dag_sha256"] and sha(arm/"residual.tsv")==r["residual_sha256"]
        files=dict(flat=flat,deep=deep)
        if case in bal:
            files["balanced"]=d3b/(case+"-balanced.cnf")
            assert sha(files["balanced"])==bal[case]["structure"]["balanced_sha256"]
        for m,p in files.items():
            if m!="flat": replay(flat.read_text(),p.read_text())
        n,h,_,_=read_snapshot(arm/"residual.tsv");k=2*n+h
        # Same admission route across all variants of each case. Wstate16 exceeds
        # normal 4096-variable limit; explicit large General, never auto.
        large=case=="wstate_16"
        modes=tuple(files)
        samples={m:[] for m in modes}
        comparisons=[]
        references=[p["flat"] for p in old[case]["pairs"] if p["flat"]["status"]=="COMPLETE"]
        for i,order in enumerate((modes,tuple(reversed(modes))),1):
            for m in order:
                x=run(binary,files[m],out/f"{case}-{i}-{m}",large)
                x["archived_gpmc_count_parity"]=parity(x,references[0],k) if references else "NO_REFERENCE"
                samples[m].append(x)
                print("RAW_DAG_ARM",json.dumps(dict(case=case,period=i,mode=m,**x)),flush=True)
            for a,b in itertools.combinations(modes,2):
                comparisons.append(parity(samples[a][-1],samples[b][-1],k))
        within=[parity(v[0],v[1],k) for v in samples.values()]
        bad=sum(x=="DISAGREEMENT" for x in comparisons+within)+sum(x["archived_gpmc_count_parity"]=="DISAGREEMENT" for v in samples.values() for x in v)
        stats={m:dict(complete=sum(x["status"]=="COMPLETE" for x in v),statuses=[x["status"] for x in v],routes=[x.get("route") for x in v],median_wall_s=statistics.median(x["wall_s"] for x in v) if all(x["status"]=="COMPLETE" for x in v) else None,median_rss_kib=statistics.median(x["rss_individual_kib"] for x in v) if all(x["status"]=="COMPLETE" and x["rss_individual_kib"] is not None for x in v) else None) for m,v in samples.items()}
        ratios={m:stats["flat"]["median_wall_s"]/stats[m]["median_wall_s"] for m in modes if m!="flat" and not bad and stats["flat"]["complete"]==stats[m]["complete"]==2}
        record=dict(case=case,large_general=large,stats=stats,solver_speedups=ratios,disagreements=bad,comparisons=comparisons,within=within,samples=samples)
        reports.append(record)
        print("RAW_DAG_CASE",json.dumps({k:v for k,v in record.items() if k!="samples"}),flush=True)
    summary=dict(cases=len(reports),arms=sum(len(v) for r in reports for v in r["samples"].values()),disagreements=sum(r["disagreements"] for r in reports),complete=sum(x["status"]=="COMPLETE" for r in reports for v in r["samples"].values() for x in v),scope="screening only")
    (out/"results.json").write_text(json.dumps(dict(summary=summary,rows=reports),indent=2)+"\n")
    print("RAW_DAG_SUMMARY",json.dumps(summary),flush=True)
    assert summary["arms"]==28 and summary["disagreements"]==0
    assert not any(x["status"]=="INVALID_PARTIAL_OUTPUT" for r in reports for v in r["samples"].values() for x in v)
if __name__=="__main__":
    main()

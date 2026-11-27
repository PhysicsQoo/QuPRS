#!/usr/bin/env python3
"""Same-CPS Boolean encoder A/B; exact bins, not a new verification mode.
Four alternating periods. Timings here are solver-stage, not full E2E."""
import csv
import hashlib
import json
import pathlib
import statistics
import subprocess
import sys
import time
from fractions import Fraction
from hoare_ganak_exact import single_fibre_pack, single_fibre_decode, parse_gpmc_integer

directory,solver=map(pathlib.Path,sys.argv[1:3])
rows=list(csv.DictReader((directory/"manifest.tsv").open(),delimiter="\t"))
assert len(rows)==36
groups={}
for row in rows:
    key=tuple(row[x] for x in ("case","variant","route"))
    groups.setdefault(key,{})[row["encoding"]]=row
assert len(groups)==18 and all(set(g)=={"flat","dag"} for g in groups.values())
records=[]
for period in range(4):
    keys=list(groups)
    if period%2:keys.reverse()
    for key in keys:
        group=groups[key]
        pair={}
        for encoding in (("flat","dag") if period%2==0 else ("dag","flat")):
            row=group[encoding]
            n,k,h,steps,primary,v,c,encode_ns=map(int,(row[x] for x in ("n","k","h","steps","primary","vars","clauses","encode_ns")))
            stem=directory/("-".join(key)+"-"+encoding)
            base=stem.with_suffix(".cnf").read_text()
            assert base.splitlines()[0]==f"p cnf {v} {c}"
            packed,radix,bound=single_fibre_pack(base,list(map(int,row["phase"].split(","))),primary)
            query=stem.with_suffix(".packed.cnf");query.write_text(packed)
            log=stem.with_suffix(f".{period}.log")
            t=time.monotonic()
            p=subprocess.run(["/usr/bin/time","-f","%M","-o",str(stem.with_suffix(f".{period}.rss")),"timeout","--kill-after=1s","4",str(solver),"-mode=1","-natw",str(query)],capture_output=True,text=True)
            elapsed=time.monotonic()-t
            log.write_text(p.stdout+p.stderr)
            bins=None
            status="TIMEOUT" if p.returncode in (124,137) else "ERROR"
            if p.returncode==0:
                bins=single_fibre_decode(parse_gpmc_integer(p.stdout,"wmc",bound*radix**7),radix,bound,8)
                assert all(bins[j]==0 for j in (1,2,3,5,6,7)),bins
                mass=Fraction(bins[0]-bins[4])*Fraction(2)**(-k)
                case,variant,_=key
                expected=Fraction(0) if case=="bv03" and variant=="relative" else Fraction(3249,4096)*(8 if case=="mogrover03" else 1) if variant=="relative" else Fraction(8 if case=="mogrover03" else 1)
                assert mass==expected,(key,encoding,mass,expected)
                status="EXACT"
            rss=stem.with_suffix(f".{period}.rss").read_text().split()
            rec=dict(case=key[0],variant=key[1],route=key[2],encoding=encoding,period=period,
                     n=n,k=k,h=h,steps=steps,primary=primary,vars=v,clauses=c,encode_ns=encode_ns,
                     solver_s=elapsed,rss_kib=int(rss[-1]) if rss and rss[-1].isdigit() else None,
                     status=status,bins=bins,cnf_sha256=hashlib.sha256(base.encode()).hexdigest(),
                     ir_sha256=hashlib.sha256((directory/("-".join(key)+".ir")).read_bytes()).hexdigest())
            records.append(rec);pair[encoding]=rec
            print("CPS_ENCODING_ARM",json.dumps(rec),flush=True)
        a,b=pair["flat"],pair["dag"]
        assert all(a[x]==b[x] for x in ("n","k","h","steps","primary","ir_sha256"))
        if a["status"]==b["status"]=="EXACT":assert a["bins"]==b["bins"],key
        assert a["status"]=="EXACT","established flat source regression"
summary=[]
for key,group in groups.items():
    out=dict(case=key[0],variant=key[1],route=key[2])
    for enc in ("flat","dag"):
        rs=[r for r in records if (r["case"],r["variant"],r["route"],r["encoding"])==(*key,enc)]
        assert len(rs)==4
        out[enc]=dict(exact=sum(r["status"]=="EXACT" for r in rs),vars=rs[0]["vars"],clauses=rs[0]["clauses"],encode_ns=rs[0]["encode_ns"],
                      median_solver_s=statistics.median(r["solver_s"] for r in rs) if all(r["status"]=="EXACT" for r in rs) else None,
                      median_rss_kib=statistics.median(r["rss_kib"] for r in rs) if all(r["rss_kib"] is not None for r in rs) else None)
    summary.append(out);print("CPS_ENCODING_MEDIAN",json.dumps(out),flush=True)
(directory/"summary.json").write_text(json.dumps(dict(rows=records,summary=summary),indent=2)+"\n")
print("CPS_ENCODING_SUMMARY",json.dumps(dict(arms=len(records),pairs=18,periods=4,flat_exact=sum(r["status"]=="EXACT" and r["encoding"]=="flat" for r in records),dag_exact=sum(r["status"]=="EXACT" and r["encoding"]=="dag" for r in records))),flush=True)

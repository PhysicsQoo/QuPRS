#!/usr/bin/env python3
"""Source CPS three-mode decision smoke. Equal 4s solver-stage caps, not a
matched end-to-end performance benchmark. All decisions precede oracle checks."""
import csv
import hashlib
import json
import pathlib
import subprocess
import sys
import time
from fractions import Fraction
from hoare_ganak_exact import single_fibre_pack, single_fibre_decode, parse_gpmc_integer

directory, solver = map(pathlib.Path, sys.argv[1:3])
rows = list(csv.DictReader((directory / "manifest.tsv").open(), delimiter="\t"))
assert len(rows) == 27
records = {}
CAP = 4
def sign(a,b):
    if a==0:
        return (b>0)-(b<0)
    if b==0 or (a>0)==(b>0):
        return (a>0)-(a<0)
    cmp=(a*a>2*b*b)-(a*a<2*b*b)
    return cmp if a>0 else -cmp

for row in rows:
    case, variant, mode = (row[x] for x in ("case","variant","mode"))
    key=(case,variant,mode)
    assert key not in records and row["label"]=="PASS"
    k,h,n,steps,primary,v,c,oa,ob,ok,rr_ns,encode_ns = (
        int(row[x]) for x in ("k","h","n","steps","primary","vars","clauses",
                              "oracle_a","oracle_b","oracle_k","rr_ns","encode_ns"))
    status=row["status"]
    verdict=status if status!="READY" else "UNKNOWN"
    reason="algebraic" if status in ("PROVED","REFUTED") else "residual"
    stem=directory/f"{case}-{variant}-{mode}"
    rec=dict(case=case,variant=variant,mode=mode,k=k,h=h,n=n,steps=steps,
             primary=primary,vars=v,clauses=c,rr_ns=rr_ns,encode_ns=encode_ns,
             initial_sha256=hashlib.sha256((directory/row["initial"]).read_bytes()).hexdigest(),
             expected=row["expected"],solver_s=0,solver_invoked=False)
    if status=="READY":
        assert mode!="rr"
        base=stem.with_suffix(".cnf").read_text()
        assert base.splitlines()[0]==f"p cnf {v} {c}"
        packed,radix,bound=single_fibre_pack(base,list(map(int,row["phase"].split(","))),primary)
        query=stem.with_suffix(".packed.cnf");query.write_text(packed)
        rec.update(solver_invoked=True,cnf_sha256=hashlib.sha256(base.encode()).hexdigest(),
                   packed_sha256=hashlib.sha256(packed.encode()).hexdigest())
        start=time.monotonic()
        try:
            proc=subprocess.run([str(solver),"-mode=1","-natw",str(query)],
                                capture_output=True,text=True,timeout=CAP)
            rec["returncode"]=proc.returncode
            stdout,stderr=proc.stdout,proc.stderr
            if proc.returncode:
                reason="SOLVER_ERROR"
            else:
                try:
                    bins=single_fibre_decode(parse_gpmc_integer(stdout,"wmc",bound*radix**7),radix,bound,8)
                except (ValueError,OverflowError):
                    reason="INVALID_COUNT"
                else:
                    assert all(bins[i]==bins[-i%8] for i in range(8)),(key,bins)
                    a,b=bins[0]-bins[4],bins[1]-bins[3]
                    norm=(Fraction(a)*Fraction(2)**(-k),Fraction(b)*Fraction(2)**(-k))
                    diff=sign(norm[0]-(1<<n),norm[1])
                    assert sign(*norm)>=0 and diff<=0,(key,norm)
                    verdict="PROVED" if diff==0 else "REFUTED"
                    reason="EXACT"
                    rec.update(bins=bins,norm=list(map(str,norm)))
                    # Numerical independent oracle is a gate, never a
                    # source of a definite decision for a timed-out arm.
                    assert norm==(Fraction(oa)*Fraction(2)**(-ok),Fraction(ob)*Fraction(2)**(-ok)),(key,norm)
        except subprocess.TimeoutExpired as exc:
            reason="TIMEOUT"
            stdout,stderr=exc.stdout or b"",exc.stderr or b""
        rec["solver_s"]=time.monotonic()-start
        for suffix,data in ((".stdout",stdout),(".stderr",stderr)):
            stem.with_suffix(suffix).write_bytes(data.encode() if isinstance(data,str) else data)
    assert verdict in ("UNKNOWN",row["expected"]),(key,verdict,row["expected"])
    if mode=="rr":
        assert not rec["solver_invoked"]
    if mode=="wmc":
        assert rec["solver_invoked"] and steps==0
    rec.update(verdict=verdict,reason=reason)
    records[key]=rec
    print("CPS_CORE_DECISION_ARM",json.dumps(rec),flush=True)
for case in ("bv03","grover03","mogrover03"):
    for variant in ("source","relative","global"):
        group=[records[case,variant,m] for m in ("rr","wmc","hybrid")]
        assert len({r["initial_sha256"] for r in group})==1
        if case=="bv03":
            assert group[1]["verdict"]==group[1]["expected"]
            assert group[2]["verdict"]==group[2]["expected"]
summary={mode:dict(definite=sum(r["verdict"]!="UNKNOWN" for r in records.values() if r["mode"]==mode),
                   queries=sum(r["solver_invoked"] for r in records.values() if r["mode"]==mode))
         for mode in ("rr","wmc","hybrid")}
(directory/"summary.json").write_text(json.dumps(list(records.values()),indent=2)+"\n")
print("CPS_CORE_DECISION_SUMMARY",json.dumps(dict(arms=len(records),pairs=9,**summary)),flush=True)

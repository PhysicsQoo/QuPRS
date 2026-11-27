#!/usr/bin/env python3
"""Guard-only exact cofactor histogram. No quantum verdict or RR admission."""
import collections
import csv
import hashlib
import json
import pathlib
import subprocess
import sys
import time
from hoare_ganak_exact import single_fibre_pack, single_fibre_decode, parse_gpmc_integer

directory, solver = map(pathlib.Path, sys.argv[1:3])
rows = list(csv.DictReader((directory / "manifest.tsv").open(), delimiter="\t"))
assert rows[0]["key"] == "smoke" and len(rows) == 16
assert len({r["key"] for r in rows}) == len(rows)
records = []
for row in rows:
    key = row["key"]
    rec = dict(key=key, classification="UNKNOWN")
    if row["primary"] == "-":
        rec["reason"] = "ENCODER_UNSUPPORTED"
    else:
        p,v,c = (int(row[x]) for x in ("primary","vars","clauses"))
        base = (directory / (key+".cnf")).read_text()
        assert base.splitlines()[0] == f"p cnf {v} {c}"
        packed,radix,bound = single_fibre_pack(base,list(map(int,row["phase"].split(","))),p)
        query = directory / (key+".packed.cnf")
        query.write_text(packed)
        rec.update(primary=p,vars=v,clauses=c,cnf_sha256=hashlib.sha256(base.encode()).hexdigest(),
                   packed_sha256=hashlib.sha256(packed.encode()).hexdigest())
        start=time.monotonic()
        try:
            run=subprocess.run([str(solver),"-mode=1","-natw",str(query)],capture_output=True,text=True,timeout=2)
        except subprocess.TimeoutExpired:
            rec["reason"]="SOLVER_TIMEOUT"
        else:
            (directory/(key+".stdout")).write_text(run.stdout)
            (directory/(key+".stderr")).write_text(run.stderr)
            if run.returncode:
                rec.update(reason="SOLVER_ERROR",returncode=run.returncode)
            else:
                try:
                    bins=single_fibre_decode(parse_gpmc_integer(run.stdout,"wmc",bound*radix**3),radix,bound,4)
                except (ValueError,OverflowError):
                    rec["reason"]="INVALID_COUNT"
                else:
                    assert sum(bins)==bound,(key,bins,bound)
                    n0,n1,n2=bins[0],bins[1]+bins[2],bins[3]
                    kind=("ZERO" if not(n1 or n2) else "FIXED_TWO" if not n1 else
                          "FIXED_ONE" if not n2 else "MIXED_ONE_TWO")
                    rec.update(classification=kind,reason="EXACT",bins=bins,multiplicity=[n0,n1,n2])
        rec["solver_s"]=time.monotonic()-start
    if key=="smoke":
        assert rec.get("bins")==[1,1,1,1],rec
    else:
        records.append(rec)
    print("CPS_CORE8_ELIM_ARM",json.dumps(rec),flush=True)
hist=dict(collections.Counter(r["classification"] for r in records))
(directory/"summary.json").write_text(json.dumps(dict(rows=records,classification=hist),indent=2)+"\n")
print("CPS_CORE8_ELIM_SUMMARY",json.dumps(dict(candidates=len(records),classification=hist)),flush=True)

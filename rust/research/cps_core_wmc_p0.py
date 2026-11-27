#!/usr/bin/env python3
"""CORE-3 exact GPMC raw/residual parity, existing packed WMC transport."""
import csv
import hashlib
import json
import pathlib
import subprocess
import sys
import time
from fractions import Fraction
from hoare_ganak_exact import single_fibre_pack, single_fibre_decode, parse_gpmc_integer

directory, solver = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
rows = list(csv.DictReader((directory / "manifest.tsv").open(), delimiter="\t"))
assert len(rows) == 28
records = {}
sparse_flat=sparse_dag=0
for row in rows:
    case, route = row["case"], row["route"]
    key = (case, route)
    assert key not in records
    k, h, steps, primary, v, c, a, b = (int(row[x]) for x in ("k", "h", "steps", "primary", "vars", "clauses", "a", "b"))
    base = (directory / f"{case}-{route}.cnf").read_text()
    assert base.splitlines()[0] == f"p cnf {v} {c}"
    packed, radix, bound = single_fibre_pack(base, list(map(int, row["phase"].split(","))), primary)
    query = directory / f"{case}-{route}.packed.cnf"
    query.write_text(packed)
    t = time.monotonic()
    run = subprocess.run([str(solver), "-mode=1", "-natw", str(query)], capture_output=True, text=True, timeout=10, check=True)
    elapsed = time.monotonic() - t
    (directory / f"{case}-{route}.stdout").write_text(run.stdout)
    (directory / f"{case}-{route}.stderr").write_text(run.stderr)
    bins = single_fibre_decode(parse_gpmc_integer(run.stdout, "wmc", bound * radix**7), radix, bound, 8)
    assert all(bins[i] == bins[-i % 8] for i in range(8)), (key, bins)
    coeff = (bins[0] - bins[4], bins[1] - bins[3])
    assert coeff == (a,b), (key, coeff, (a,b))
    # Exact normalized norm: coefficients in Q(sqrt(2)), including k<0.
    norm = tuple(Fraction(x) * Fraction(2)**(-k) for x in coeff)
    rec = dict(case=case, route=route, k=k, h=h, steps=steps, primary=primary, vars=v, clauses=c,
               bins=bins, coeff=coeff, norm=list(map(str,norm)), solver_s=elapsed,
               cnf_sha256=hashlib.sha256(base.encode()).hexdigest(),
               packed_sha256=hashlib.sha256(packed.encode()).hexdigest())
    for tag in ("sparse-flat","sparse-dag"):
        stem=directory/f"{case}-{route}.{tag}"
        base_path=pathlib.Path(str(stem)+".cnf")
        if not base_path.is_file():
            assert tag=="sparse-dag",key
            continue
        sparse=base_path.read_text()
        phase=list(map(int,pathlib.Path(str(stem)+".phase").read_text().split(",")))
        packed_w,radix_w,bound_w=single_fibre_pack(sparse,phase,primary)
        q=pathlib.Path(str(stem)+".packed.cnf");q.write_text(packed_w)
        run_w=subprocess.run([str(solver),"-mode=1","-natw",str(q)],capture_output=True,text=True,timeout=10,check=True)
        pathlib.Path(str(stem)+".stdout").write_text(run_w.stdout)
        pathlib.Path(str(stem)+".stderr").write_text(run_w.stderr)
        wb=single_fibre_decode(parse_gpmc_integer(run_w.stdout,"wmc",bound_w*radix_w**7),radix_w,bound_w,8)
        assert wb==bins,(key,tag,wb,bins)
        if tag=="sparse-flat":sparse_flat+=1
        else:sparse_dag+=1
    records[key] = rec
    print("CPS_CORE_WMC_ARM", json.dumps(rec), flush=True)
pairs = sorted({r["case"] for r in records.values()})
changed = 0
for case in pairs:
    raw, residual = records[case,"raw"], records[case,"residual"]
    assert raw["norm"] == residual["norm"], case
    changed += residual["steps"] > 0
    assert residual["h"] <= raw["h"]
assert changed > 0
assert records["negative-scale","residual"]["k"] < 0
assert records["radical","raw"]["coeff"][1] != 0
assert records["cancellation","raw"]["coeff"] == (0,0) and sum(records["cancellation","raw"]["bins"]) > 0
assert sum(records["zero-guard","raw"]["bins"]) == 0
print("CPS_CORE_WMC_SUMMARY", json.dumps(dict(arms=len(records), pairs=len(pairs), changed=changed, negative_scale=True, radical=True, cancellation=True, zero_guard=True)))

assert sparse_flat==28 and sparse_dag>0
print("CPS_SPARSE_WMC_PARITY",json.dumps(dict(flat=sparse_flat,dag=sparse_dag,full_bins="PASS")),flush=True)

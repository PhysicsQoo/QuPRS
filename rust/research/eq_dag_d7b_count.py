#!/usr/bin/env python3
"""Same sealed Feynman inputs, native GPMC 30/90 digit diagnosis only."""
import json,subprocess,sys,time
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal,localcontext
from eq_dag_d3_ab import sha
from eq_dag_e1d_parity import read_snapshot
def main():
    src,gpmc,reader,out=map(lambda p:Path(p).resolve(),sys.argv[1:])
    out.mkdir(parents=True,exist_ok=False)
    prov=json.loads((src/"provenance.json").read_text())
    assert sha(gpmc)==prov["gpmc_sha256"]
    rows=list(map(json.loads,(src/"rows.jsonl").read_text().splitlines()))
    case="feynman_grover_5_eq";rr=[]
    for variant in ("main","combined"):
        rec=next(x for x in rows if x["case"]==case and x["variant"]==variant)
        d=src/f"{case}-1-{variant}";cnf=d/"actual.cnf";snap=d/"residual.tsv"
        assert sha(cnf)==rec["cnf"]["sha256"] and sha(snap)==rec["residual_sha256"]
        n,h,_,_=read_snapshot(snap.read_bytes());k=2*n+h
        for digits in (30,90):
            a=out/f"{variant}-{digits}";a.mkdir()
            cmd=["prlimit","--as=4294967296","--","/usr/bin/time","-f","%M","-o",str(a/"rss.txt"),"timeout","--kill-after=2s","60",str(gpmc),"-mode=1"]+(["-prec=90"] if digits==90 else [])+[str(cnf)]
            t=time.monotonic()
            with (a/"stdout.txt").open("wb") as stdout,(a/"stderr.txt").open("wb") as stderr:p=subprocess.run(cmd,stdout=stdout,stderr=stderr)
            row=dict(variant=variant,digits=digits,returncode=p.returncode,wall_s=time.monotonic()-t,cnf_sha256=sha(cnf),n=n,h=h,normalization_twice_log2=k)
            if p.returncode==0:
                raw=(a/"stdout.txt").read_text(errors="replace")
                row["reported_precision"]=[l.split()[-1] for l in raw.splitlines() if l.startswith("c o precision ")]
                x=subprocess.run([str(reader),str(a/"stdout.txt"),str(k)],capture_output=True,text=True)
                (a/"reader.txt").write_text(x.stdout+"\n"+x.stderr)
                if x.returncode==0:
                    re,im,v,fmt=x.stdout.strip().split("\t")
                    normsq=(F(re)**2+F(im)**2)/F(2)**k
                    with localcontext() as c:
                        c.prec=80
                        norm=Decimal(normsq.numerator)/Decimal(normsq.denominator)
                        row.update(real=re,imag=im,verdict=v,format=fmt,normalized_trace_abs=str(norm.sqrt()),normalized_trace_abs_squared=str(norm))
                else:row["reader_error"]=x.returncode
            rr.append(row);print("D7B_COUNT",json.dumps(row),flush=True)
    (out/"counts.json").write_text(json.dumps(dict(rows=rr,scope="diagnostic raw counts; original EQ discrepancy unresolved until localized"),indent=2)+"\n")
if __name__=="__main__":main()

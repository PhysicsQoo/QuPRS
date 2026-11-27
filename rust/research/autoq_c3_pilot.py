#!/usr/bin/env python3
"""C3 first matched native pilot: process-isolated same-family budget.

Uses existing exact packed GPMC CNF overlap, not a dense-oracle baseline.
GNU time max RSS is a process-tree peak individual RSS, not summed RSS.
AutoQ timing is intentionally not mixed into this native ablation.
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

from hoare_ganak_exact import (
    single_fibre_pack, single_fibre_decode, parse_gpmc_integer,
)

CAP = 4.0
MODES = ("rr", "wmc", "hybrid", "structural")
CASES = {
    "ghz3": "PROVED", "ghz5": "PROVED", "ghz8": "PROVED",
    "ghz3-plus": "REFUTED", "ghz3-broken": "REFUTED",
    "bv03": "PROVED", "grover03": "PROVED", "mogrover03": "PROVED",
}

def arm(binary, solver, case, mode, folder):
    start = time.monotonic()
    cnf = folder / "base.cnf"
    env = dict(os.environ, AQ_C3_CASE=case, AQ_C3_MODE=mode,
               AQ_C3_CNF=str(cnf), AQ_C3_BUDGET_MS=str(int(CAP*1000)))
    proc = subprocess.Popen([str(binary), "--exact",
        "exact_property_cnf::hoare_autoq_c3_arm", "--nocapture"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, env=env)
    queries = 0
    failures = 0
    native = None
    with (folder/"native.log").open("w") as log, (folder/"solver.jsonl").open("w") as sol:
        for line in proc.stdout:
            log.write(line)
            if "AQ_C3_QUERY " in line:
                primary, k, phase, rem = line.split("AQ_C3_QUERY ",1)[1].split()
                primary,k,rem = int(primary),int(k),int(rem)
                queries += 1
                result = "UNKNOWN"
                record = dict(query=queries, status="UNKNOWN")
                t = time.monotonic()
                try:
                    base = cnf.read_text()
                    data, radix, bound = single_fibre_pack(base,list(map(int,phase.split(","))),primary)
                    packed = folder/"packed.cnf"
                    packed.write_text(data)
                    remaining = min(rem/1000, CAP-(time.monotonic()-start))
                    if remaining <= 0:
                        raise TimeoutError("whole-family budget")
                    run = subprocess.run([str(solver),"-mode=1","-natw",str(packed)],
                                         capture_output=True,text=True,timeout=remaining)
                    if run.returncode != 0:
                        raise RuntimeError(f"GPMC exit {run.returncode}")
                    value = parse_gpmc_integer(run.stdout,"wmc",bound*radix**7)
                    bins = single_fibre_decode(value,radix,bound,8)
                    a,b,c,d = (bins[j]-bins[j+4] for j in range(4))
                    real = a*a+b*b+c*c+d*d
                    radical = a*b+b*c+c*d-a*d
                    result = "PROVED" if radical==0 and real==(1<<k) else "REFUTED"
                    record.update(status="EXACT",bins=bins,base_sha256=hashlib.sha256(base.encode()).hexdigest(),
                                  packed_sha256=hashlib.sha256(data.encode()).hexdigest())
                except (TimeoutError, subprocess.TimeoutExpired, RuntimeError, ValueError) as e:
                    failures += 1
                    record.update(error=type(e).__name__, detail=str(e)[:300])
                record["elapsed_s"] = time.monotonic()-t
                sol.write(json.dumps(record)+"\n");sol.flush()
                proc.stdin.write(result+"\n");proc.stdin.flush()
            if "AQ_C3_NATIVE " in line:
                assert native is None
                native = dict(x.split("=",1) for x in line.split("AQ_C3_NATIVE ",1)[1].split())
    rc=proc.wait()
    elapsed=time.monotonic()-start
    assert rc==0 and native is not None, (rc,case,mode)
    assert native["case"]==case and native["mode"]==mode and int(native["queries"])==queries
    verdict=native["verdict"] if elapsed<=CAP else "UNKNOWN"
    assert verdict=="UNKNOWN" or verdict==CASES[case], native
    print(json.dumps(dict(case=case,mode=mode,verdict=verdict,native=native,
                         queries=queries,solver_failures=failures,worker_wall_s=elapsed)))

def main():
    binary, solver, out = (pathlib.Path(x).resolve() for x in sys.argv[1:4])
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    # Reversed order in the second period, including cases. No shared Rust
    # state, solver subprocess or CNF across arms. Build is excluded equally.
    for period in range(2):
        cases=list(CASES) if period==0 else list(reversed(CASES))
        modes=MODES if period==0 else tuple(reversed(MODES))
        for case in cases:
            for mode in modes:
                folder=out/f"{period}-{case}-{mode}";folder.mkdir()
                t=time.monotonic()
                p=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(folder/"resource.txt"),
                    "timeout","--kill-after=1s",str(CAP),
                    sys.executable,str(pathlib.Path(__file__).resolve()),"--arm",
                    str(binary),str(solver),case,mode,str(folder)],
                    text=True,capture_output=True)
                elapsed=time.monotonic()-t
                (folder/"worker.stdout").write_text(p.stdout)
                (folder/"worker.stderr").write_text(p.stderr)
                if p.returncode in (124,137):
                    row=dict(case=case,mode=mode,verdict="UNKNOWN",reason="PROCESS_TIMEOUT",
                             queries=None,solver_failures=None)
                else:
                    assert p.returncode==0,(case,mode,p.stderr,p.stdout)
                    row=json.loads(p.stdout)
                if elapsed>CAP+0.05:
                    row.update(verdict="UNKNOWN",reason="OUTER_DEADLINE")
                resource=(folder/"resource.txt").read_text().split() if (folder/"resource.txt").exists() else []
                row.update(period=period,budget_s=CAP,process_wall_s=elapsed,
                           max_rss_kib=int(resource[-1]) if len(resource)>=2 and resource[-1].isdigit() else None)
                assert row["verdict"] in ("UNKNOWN",CASES[case])
                rows.append(row);print("AQ_C3_ARM "+json.dumps(row),flush=True)
    assert len(rows)==2*len(CASES)*len(MODES)
    # Correctness/route gate, not a speedup gate.
    for p in (0,1):
        for c in ("ghz3","ghz5","ghz8","ghz3-plus"):
            r=next(r for r in rows if r["period"]==p and r["case"]==c and r["mode"]=="structural")
            assert r["verdict"]==CASES[c] and r["queries"]==0 and r["native"]["route"]=="symbolic",r
    summary={m:dict(arms=sum(r["mode"]==m for r in rows),
                    definite=sum(r["mode"]==m and r["verdict"]!="UNKNOWN" for r in rows),
                    known_queries=sum(r["queries"] or 0 for r in rows if r["mode"]==m),
                    censored=sum(r["mode"]==m and r["queries"] is None for r in rows)) for m in MODES}
    (out/"summary.json").write_text(json.dumps(dict(rows=rows,summary=summary,
        binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
        gpmc_sha256=hashlib.sha256(solver.read_bytes()).hexdigest()),indent=2)+"\n")
    print("AQ_C3_SUMMARY "+json.dumps(summary),flush=True)

if __name__=="__main__":
    if sys.argv[1]=="--arm":
        arm(pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]),sys.argv[4],sys.argv[5],pathlib.Path(sys.argv[6]))
    else:
        main()

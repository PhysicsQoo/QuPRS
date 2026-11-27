#!/usr/bin/env python3
"""C3 first matched native pilot: process-isolated same-family budget.

Uses existing exact packed GPMC CNF overlap, not a dense-oracle baseline.
GNU time max RSS is a process-tree peak individual RSS, not summed RSS.
C3-R2 adds phase-blind support indexing and same-budget AutoQ.
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
MODES = ("wmc", "hybrid-support", "hybrid-direct", "structural", "structural-factor", "autoq")
CASES = {
    "ghz3": "PROVED", "ghz5": "PROVED", "ghz8": "PROVED",
    "ghz3-plus": "REFUTED", "ghz3-broken": "REFUTED",
    "bv03": "PROVED", "grover03": "PROVED", "mogrover03": "PROVED",
    "grover03-relative": "REFUTED", "mogrover03-relative": "REFUTED",
    "grover04": "PROVED", "mogrover04": "PROVED",
}

from autoq_decision_pair import BLOBS, GHZ_BLOBS, SHAPES, PIN, blob, classify, replace_once

HELDOUT = {
    "grover04": (("3cb06685b906e4a7da6adab65bd6b472370fe800","c5a97b5c984fb0ea92bfaa624ee41fccf875ece6","2493f92a4ae9b335b30b86d5d17aa70902402b13"),(7,100)),
    "mogrover04": (("2b1c53ee628ef52edeeb09bf0dc70f1d601f968c","5e63ffba67c329e6fcb14693122c35cd0f004728","56e26972835eb604ee7ffd005ae0f10cdd081697"),(11,120)),
}

def prepare_autoq(root, out):
    fixtures=out/"source"
    fixtures.mkdir()
    assert subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()==PIN
    specs={}
    for case in CASES:
        if case.startswith("ghz"):
            n=int(case[3:].split("-")[0])
            folder=root/"benchmarks"/"all"/"GHZall"/f"{n:03d}"
            hashes=GHZ_BLOBS[n];shape=(n,n)
        else:
            key=case.removesuffix("-relative")
            family={"bv":"BV","grover":"Grover","mogrover":"MOGrover"}[key[:-2]]
            folder=root/"benchmarks"/"all"/family/key[-2:]
            hashes,shape=HELDOUT[key] if key in HELDOUT else (BLOBS[key],SHAPES[key])
        names=("pre.hsl","post.hsl","circuit.qasm")
        data=[(folder/f).read_bytes() for f in names]
        assert tuple(map(blob,data))==hashes,(case,folder)
        if case.endswith("-relative"):
            data[1]=replace_once(data[1],b"aH := 11 /",b"aH := -11 /")
        if case.endswith("-plus"):
            parts=data[1].split(" ∪\n".encode())
            assert len(parts)==2
            data[1]=replace_once(parts[0]+b"\n",b"cn := -1/sqrt2\n",b"")
        if case.endswith("-broken"):
            lines=data[2].rstrip().splitlines()
            assert lines[-1].strip().startswith(b"cx ")
            data[2]=b"\n".join(lines[:-1])+b"\n"
            shape=(shape[0],shape[1]-1)
        dest=fixtures/case
        dest.mkdir()
        for name,content in zip(names,data):
            (dest/name).write_bytes(content)
        specs[case]=dict(shape=shape,blobs=hashes,sha256=[hashlib.sha256(d).hexdigest() for d in data])
    (fixtures/"manifest.json").write_text(json.dumps(specs,indent=2)+"\n")
    return fixtures

def autoq_arm(exe, fixtures, case, folder):
    start=time.monotonic()
    spec=json.loads((fixtures/"manifest.json").read_text())[case]
    f=fixtures/case
    p=subprocess.run([str(exe),"ver",str(f/"pre.hsl"),str(f/"circuit.qasm"),str(f/"post.hsl")],
                     capture_output=True,text=True,errors="replace")
    (folder/"autoq.stdout").write_text(p.stdout)
    (folder/"autoq.stderr").write_text(p.stderr)
    actual=classify(p.stdout,p.stderr,p.returncode,tuple(spec["shape"]))
    verdict=actual if actual in ("PROVED","REFUTED") else "UNKNOWN"
    assert verdict=="UNKNOWN" or verdict==CASES[case],(case,actual)
    print(json.dumps(dict(case=case,mode="autoq",verdict=verdict,autoq_status=actual,
                         returncode=p.returncode,queries=None,solver_failures=None,
                         worker_wall_s=time.monotonic()-start)))

def arm(binary, solver, case, mode, folder):
    start = time.monotonic()
    cnf = folder / "base.cnf"
    env = dict(os.environ, AQ_C3_CASE=case, AQ_C3_MODE=mode,
               AQ_C3_CNF=str(cnf), AQ_C3_BUDGET_MS=str(int(CAP*1000)))
    native_test=os.environ.get("AQ_C3_NATIVE_TEST","exact_property_cnf::hoare_autoq_c3_arm")
    assert native_test in ("exact_property_cnf::hoare_autoq_c3_arm","exact_property_cnf::hoare_autoq_shared_fixed_basis_arm","exact_property_cnf::hoare_autoq_ss2_arm")
    proc = subprocess.Popen([str(binary), "--exact", native_test, "--nocapture"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, env=env)
    queries = 0
    failures = 0
    native = None
    with (folder/"native.log").open("w") as log, (folder/"solver.jsonl").open("w") as sol:
        for line in proc.stdout:
            log.write(line)
            if os.environ.get("AQ_SHARED_FAMILY"):log.flush()
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
    autoq, source_root = (pathlib.Path(x).resolve() for x in sys.argv[4:6])
    version=subprocess.check_output([str(autoq),"-v"],text=True,stderr=subprocess.STDOUT,timeout=10)
    assert PIN in version
    fixtures=prepare_autoq(source_root,out)
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
                args=(["--autoq-arm",str(autoq),str(fixtures),case,str(folder)] if mode=="autoq"
                      else ["--arm",str(binary),str(solver),case,mode,str(folder)])
                p=subprocess.run(["/usr/bin/time","-f","%e %M","-o",str(folder/"resource.txt"),
                    "timeout","--kill-after=1s",str(CAP),
                    sys.executable,str(pathlib.Path(__file__).resolve()),*args],
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
            for m in ("structural","structural-factor"):
                r=next(r for r in rows if r["period"]==p and r["case"]==c and r["mode"]==m)
                assert r["verdict"]==CASES[c] and r["queries"]==0 and r["native"]["route"]=="symbolic",r
    summary={m:dict(arms=sum(r["mode"]==m for r in rows),
                    definite=sum(r["mode"]==m and r["verdict"]!="UNKNOWN" for r in rows),
                    known_queries=sum(r["queries"] or 0 for r in rows if r["mode"]==m),
                    censored=sum(r["mode"]==m and r.get("reason") in ("PROCESS_TIMEOUT","OUTER_DEADLINE") for r in rows)) for m in MODES}
    (out/"summary.json").write_text(json.dumps(dict(rows=rows,summary=summary,
        binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
        gpmc_sha256=hashlib.sha256(solver.read_bytes()).hexdigest(),
        autoq_sha256=hashlib.sha256(autoq.read_bytes()).hexdigest(),autoq_pin=PIN),indent=2)+"\n")
    print("AQ_C3_SUMMARY "+json.dumps(summary),flush=True)

if __name__=="__main__":
    if sys.argv[1]=="--arm":
        arm(pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]),sys.argv[4],sys.argv[5],pathlib.Path(sys.argv[6]))
    elif sys.argv[1]=="--autoq-arm":
        autoq_arm(pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]),sys.argv[4],pathlib.Path(sys.argv[5]))
    else:
        main()
